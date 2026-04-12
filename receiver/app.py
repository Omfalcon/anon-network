import json
import os

from flask import Flask, jsonify, request

from common.crypto import decrypt_layer, load_private_key
from common.link_session import (
    b64_to_public_key,
    derive_link_key,
    generate_x25519_pair,
    link_decrypt,
    public_key_to_b64,
)

app = Flask(__name__)
private_key = load_private_key("receiverB")

in_session_keys: dict[str, bytes] = {}


@app.route("/session/handshake", methods=["POST"])
def session_handshake():
    body = request.json or {}
    aci = body.get("aci")
    i_pub_b64 = body.get("initiator_pub_b64")
    initiator_node = body.get("initiator_node")
    responder_node = body.get("responder_node")

    if not all([aci, i_pub_b64, initiator_node, responder_node]):
        return jsonify({"error": "aci, initiator_pub_b64, initiator_node, responder_node required"}), 400
    if responder_node != "receiverB":
        return jsonify({"error": "wrong responder for this node"}), 400

    try:
        i_pub = b64_to_public_key(i_pub_b64)
        priv_r, pub_r = generate_x25519_pair()
        shared = priv_r.exchange(i_pub)
        in_session_keys[aci] = derive_link_key(shared, aci, initiator_node, responder_node)
        print(
            f"[receiverB] Phase 4 | ECDH responder | {initiator_node}→{responder_node} | "
            f"inbound link key stored | {aci}"
        )
        return jsonify({"responder_pub_b64": public_key_to_b64(pub_r)}), 200
    except Exception as e:
        print(f"[receiverB] handshake failed: {e}")
        return jsonify({"error": "handshake failed"}), 400


@app.route("/receive", methods=["POST"])
def receive():
    data = request.json or {}
    onion_blob = data.get("onion")
    aci = data.get("aci")

    if not aci:
        return jsonify({"error": "aci required"}), 400

    try:
        k_in = in_session_keys.get(aci)
        if not k_in:
            return jsonify({"error": f"no inbound session for {aci}"}), 400

        print(f"[receiverB] Phase 4 | /receive | ACI={aci}")
        print("[receiverB] Phase 4 | link AES-GCM decrypt ok (from routerY)")
        inner_str = link_decrypt(k_in, onion_blob).decode("utf-8")
        print("[receiverB] Phase 3 | final RSA+Fernet layer peel → inner JSON payload")
        peeled_data = decrypt_layer(private_key, inner_str)
        inner_content = json.loads(peeled_data.get("message"))

        print("\n" + "=" * 30)
        print("[Receiver] SUCCESS: Onion Decapsulated")
        print(f"[*] ACI: {inner_content.get('aci')}")
        print(f"[*] Msg: {inner_content.get('message')}")
        print(f"[*] Fragments: {len(inner_content.get('fragments', []))}")
        print("=" * 30 + "\n")

        return jsonify({"status": "Success"}), 200

    except Exception as e:
        print(f"[Receiver] Final decryption crash: {e}")
        return jsonify({"error": "Decryption failed"}), 403


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7000))
    app.run(host="0.0.0.0", port=port)
