
from flask import Flask, request, jsonify
from pymongo import MongoClient
from config import MONGO_URI, DB_NAME, TRACE_AUTH_TOKEN
from common.crypto import sign_data, serialize_public_key, load_private_key
import os

app = Flask(__name__)

NODE_NAME = os.environ.get("NODE_NAME", "ME1")
private_key = load_private_key(NODE_NAME)
public_key = private_key.public_key()

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
fragments_collection = db["fragments"]


def _trace_authorized() -> bool:
    auth = request.headers.get("Authorization", "")
    return auth == f"Bearer {TRACE_AUTH_TOKEN}"


@app.route("/public_key", methods=["GET"])
def get_public_key():
    return jsonify({
        "public_key": serialize_public_key(public_key)
    })


@app.route("/sign", methods=["POST"])
def sign_fragment():
    data = request.json
    fragment = data.get("fragment")
    pseudonym = data.get("pseudonym")
    position = data.get("position")

    if not fragment or not pseudonym or position is None:
        return jsonify({"error": "fragment, pseudonym, and position required"}), 400

    fragment = str(fragment)

    try:
        position = int(position)
    except (TypeError, ValueError):
        return jsonify({"error": "position must be an integer"}), 400

    signature = sign_data(private_key, fragment)

    fragments_collection.insert_one({
        "pseudonym": pseudonym,
        "fragment": fragment,
        "signature": signature,
        "position": position,
        "me_id": NODE_NAME,
    })

    print(f"[{NODE_NAME}] Signed fragment {fragment} (pos={position}) for {pseudonym}")

    return jsonify({
        "fragment": fragment,
        "signature": signature,
        "position": position,
        "me_id": NODE_NAME,
    })


@app.route("/trace/fragments", methods=["POST"])
def trace_fragments():
    """Phase 5: release this ME's signed fragments for a pseudonym (authorized only)."""
    if not _trace_authorized():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json or {}
    pseudonym = data.get("pseudonym")
    if not pseudonym:
        return jsonify({"error": "pseudonym required"}), 400

    cursor = fragments_collection.find(
        {"pseudonym": pseudonym, "me_id": NODE_NAME},
    )
    rows = []
    for doc in cursor:
        rows.append(
            {
                "pseudonym": doc["pseudonym"],
                "fragment": str(doc["fragment"]),
                "signature": doc["signature"],
                "position": doc["position"],
                "me_id": doc["me_id"],
                "mongo_id": str(doc["_id"]),
            }
        )
    print(f"[{NODE_NAME}] Phase 5 | /trace/fragments | {pseudonym} → {len(rows)} record(s)")
    return jsonify({"me_id": NODE_NAME, "fragments": rows}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
