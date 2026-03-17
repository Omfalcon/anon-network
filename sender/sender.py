# sender/sender.py

import requests
import os
from common.crypto import create_onion, load_public_key
from config import TRUSTEE_URL, ME_URLS, ROUTING_TABLE



def main():
    ip = "192.168.1.10"

    print("Registering with Trustee...")
    response = requests.post(
        f"{TRUSTEE_URL}/register",
        json={"ip": ip}
    )

    data = response.json()
    pseudonym = data["pseudonym"]
    fragments = data["fragments"]

    print(f"Pseudonym: {pseudonym}")
    print("Fragments:", fragments)

    signed_fragments = []

    for i, fragment in enumerate(fragments):
        me_url = ME_URLS[i % len(ME_URLS)]

        print(f"Sending fragment {fragment} to {me_url}")

        sign_response = requests.post(
            f"{me_url}/sign",
            json={
                "fragment": fragment,
                "pseudonym": pseudonym
            }
        )

        signed_data = sign_response.json()
        signed_fragments.append(signed_data)

    print("\nSigned Fragments:")
    for sf in signed_fragments:
        print(f"{sf['fragment']} → Signed ✔")

    print("\nInitializing connection...")

    init_response = requests.post(
        "http://127.0.0.1:6001/init",
        json={}
    )

    aci = init_response.json()["aci"]

    print(f"Received ACI: {aci}")

    print("\nSending message through circuit...")

    requests.post(
        "http://127.0.0.1:6001/forward",
        json={
            "aci": aci,
            "message": "Hello om Circuit"
        }
    )

    def get_key(node_name):
        with open(f"keys/{node_name}_pub.pem", "r") as f:
            return load_public_key(f.read())

    try:
        pub_s = get_key("routerS")
        pub_x = get_key("routerX")
        pub_y = get_key("routerY")
        pub_b = get_key("receiverB")
    except FileNotFoundError:
        print("Error: Public keys not found. Ensure Phase 1 key generation is complete.")
        return

    # 2. Define the Hops (Inside-Out: Receiver -> Y -> X -> S)
    # Each hop tuple: (Public Key, Next Hop URL)
    # The ACI and signed fragments are included in the innermost message
    inner_payload = {
        "aci": aci,
        "message": "Hello om Circuit",
        "fragments": signed_fragments
    }
    
    hops = [
        (pub_b, None),                             # Final destination: Receiver
        (pub_y, ROUTING_TABLE["RECEIVER"]),        # Router Y forwards to Receiver
        (pub_x, ROUTING_TABLE["ROUTER_Y"]),        # Router X forwards to Y
        (pub_s, ROUTING_TABLE["ROUTER_X"])         # Router S forwards to X
    ]

    # 3. Create the Onion
    import json
    onion = create_onion(json.dumps(inner_payload), hops)

    print("\nSending onion through circuit...")
    # We only send onion to the FIRST router (S)
    requests.post(
        "http://127.0.0.1:6001/forward",
        json={"onion": onion}
    )

if __name__ == "__main__":
    main()