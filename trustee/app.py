# trustee/app.py

from flask import Flask, request, jsonify
from pymongo import MongoClient
import uuid
from config import MONGO_URI, DB_NAME
from common.shamir import split_ip

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)