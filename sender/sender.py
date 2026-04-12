import requests
import os
import json
from common.crypto import create_onion, load_public_key_from_file
from config import TRUSTEE_URL, ME_URLS, ROUTING_TABLE

def main():
    ip = "192.168.1.10"

    # --- Phase 1 & 2: Trustee & ME Registration ---
    print("\n" + "=" * 40)
    print("Phase 1–2: Identity (Trustee + ME signatures)")
    print("=" * 40)
    print("Registering with Trustee...")
    response = requests.post(f"{TRUSTEE_URL}/register", json={"ip": ip})
    response.raise_for_status()
    data = response.json()
    pseudonym, fragments = data["pseudonym"], data["fragments"]
    print(f"[Sender] Pseudonym: {pseudonym} | fragments: {len(fragments)}")

    signed_fragments = []
    for i, fragment in enumerate(fragments):
        me_url = ME_URLS[i % len(ME_URLS)]
        sign_response = requests.post(f"{me_url}/sign", json={"fragment": fragment, "pseudonym": pseudonym})
        sign_response.raise_for_status()
        signed_fragments.append(sign_response.json())

    # --- Phase 3–4: Onion + session keys ---
    print("\n" + "=" * 40)
    print("Phase 3: Hybrid onion (RSA-OAEP + Fernet per hop)")
    print("Phase 4: ECDH at /init + link AES-GCM between routers")
    print("=" * 40)
    print("[Sender] POST http://127.0.0.1:6001/init  (ECDH chain: S→X, X→Y, Y→receiver)")
    init_response = requests.post("http://127.0.0.1:6001/init", json={})
    init_response.raise_for_status()
    aci = init_response.json()["aci"]
    print(f"[Sender] Phase 4 | Circuit ID (ACI): {aci}")
    print("[Sender] Phase 4 | Session keys derived (HKDF salt=ACI); ready to forward.")

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

    print("\n[Sender] Baking hybrid onion (inner → outer: B ← Y ← X ← S)...")
    onion = create_onion(json.dumps(inner_payload), hops)

    print("[Sender] POST http://127.0.0.1:6001/forward  (body: onion + aci for link crypto)")
    fwd = requests.post(
        "http://127.0.0.1:6001/forward",
        json={"onion": onion, "aci": aci},
    )
    fwd.raise_for_status()
    print(f"[Sender] Forward HTTP {fwd.status_code}: {fwd.json()}")

    print("\n" + "=" * 40)
    print("Sender finished. Watch router/receiver terminals for Phase 4 peel + link logs.")
    print("=" * 40 + "\n")

if __name__ == "__main__":
    main()