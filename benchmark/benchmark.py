import sys
import os
import time
import requests
import json
import pandas as pd

# Add the project root to sys.path so 'config' and 'common' can be imported
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import TRUSTEE_URL, ME_URLS, TRACE_AUTH_TOKEN

def benchmark_crypto():
    """Measures the raw overhead of core cryptographic operations."""
    from common.crypto import generate_keys, sign_data, encrypt_layer, load_public_key_from_file
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    
    print("\n[Benchmarking] Starting Cryptographic Performance Test...")
    results = []
    
    # RSA Key Gen
    start = time.perf_counter()
    priv, pub = generate_keys()
    results.append({"operation": "RSA-2048 KeyGen", "time_ms": (time.perf_counter() - start) * 1000})
    
    # RSA Sign
    data = "192"
    start = time.perf_counter()
    for _ in range(100):
        sign_data(priv, data)
    results.append({"operation": "RSA-2048 Sign (x100)", "time_ms": (time.perf_counter() - start) * 10})
    
    # ECDH Key Gen (X25519)
    start = time.perf_counter()
    x_priv = X25519PrivateKey.generate()
    results.append({"operation": "X25519 KeyGen", "time_ms": (time.perf_counter() - start) * 1000})

    return results

def benchmark_system():
    """Measures latency of full system phases. Expects nodes to be running."""
    print("\n[Benchmarking] Starting System Latency Test...")
    phases = []
    
    # Phase 1-2: Registration
    try:
        start = time.perf_counter()
        response = requests.post(f"{TRUSTEE_URL}/register", json={"ip": "10.0.0.1"})
        reg_time = (time.perf_counter() - start) * 1000
        data = response.json()
        pseudonym = data["pseudonym"]
        fragments = data["fragments"]
        
        # ME Signing
        start = time.perf_counter()
        for i, frag in enumerate(fragments):
            requests.post(f"{ME_URLS[i % len(ME_URLS)]}/sign", 
                          json={"fragment": frag, "pseudonym": pseudonym, "position": i})
        sign_time = (time.perf_counter() - start) * 1000
        phases.append({"phase": "P1-2: Registration + ME Sign", "time_ms": reg_time + sign_time})
        print(f"  [ok] Phase 1-2: {reg_time + sign_time:.2f}ms")

        # Phase 4: Circuit Setup (/init)
        start = time.perf_counter()
        init_res = requests.post("http://127.0.0.1:6001/init", json={})
        setup_time = (time.perf_counter() - start) * 1000
        aci = init_res.json()["aci"]
        phases.append({"phase": "P4: Circuit Setup (ECDH)", "time_ms": setup_time})
        print(f"  [ok] Phase 4 Setup: {setup_time:.2f}ms")

        # Phase 5: Trace
        start = time.perf_counter()
        requests.post(f"{TRUSTEE_URL}/trace/reconstruct", 
                      json={"pseudonym": pseudonym},
                      headers={"Authorization": f"Bearer {TRACE_AUTH_TOKEN}"})
        trace_time = (time.perf_counter() - start) * 1000
        phases.append({"phase": "P5: Reverse Trace", "time_ms": trace_time})
        print(f"  [ok] Phase 5 Trace: {trace_time:.2f}ms")

    except Exception as e:
        print(f"  [!] System benchmark failed: {e}. Are the nodes running?")
        return []

    return phases

def main():
    # 1. Crypto Bench
    crypto_res = benchmark_crypto()
    
    # 2. System Bench
    system_res = benchmark_system()
    
    # Save to CSV
    if crypto_res or system_res:
        df = pd.DataFrame(crypto_res + system_res)
        csv_path = os.path.join(SCRIPT_DIR, "results.csv")
        df.to_csv(csv_path, index=False)
        print(f"\n[Success] Results saved to {csv_path}")
        print("Run 'python benchmark/generate_plots.py' next.")
    else:
        print("\n[Error] No results collected. Check if nodes are running.")

if __name__ == "__main__":
    main()
