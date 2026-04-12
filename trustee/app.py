# trustee/app.py

import uuid
from collections import defaultdict

import requests
from flask import Flask, request, jsonify
from pymongo import MongoClient

from common.crypto import load_public_key_from_file, verify_signature
from common.shamir import reconstruct_ip, split_ip
from config import DB_NAME, ME_URLS, MONGO_URI, TRACE_AUTH_TOKEN

app = Flask(__name__)

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
senders_collection = db["senders"]


@app.route("/register", methods=["POST"])
def register():
    data = request.json
    ip = data.get("ip")

    if not ip:
        return jsonify({"error": "IP required"}), 400

    pseudonym = "PA-" + str(uuid.uuid4())[:8]
    fragments = split_ip(ip)

    senders_collection.insert_one({
        "pseudonym": pseudonym,
        "real_ip": ip,
        "fragments": fragments
    })

    print(f"[Trustee] Registered {pseudonym} with IP {ip}")

    return jsonify({
        "pseudonym": pseudonym,
        "fragments": fragments
    })


@app.route("/trace/reconstruct", methods=["POST"])
def trace_reconstruct():
    """
    Phase 5 — Controlled reverse trace: collect signed fragments from all MEs,
    verify RSA signatures, reconstruct IP, compare to Trustee ground truth.
    Requires Authorization: Bearer <TRACE_AUTH_TOKEN>.
    """
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {TRACE_AUTH_TOKEN}":
        return jsonify({"error": "Unauthorized"}), 401

    body = request.json or {}
    pseudonym = body.get("pseudonym")
    if not pseudonym:
        return jsonify({"error": "pseudonym required"}), 400

    sender_doc = senders_collection.find_one({"pseudonym": pseudonym})
    if not sender_doc:
        return jsonify({"error": "unknown pseudonym"}), 404

    all_rows = []
    for me_url in ME_URLS:
        try:
            r = requests.post(
                f"{me_url.rstrip('/')}/trace/fragments",
                json={"pseudonym": pseudonym},
                headers={"Authorization": f"Bearer {TRACE_AUTH_TOKEN}"},
                timeout=30,
            )
            r.raise_for_status()
            payload = r.json()
            all_rows.extend(payload.get("fragments", []))
        except requests.RequestException as e:
            print(f"[Trustee] Phase 5 | ME request failed ({me_url}): {e}")
            return jsonify({"error": f"ME unreachable: {me_url}"}), 502

    # Multiple Mongo rows per position can exist (e.g. old signatures before ME used PEM keys).
    # For each position, prefer the newest doc whose signature verifies against current keys/ME{1,2}_pub.pem.
    by_position = defaultdict(list)
    for row in all_rows:
        pos = row.get("position")
        if pos is not None:
            by_position[int(pos)].append(row)

    if sorted(by_position.keys()) != [0, 1, 2, 3]:
        return jsonify({
            "error": "fragment positions must be exactly 0,1,2,3",
            "unique_positions": sorted(by_position.keys()),
        }), 400

    verified_rows = []
    for pos in range(4):
        candidates = by_position[pos]
        candidates.sort(key=lambda r: r.get("mongo_id", ""), reverse=True)
        chosen = None
        for row in candidates:
            me_id = row.get("me_id")
            if not me_id:
                continue
            try:
                pk = load_public_key_from_file(me_id)
            except FileNotFoundError:
                return jsonify({"error": f"no public key on disk for {me_id}"}), 500
            if verify_signature(pk, str(row["fragment"]), row["signature"]):
                chosen = row
                break
        if chosen is None:
            return jsonify({
                "error": "no verifying signature for this position (stale Mongo fragments? clear collection or restart MEs after keyring)",
                "position": pos,
                "candidates": len(candidates),
            }), 400
        verified_rows.append(chosen)

    ordered = [str(r["fragment"]) for r in verified_rows]
    reconstructed = reconstruct_ip(ordered)
    ground = sender_doc["real_ip"]
    match = reconstructed == ground

    print(
        f"[Trustee] Phase 5 | trace/reconstruct | {pseudonym} → IP={reconstructed} "
        f"| ground_truth={ground} | match={match}"
    )

    return jsonify({
        "pseudonym": pseudonym,
        "reconstructed_ip": reconstructed,
        "trustee_ground_truth_ip": ground,
        "ground_truth_match": match,
        "fragments_verified": len(verified_rows),
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)