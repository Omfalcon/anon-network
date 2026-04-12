import os
import uuid

import requests
from flask import Flask, jsonify, request

from common.crypto import decrypt_layer, load_private_key
from common.link_session import (
    b64_to_public_key,
    derive_link_key,
    generate_x25519_pair,
    link_decrypt,
    link_encrypt,
    public_key_to_b64,
)

try:
    from config import NODE_BASES
except ImportError:
    NODE_BASES = {
        "routerS": "http://127.0.0.1:6001",
        "routerX": "http://127.0.0.1:6002",
        "routerY": "http://127.0.0.1:6003",
        "receiverB": "http://127.0.0.1:7000",
    }

app = Flask(__name__)
NODE_NAME = os.environ.get("NODE_NAME", "routerS")
PORT = os.environ.get("PORT", 6001)

private_key = load_private_key(NODE_NAME)

# Phase 4: per-circuit link keys (same material; direction is encrypt vs decrypt)
in_session_keys: dict[str, bytes] = {}
out_session_keys: dict[str, bytes] = {}


def _is_entry() -> bool:
    return NODE_NAME == "routerS"


@app.route("/forward", methods=["POST"])
def forward():
    data = request.json or {}
    onion_blob = data.get("onion")
    aci = data.get("aci")

    if not aci:
        return jsonify({"error": "aci required for session-key forwarding"}), 400

    try:
        print(f"[{NODE_NAME}] Phase 4 | /forward | ACI={aci}")
        if _is_entry():
            print(f"[{NODE_NAME}] Phase 4 | entry: onion from sender (outer layer = RSA for {NODE_NAME}; no link decrypt)")
            inner_str = onion_blob
        else:
            k_in = in_session_keys.get(aci)
            if not k_in:
                return jsonify({"error": f"no inbound session for {aci}"}), 400
            print(f"[{NODE_NAME}] Phase 4 | link AES-GCM decrypt ok (inbound session key for this ACI)")
            inner_str = link_decrypt(k_in, onion_blob).decode("utf-8")

        peeled_data = decrypt_layer(private_key, inner_str)
        next_hop = peeled_data.get("next_hop")
        inner_onion = peeled_data.get("message")

        print(f"[{NODE_NAME}] Phase 3 | RSA+Fernet layer peeled → next_hop={next_hop}")

        if not next_hop:
            return jsonify({"error": "No next hop"}), 400

        k_out = out_session_keys.get(aci)
        if not k_out:
            return jsonify({"error": f"no outbound session for {aci}"}), 400

        payload = inner_onion
        if isinstance(payload, str):
            payload_bytes = payload.encode("utf-8")
        else:
            payload_bytes = payload

        wrapped = link_encrypt(k_out, payload_bytes)
        print(
            f"[{NODE_NAME}] Phase 4 | link AES-GCM encrypt → {next_hop} "
            f"(frame ~{len(wrapped)} b64 chars)"
        )
        requests.post(next_hop, json={"onion": wrapped, "aci": aci}, timeout=30)
        return jsonify({"status": "Forwarded"}), 200

    except Exception as e:
        print(f"[{NODE_NAME}] Forward failed: {e}")
        return jsonify({"error": "Forward failed"}), 403


