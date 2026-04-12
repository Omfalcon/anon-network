# 🎓 Research & Verification Guide (IEEE Paper Support)

This document contains the formal proofs, limitations, and verification procedures for the **Anon-Network** project. Use this during your paper writing to cite specific "test procedures" and "security properties."

---

## 🛡️ 1. Security Proofs (Link Layer)

We have implemented a formal verification script to prove the cryptographic properties of **Phase 4 (Link Encryption)**.

### Performance & Security Correlation
Run the following script to demonstrate that intermediate nodes cannot decrypt the onion without the circuit-bound session key:

```powershell
python verify_link_layer_demo.py
```

**What this proves for your paper:**
- **Key Uniqueness**: Keys derived via HKDF are unique to the pair of nodes and the specific ACI.
- **Confidentiality**: Even if an attacker captures the `onion` blob on the wire, they cannot recover the inner layers without the ephemeral X25519 shared secret.
- **Integrity**: Any tampering with the ciphertext results in an `InvalidTag` error (AES-GCM property).

---

## 📊 2. Benchmarking Results

To provide quantitative data for your "Results and Discussion" section, use the internal benchmarking suite.

### Procedure:
1. Ensure all nodes are running (`.\startup.ps1`).
2. Run the benchmark:
   ```powershell
   $env:PYTHONPATH="."
   python benchmark/benchmark.py
   ```
3. Generate the plots:
   ```powershell
   python benchmark/generate_plots.py
   ```

### Output Files for Paper:
- `benchmark/latency_breakdown.png`: Shows the cost of **Registration** vs. **Circuit Setup** vs. **Trace**.
- `benchmark/crypto_performance.png`: Compares raw RSA, AES, and ECDH overhead.

**Interpretation:** You can argue that while **Phase 5 (Trace)** adds slight latency, it is performed "out-of-band" and does not impact the **real-time forwarding** speed of the network.

---

## 🔍 3. Verification Checklist (Paper Citations)

| Step | Component | Verification Marker |
|------|-----------|----------------------|
| **1** | **Identity** | `Trustee` assigns fragments; `MEs` provide RSA signatures. |
| **2** | **Privacy** | `Router S/X/Y` each peel exactly 1 RSA layer; cannot see the destination. |
| **3** | **Security** | `link_session` uses ECDH + AES-GCM to prevent eavesdropping between routers. |
| **4** | **Accountability**| `trace_request.py` successfully matches registered IP using distributed fragments. |

---

## ⚠️ 4. Research Limitations

For a strong academic paper, you must state what the system is **not** claiming to solve:
1. **Localhost Simulation**: The benchmarks are run on a local machine; real-world latency would include network jitter and light-speed delays.
2. **No Transport TLS**: This demo focuses on **Onion and Link encryption**. In a real-world scenario, standard TLS would be added for transport-layer security.
3. **Policy-Gated Trace**: Traceability relies on the possession of the `TRACE_AUTH_TOKEN`. This represents a **Policy Boundary**, assuming the Trustee and MEs are under legal/governance oversight.

---

## 📸 5. Screenshots to Capture
- **Sender Terminal**: Shows the `ACI` generation and `Baking onion` logs.
- **Receiver Terminal**: The `SUCCESS` block showing the decrypted message.
- **Trace Terminal**: The `ground_truth_match: true` JSON output.
- **Plots**: The PNGs generated in the `benchmark/` folder.
