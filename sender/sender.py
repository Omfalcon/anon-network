import requests
import os
import json
from common.crypto import create_onion, load_public_key_from_file
from config import TRUSTEE_URL, ME_URLS, ROUTING_TABLE

def main():
    ip = "192.168.1.10"

    # --- Phase 1 & 2: Trustee & ME Registration ---
    print("Registering with Trustee...")
    response = requests.post(f"{TRUSTEE_URL}/register", json={"ip": ip})
    data = response.json()
    pseudonym, fragments = data["pseudonym"], data["fragments"]

    signed_fragments = []
    for i, fragment in enumerate(fragments):
        me_url = ME_URLS[i % len(ME_URLS)]
        sign_response = requests.post(f"{me_url}/sign", json={"fragment": fragment, "pseudonym": pseudonym})
        signed_fragments.append(sign_response.json())

    # --- Phase 3: Onion Routing ---
    # 1. Initialize ACI
    init_response = requests.post("http://127.0.0.1:6001/init", json={})
    aci = init_response.json()["aci"]
    print(f"Received ACI: {aci}")

    # 2. Load Public Keys (Using our helper)
    try:
        pub_s = load_public_key_from_file("routerS")
        pub_x = load_public_key_from_file("routerX")
        pub_y = load_public_key_from_file("routerY")
        pub_b = load_public_key_from_file("receiverB")
    except FileNotFoundError:
        print("Error: PEM files missing in /keys folder.")
        return

    # 3. Prepare Payload (Hybrid Encryption handles the size!)
    inner_payload = {
        "aci": aci,
        "message": "Hello from Circuit",
        "fragments": signed_fragments
    }

    # 4. Define Hops (Inside-Out)
    hops = [
        (pub_b, None),                       # Final: Receiver
        (pub_y, ROUTING_TABLE["RECEIVER"]),  # Y -> Receiver
        (pub_x, ROUTING_TABLE["Y"]),         # X -> Y
        (pub_s, ROUTING_TABLE["X"])          # S -> X
    ]

    print("\nBaking the Hybrid Onion...")
    onion = create_onion(json.dumps(inner_payload), hops)

    print("Sending onion to entry node (Router S)...")
    requests.post("http://127.0.0.1:6001/forward", json={"onion": onion})

if __name__ == "__main__":
    main()