@app.route("/init", methods=["POST"])
def init_circuit():
    if not _is_entry():
        return jsonify({"error": "Circuit init must be requested from entry router (routerS)"}), 400

    aci = f"ACI-{uuid.uuid4().hex[:8]}"
    print(f"\n[{NODE_NAME}] Phase 4 | /init | new circuit {aci}")
    print(f"[{NODE_NAME}] Phase 4 | ECDH handshake 1/3: routerS → routerX ...")

    # 1) S -> X
    priv_s, pub_s = generate_x25519_pair()
    rx = requests.post(
        f"{NODE_BASES['routerX']}/session/handshake",
        json={
            "aci": aci,
            "initiator_pub_b64": public_key_to_b64(pub_s),
            "initiator_node": "routerS",
            "responder_node": "routerX",
        },
        timeout=30,
    )
    rx.raise_for_status()
    pub_x = b64_to_public_key(rx.json()["responder_pub_b64"])
    shared_sx = priv_s.exchange(pub_x)
    out_session_keys[aci] = derive_link_key(shared_sx, aci, "routerS", "routerX")
    print(f"[{NODE_NAME}] Phase 4 | ECDH S↔X OK | HKDF link key stored for {aci}")

    # 2) X -> Y (orchestrated on X)
    print(f"[{NODE_NAME}] Phase 4 | ECDH handshake 2/3: routerX → routerY (downstream on X) ...")
    dr = requests.post(
        f"{NODE_BASES['routerX']}/session/downstream",
        json={"aci": aci},
        timeout=30,
    )
    dr.raise_for_status()

    # 3) Y -> receiver
    print(f"[{NODE_NAME}] Phase 4 | ECDH handshake 3/3: routerY → receiverB ...")
    yr = requests.post(
        f"{NODE_BASES['routerY']}/session/downstream",
        json={"aci": aci},
        timeout=30,
    )
    yr.raise_for_status()

    print(f"[{NODE_NAME}] Phase 4 | /init complete — all link keys ready for {aci}\n")
    return jsonify({"aci": aci})


@app.route("/session/handshake", methods=["POST"])
def session_handshake():
    body = request.json or {}
    aci = body.get("aci")
    i_pub_b64 = body.get("initiator_pub_b64")
    initiator_node = body.get("initiator_node")
    responder_node = body.get("responder_node")

    if not all([aci, i_pub_b64, initiator_node, responder_node]):
        return jsonify({"error": "aci, initiator_pub_b64, initiator_node, responder_node required"}), 400
    if responder_node != NODE_NAME:
        return jsonify({"error": "wrong responder for this node"}), 400

    try:
        i_pub = b64_to_public_key(i_pub_b64)
        priv_r, pub_r = generate_x25519_pair()
        shared = priv_r.exchange(i_pub)
        in_session_keys[aci] = derive_link_key(shared, aci, initiator_node, responder_node)
        print(
            f"[{NODE_NAME}] Phase 4 | ECDH responder | {initiator_node}→{responder_node} | "
            f"inbound link key stored | {aci}"
        )
        return jsonify({"responder_pub_b64": public_key_to_b64(pub_r)}), 200
    except Exception as e:
        print(f"[{NODE_NAME}] handshake failed: {e}")
        return jsonify({"error": "handshake failed"}), 400


@app.route("/session/downstream", methods=["POST"])
def session_downstream():
    if NODE_NAME not in ("routerX", "routerY"):
        return jsonify({"error": "downstream only on routerX or routerY"}), 404

    body = request.json or {}
    aci = body.get("aci")
    if not aci:
        return jsonify({"error": "aci required"}), 400

    if NODE_NAME == "routerX":
        target_base = NODE_BASES["routerY"]
        target_name = "routerY"
        i_node, r_node = "routerX", "routerY"
    else:
        target_base = NODE_BASES["receiverB"]
        target_name = "receiverB"
        i_node, r_node = "routerY", "receiverB"

    try:
        priv_i, pub_i = generate_x25519_pair()
        rr = requests.post(
            f"{target_base}/session/handshake",
            json={
                "aci": aci,
                "initiator_pub_b64": public_key_to_b64(pub_i),
                "initiator_node": i_node,
                "responder_node": r_node,
            },
            timeout=30,
        )
        rr.raise_for_status()
        peer_pub = b64_to_public_key(rr.json()["responder_pub_b64"])
        shared = priv_i.exchange(peer_pub)
        out_session_keys[aci] = derive_link_key(shared, aci, i_node, r_node)
        print(
            f"[{NODE_NAME}] Phase 4 | ECDH initiator | {i_node}→{r_node} | "
            f"outbound link key stored | {aci}"
        )
        return jsonify({"status": "ok", "target": target_name}), 200
    except Exception as e:
        print(f"[{NODE_NAME}] downstream failed: {e}")
        return jsonify({"error": "downstream failed"}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(PORT))
