from flask import Flask, request, jsonify
import os
import json
from common.crypto import decrypt_layer, load_private_key

app = Flask(__name__)
private_key = load_private_key("receiverB")

@app.route("/receive", methods=["POST"])
def receive():
    data = request.json
    onion_blob = data.get("onion")

    try:
        # Peel the final layer
        peeled_data = decrypt_layer(private_key, onion_blob)
        
        # The 'message' inside the final layer is the stringified inner_payload
        inner_content = json.loads(peeled_data.get("message"))
        
        print("\n" + "="*30)
        print("[Receiver] SUCCESS: Onion Decapsulated")
        print(f"[*] ACI: {inner_content.get('aci')}")
        print(f"[*] Msg: {inner_content.get('message')}")
        print(f"[*] Fragments: {len(inner_content.get('fragments', []))}")
        print("="*30 + "\n")

        return jsonify({"status": "Success"}), 200

    except Exception as e:
        print(f"[Receiver] Final decryption crash: {e}")
        return jsonify({"error": "Decryption failed"}), 403

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7000)) 
    app.run(host="0.0.0.0", port=port)