from flask import Flask, request, jsonify
import requests
import os
from common.crypto import decrypt_layer, load_private_key

app = Flask(__name__)
NODE_NAME = os.environ.get("NODE_NAME", "routerS") # Set by startup.sh
PORT = os.environ.get("PORT", 6001)

# Load unique identity
private_key = load_private_key(NODE_NAME)

@app.route("/forward", methods=["POST"])
def forward():
    data = request.json
    onion_blob = data.get("onion")

    try:
        # Peel layer: returns {'next_hop': ..., 'message': ...}
        peeled_data = decrypt_layer(private_key, onion_blob)
        next_hop = peeled_data.get("next_hop")
        inner_onion = peeled_data.get("message")
        
        print(f"[{NODE_NAME}] Layer peeled. Forwarding to: {next_hop}")

        if next_hop:
            requests.post(next_hop, json={"onion": inner_onion})
            return jsonify({"status": "Forwarded"}), 200
        return jsonify({"error": "No next hop"}), 400

    except Exception as e:
        print(f"[{NODE_NAME}] Decryption failed: {e}")
        return jsonify({"error": "Decryption failed"}), 403

@app.route("/init", methods=["POST"])
def init_circuit():
    import uuid
    return jsonify({"aci": f"ACI-{uuid.uuid4().hex[:8]}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(PORT))