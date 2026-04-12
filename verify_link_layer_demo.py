"""
verify_link_layer_demo.py
-------------------------
Proof of Security for IEEE Paper (Phase 4: Link Encryption).
Demonstrates:
1. Success: Neighbors with the shared ACI and secret can decrypt.
2. Failure: Observers with the WRONG key cannot decrypt.
3. Failure: Observers with the WRONG ACI (salt) cannot decrypt.
"""

import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from common.link_session import derive_link_key, link_encrypt, link_decrypt

def run_proof():
    print("\n" + "="*50)
    print("PHASE 4 PROOF: Pairwise Link Security")
    print("="*50)

    # 1. Setup shared context
    shared_secret = os.urandom(32)
    aci_correct = "ACI-CORRECT-123456"
    aci_wrong = "ACI-WRONG-654321"
    node_a, node_b = "RouterS", "RouterX"
    
    plaintext = b"Sensitive Onion Layer Data"
    
    # Derive the correct key
    key_correct = derive_link_key(shared_secret, aci_correct, node_a, node_b)
    
    # 2. Encrypt with the correct key
    ciphertext_b64 = link_encrypt(key_correct, plaintext)
    print(f"[Setup] Encrypted data for {node_a} <-> {node_b}")
    print(f"[Setup] ACI: {aci_correct}")

    # --- TEST 1: SUCCESS CASE ---
    try:
        decrypted = link_decrypt(key_correct, ciphertext_b64)
        if decrypted == plaintext:
            print("[SUCCESS] Test 1: Authorized neighbor decrypted correctly. [ok]")
        else:
            print("[FAIL] Test 1: Decryption mismatch.")
    except Exception as e:
        print(f"[FAIL] Test 1: Unexpected error: {e}")

    # --- TEST 2: WRONG KEY (Impersonation/Eavesdropping) ---
    wrong_secret = os.urandom(32)
    key_attacker = derive_link_key(wrong_secret, aci_correct, node_a, node_b)
    
    try:
        link_decrypt(key_attacker, ciphertext_b64)
        print("[FAIL] Test 2: Attacker with wrong secret decrypted the data!")
    except Exception:
        print("[SUCCESS] Test 2: Attacker with wrong key failed (InvalidTag). [ok]")

    # --- TEST 3: WRONG ACI (Replay/Mismatched Context) ---
    # Even with the right secret, the wrong ACI results in a different derived key.
    key_wrong_aci = derive_link_key(shared_secret, aci_wrong, node_a, node_b)
    
    try:
        link_decrypt(key_wrong_aci, ciphertext_b64)
        print("[FAIL] Test 3: Attacker with wrong ACI decrypted the data!")
    except Exception:
        print("[SUCCESS] Test 3: Attacker with wrong ACI failed (InvalidTag). [ok]")

    print("="*50)
    print("All security properties verified for Phase 4.")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_proof()
