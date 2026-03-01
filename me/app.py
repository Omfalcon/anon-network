
from flask import Flask, request, jsonify
from pymongo import MongoClient
from config import MONGO_URI, DB_NAME
from common.crypto import generate_keys, sign_data, serialize_public_key
import os

app = Flask(__name__)

private_key, public_key = generate_keys()

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
fragments_collection = db["fragments"]


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

    if not fragment or not pseudonym:
        return jsonify({"error": "Missing data"}), 400

    signature = sign_data(private_key, fragment)

    fragments_collection.insert_one({
        "pseudonym": pseudonym,
        "fragment": fragment,
        "signature": signature
    })

    print(f"[ME] Signed fragment {fragment} for {pseudonym}")

    return jsonify({
        "fragment": fragment,
        "signature": signature
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)