# receiver/app.py

from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route("/receive", methods=["POST"])
def receive():
    data = request.json
    aci = data.get("aci")
    message = data.get("message")

    print(f"[Receiver] ACI {aci} → Message: {message}")

    return jsonify({"status": "Message received"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7000, debug=True)