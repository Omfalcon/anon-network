# sender/sender.py

import requests

from config import TRUSTEE_URL, ME_URLS


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

if __name__ == "__main__":
    main()