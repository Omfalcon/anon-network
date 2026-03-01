# router/app.py

from flask import Flask, request, jsonify
import requests
import os
import uuid

app = Flask(__name__)

NEXT_HOP = os.environ.get("NEXT_HOP")

# In-memory routing table
routing_table = {}


@app.route("/init", methods=["POST"])
def init_connection():
    data = request.json
    aci = data.get("aci")

    if not aci:
        aci = "ACI-" + str(uuid.uuid4())[:8]

    routing_table[aci] = {
        "next_hop": NEXT_HOP
    }

    print(f"[Router {os.environ.get('PORT')}] Registered ACI {aci}")

    if NEXT_HOP and "600" in NEXT_HOP:
        requests.post(
            f"{NEXT_HOP}/init",
            json={"aci": aci}
        )

    return jsonify({"aci": aci})

@app.route("/forward", methods=["POST"])
def forward():
    data = request.json
    aci = data.get("aci")
    message = data.get("message")

    print(f"[Router {os.environ.get('PORT')}] Received message for {aci}: {message}")

    if aci not in routing_table:
        print("Unknown ACI. Rejecting.")
        return jsonify({"error": "Unknown ACI"}), 400

    next_hop = routing_table[aci]["next_hop"]

    if next_hop:
        print(f"[Router {os.environ.get('PORT')}] Forwarding {aci} to {next_hop}")

        # Determine endpoint
        endpoint = "/forward" if "600" in next_hop else "/receive"

        requests.post(
            f"{next_hop}{endpoint}",
            json={"aci": aci, "message": message}
        )

    return jsonify({"status": "Forwarded"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 6001))
    app.run(host="0.0.0.0", port=port, debug=True)