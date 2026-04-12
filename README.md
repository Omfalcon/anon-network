# 🧅 Anon-Network

### Reverse Onion Routing – Phases 1–5 (through Controlled Reverse Trace)
 
---

## 📌 Project Overview

Anon-Network is a distributed, REST-based simulation of a **Reverse Onion Routing System**.

The goal of this project is to:

* Provide anonymous multi-hop communication
* Support circuit-based routing (Tor-like model)
* Enable distributed identity validation
* Allow controlled reverse traceability
* Maintain modular microservice architecture

This implementation currently covers:

* Identity management layer
* Multi-hop routing
* Circuit establishment using ACI (Anonymous Connection Identifier)
* Hybrid per-hop onion encryption (RSA-OAEP + AES-256 via Fernet)
* Per-link session keys (X25519 ECDH + HKDF + AES-GCM) between routers for a given circuit
* **Authorized reverse trace** (Phase 5): collect ME-signed fragments, verify signatures, reconstruct IP vs Trustee ground truth
* Distributed state propagation

---

# 🏗 System Architecture (Current Phase)

```
Identity Layer
    ├── Trustee
    ├── ME1
    └── ME2

Routing Layer
    ├── Router S (Entry)
    ├── Router X
    ├── Router Y
    └── Receiver
```

---

# ✅ Completed Features

## 🔹 Phase 1 – Identity & Validation Layer

**What happens**

* Sender registers with the **Trustee** over REST (`POST /register`) and supplies a real IP.
* The Trustee assigns a **pseudonym** (e.g. `PA-xxxxxxxx`) and splits the IP into **fragments** (implementation: dotted octets as separate strings via `split_ip` in `common/shamir.py`).
* Each fragment is sent to a **Management Entity (ME)** (`POST /sign`). MEs sign fragments with **RSA** using **PKCS#1 v1.5** padding and **SHA-256** (`common/crypto.py` → `sign_data`).
* **MongoDB** stores mappings: pseudonym, real IP, fragments, and ME-side fragment records.

**Encryption / crypto used**

* **Digital signatures:** RSA + PKCS1v15 + SHA-256 on each fragment string (per-ME keypair generated at ME startup).
* No transport encryption in the demo; trust boundaries are logical (separate MEs, no single ME sees the full IP as one blob in one place—fragments are distributed).

### Achievements

✔ Distributed trust
✔ Fragment-based identity protection
✔ Digital signature validation
✔ Cloud MongoDB integration

---

## 🔹 Phase 2A – Multi-Hop Routing

**What happens**

* Independent **router** Flask apps (`router/app.py`) run as **Router S** (entry), **Router X**, **Router Y**, identified by `NODE_NAME` and `PORT`.
* Forwarding is **REST-based** (`POST /forward`): each node receives a payload and passes it toward the **next hop URL** defined by the protocol (in later phases that URL lives inside decrypted onion data).
* **Receiver** exposes `POST /receive` as the path exit.

**Encryption**

* Phase 2A establishes **topology and HTTP flow** only; **onion encryption** is Phase 3 and **link session encryption** is Phase 4.

Message flow:

```
Sender → Router S → Router X → Router Y → Receiver
```

---

## 🔹 Phase 2B – Circuit Establishment (ACI)

**What happens**

* **ACI** (Anonymous Connection Identifier), e.g. `ACI-xxxxxxxx`, labels a logical **circuit**.
* **`POST /init`** on the **entry router (Router S)** creates a new ACI. The sender includes this ACI inside the **inner payload** (JSON) so the receiver can display which circuit delivered the message.
* **`config.py`** defines **`ROUTING_TABLE`**: static next-hop URLs for `X`, `Y`, and `RECEIVER` used when building the onion (Phase 3).
* Forwarding remains **stateful** in the sense that each hop follows the embedded `next_hop` after decryption.

**Encryption**

* ACI itself is carried as **plaintext inside the innermost JSON** after all onion layers are removed at the receiver (not encrypted separately from the message in that inner blob).

* **Phase 4 extension:** the same **`POST /init`** on Router S additionally drives **ECDH session setup** along the path (see Phase 4). The sender still obtains **one ACI** per run and passes **`aci` with `forward`** for link keys.

Now the system behaves as a circuit-based anonymous network.

---

## 🔹 Phase 3 – Hybrid Onion (Per-Hop “Nested” Encryption)

**What happens**

* The sender builds an **onion** from the **inside out**: innermost payload is JSON (ACI, user message, signed fragments), then each hop adds an outer wrapper for **Router Y → X → S** order in code (`create_onion` in `common/crypto.py`).
* Each hop’s decrypted structure is JSON: **`{ "message": <inner blob string>, "next_hop": "<URL>" }`**. The entry receives the **outermost** blob; each router peels **one** layer and forwards the inner string to `next_hop`.

**Encryption techniques**

| Piece | Algorithm | Role |
|--------|-----------|------|
| Bulk of each layer | **AES-256** in **Fernet** | Encrypts the JSON (`message` + `next_hop`) for that hop. |
| Per-layer symmetric key | **RSA-OAEP** (SHA-256, MGF1-SHA256) | Only the 32-byte Fernet key is encrypted to the **next hop’s RSA public key** (2048-bit RSA in `generate_keys`). |
| Package on the wire | Base64-wrapped JSON | Outer envelope contains `k` (RSA-encrypted key) and `p` (Fernet ciphertext). |

* **Encapsulation** repeats for every hop so the payload can be arbitrarily large (bounded by practical RSA/Fernet limits), with **end-to-end onion semantics**: each intermediate only peels **its** layer.

---

## 🔹 Phase 4 – Session Keys + Secure Forwarding (✅ Completed)

**What happens**

* **ECDH at `/init` (entry router only):** `POST /init` on **Router S** generates an **ACI** and runs a **pairwise X25519 handshake** along the fixed path so each link shares a **session key** for that circuit:
  * **S ↔ X** — `POST /session/handshake` on X (S initiates, X responds).
  * **X ↔ Y** — `POST /session/downstream` on X triggers X to initiate handshake with Y.
  * **Y ↔ receiver** — `POST /session/downstream` on Y triggers Y to initiate handshake with **receiverB** (`receiver/app.py` exposes `/session/handshake`).
* **HKDF key derivation:** From each ECDH shared secret, both sides derive a **32-byte link key** with **HKDF-SHA256**, **salt = ACI string**, **info = `anon-link:<sorted node pair>`** (`common/link_session.py` → `derive_link_key`). Keys are **bound to the circuit** without sending ACI on every frame.
* **Link-layer encryption:** After a router **peels its RSA+Fernet onion layer** (Phase 3), the **inner onion string** is encrypted with **AES-256-GCM** (`link_encrypt` / `link_decrypt`) using the **outbound** link key before HTTP forward. The **next** hop **decrypts the link layer first**, then peels its RSA layer.
* **Entry exception:** The sender still posts the **raw outer onion** to Router S (no link decrypt on ingress). **All hops after S** expect **`aci` + link-wrapped `onion`** on `POST /forward` or `POST /receive`.
* **Orchestration URLs** for handshakes live in **`config.py`** → **`NODE_BASES`**.

**Encryption techniques**

| Piece | Algorithm | Role |
|--------|-----------|------|
| Ephemeral ECDH | **X25519** | Per circuit setup between neighbors; forward secrecy for the session key material. |
| Key derivation | **HKDF** (SHA-256), salt = **ACI** | Produces per-link **AES-256** keys tied to the circuit id. |
| Link ciphertext | **AES-256-GCM** (12-byte random nonce, prepended) | Confidentiality + integrity for the forwarded onion blob **between** routers. |
| End-to-end hop privacy (inner) | Phase 3 stack unchanged | RSA-OAEP + Fernet still define the **onion**; Phase 4 adds a **second** layer on the wire between routers. |

**Summary:** Phase 3 protects **who can read which onion layer**; Phase 4 adds **pairwise link encryption** keyed by **ECDH + HKDF** so intermediate HTTP links carry **GCM-protected** payloads for a given **ACI**.

---

## 🔹 Phase 5 – Reverse Trace & Controlled Identity Recovery (✅ Completed)

**What happens**

* Each ME signs **octet fragments** with a **stable RSA keypair** loaded from `keys/ME1_*.pem` / `keys/ME2_*.pem` (generated by `generate_keyring.py`). Signatures are **verifiable** by the Trustee using the matching public PEMs.
* Every `/sign` stores **`position`** (0…3 for IPv4 octets) and **`me_id`** so fragments can be **ordered** and attributed to the correct ME.
* **Authorized release:** `POST /trace/fragments` on each ME (Bearer **`TRACE_AUTH_TOKEN`** from `config.py`) returns that ME’s rows for a **pseudonym** from MongoDB.
* **Orchestrated reconstruction:** `POST /trace/reconstruct` on the **Trustee** (same Bearer token) calls **all ME URLs** in `ME_URLS`, merges rows, **deduplicates by `position`**, **verifies every signature** with `verify_signature`, rebuilds the IP with **`reconstruct_ip`** in `common/shamir.py`, and compares to the **Trustee’s stored `real_ip`** (`ground_truth_match`).
* Helper script: **`trace_request.py <pseudonym>`** for a quick demo after a sender run.

**Cryptography**

| Piece | Role |
|--------|------|
| RSA PKCS1v15 + SHA-256 signatures | ME proves which octet it attested to (same as Phase 1 signing). |
| Ordered reconstruction | `reconstruct_ip([a,b,c,d])` — dotted string; **control** is policy (who gets `TRACE_AUTH_TOKEN`). |

**Limitation (explicit):** The Trustee still stores **plaintext IP** at registration for ground-truth comparison; Phase 5 demonstrates **distributed attestation + verify + rebuild**, not full cryptographic hiding of IP from the Trustee.

---
# 🛠 Tech Stack

* Python 3.x
* Flask (REST services)
* MongoDB (Cloud Atlas)
* Requests (inter-service communication)
* Cryptography: RSA-OAEP, Fernet (AES-256), **X25519**, **HKDF-SHA256**, **AES-GCM** (`common/crypto.py`, `common/link_session.py`)

---

# 📁 Project Structure

```
anon-network/
│
├── benchmark/
│   ├── benchmark.py
│   └── generate_plots.py
│
├── common/
│   ├── __init__.py
│   ├── crypto.py
│   ├── link_session.py
│   └── shamir.py
│
├── me/
│   └── app.py
│
├── receiver/
│   └── app.py
│
├── router/
│   └── app.py
│
├── sender/
│   └── sender.py
│
├── trustee/
│   └── app.py
│
├── .gitignore
├── config.py
├── generate_keyring.py
├── requirements.txt
├── RESEARCH.md
├── verify_link_layer_demo.py
├── startup.sh
├── startup.ps1
├── trace_request.py
├── clean_trace_mongo.py
└── README.md
```

---

# ⚙️ Setup Instructions

## 1️⃣ Create Virtual Environment (Windows)

```powershell
python -m venv .venv
.venv\Scripts\activate
```

## 2️⃣ Install Dependencies

```powershell
pip install flask pymongo cryptography requests
```

---

## 3️⃣ Configure MongoDB

Update `config.py`:

```python
MONGO_URI = "your_mongodb_atlas_uri"
DB_NAME = "anon_network"
```

Ensure:

* Atlas IP whitelist includes your IP
* DB user has read/write permissions

---

# 🚀 How To Run the System

Set **`PYTHONPATH`** to the project root so `common` and `config` resolve (`export PYTHONPATH=.` on Bash/WSL, `$env:PYTHONPATH="."` on PowerShell).

## Step 1 — Start all nodes

**Git Bash / WSL / Linux**

```bash
export PYTHONPATH=.
./startup.sh
```

**Windows PowerShell (opens one `cmd` window per service for logs)**

```powershell
$env:PYTHONPATH="."
.\startup.ps1
```

## Step 2 — Run the sender

In a **second** terminal (same folder):

```powershell
$env:PYTHONPATH="."
python -m sender.sender
```

* **Sender terminal:** Phase 1–2 banner, then Phase 3–4 banner, **ACI**, “Baking hybrid onion…”, **Forward HTTP 200**.
* **Router / receiver windows:** Phase 4 **ECDH** lines during `/init`, then **link AES-GCM** + **RSA peel** logs on forward; **Receiver** prints **SUCCESS** with message and fragment count.

## Alternatively

Start each service manually in separate terminals (see sections below) with the correct `PORT` and `NODE_NAME`.

---

## 🟢 Generating Keyring

```powershell
$env:PYTHONPATH = "."
python generate_keyring.py
```

## 🟢 Start Receiver

```powershell
python -m receiver.app
```

Runs on: `http://127.0.0.1:7000`

---

## 🟢 Start Router Y

```powershell
$env:PORT="6003"
$env:NEXT_HOP="http://127.0.0.1:7000"
python -m router.app
```

---

## 🟢 Start Router X

```powershell
$env:PORT="6002"
$env:NEXT_HOP="http://127.0.0.1:6003"
python -m router.app
```

---

## 🟢 Start Router S (Entry Router)

```powershell
$env:PORT="6001"
$env:NEXT_HOP="http://127.0.0.1:6002"
python -m router.app
```

---

## 🟢 Start Trustee

```powershell
python -m trustee.app
```

---

## 🟢 Start ME1

```powershell
$env:PORT="5001"
python -m me.app
```

---

## 🟢 Start ME2

```powershell
$env:PORT="5002"
python -m me.app
```

---

## 🟢 Run Sender

```powershell
$env:PYTHONPATH="."
python -m sender.sender
```

---

# 🎬 Expected Output

* Trustee registers sender (pseudonym + IP mapping in MongoDB)
* ME servers sign each IP fragment (RSA signatures)
* **Phase 4:** Router S **`/init`** completes **ECDH** handshakes S↔X, X↔Y, Y↔receiver; session keys stored per **ACI**
* Sender builds **hybrid onion** (Phase 3) and **`POST /forward`** with **`onion` + `aci`**
* Each router: **link decrypt** (except entry) → **RSA+Fernet peel** → **link encrypt** to next hop
* Receiver: **link decrypt** → **final peel** → prints **SUCCESS**, **ACI**, **message**, **fragment count**

Example (receiver):

```
[Receiver] SUCCESS: Onion Decapsulated
[*] ACI: ACI-xxxxxxxx
[*] Msg: Hello from Circuit
[*] Fragments: 4
```

**Phase 5 (after a successful sender run):** note the **pseudonym** (e.g. `PA-df8b5545`), then:

```powershell
$env:PYTHONPATH="."
python trace_request.py PA-xxxxxxxx
```

Expect JSON with **`reconstructed_ip`**, **`trustee_ground_truth_ip`**, and **`ground_truth_match`: true** when ME keys match `keys/ME{1,2}_*.pem` and Mongo has all four signed positions.

**If trace returns `signature verification failed`:** MongoDB may still hold **old** fragment rows signed before MEs used PEM keys, or keys were regenerated without clearing data. **Restart ME + Trustee** after pulling fixes, then either run again (the Trustee picks the **newest** row per position that verifies) or wipe attestations: `PYTHONPATH=. python clean_trace_mongo.py`, then run **`sender`** again and trace the **new** pseudonym.

---

# 🧠 What The System Currently Simulates

* Circuit-based anonymous routing (fixed path in `config`; sender builds the onion)
* Distributed identity validation (Trustee + ME signatures)
* **Hybrid onion (RSA-OAEP + Fernet)** and **per-link session encryption (X25519 + HKDF + AES-GCM)** for a given **ACI**
* Stateful connection management (per-circuit keys on each node)
* Multi-hop communication model
* **Controlled reverse trace** after policy (Bearer token): fragment collection, signature checks, IP reconstruction

---

# 🎓 Research & Performance Evaluation

This repository includes a dedicated suite for academic benchmarking and security verification, making it suitable for research papers (e.g., IEEE/ACM style).

### 1. Performance Benchmarking
Measure the latency overhead of each cryptographic phase (RSA, AES, ECDH) and system stage.
```powershell
python benchmark/benchmark.py
python benchmark/generate_plots.py
```
**Generated Plots:**
- `benchmark/latency_breakdown.png`: Comparison of Registration, Setup, and Trace times.
- `benchmark/crypto_performance.png`: Raw overhead of individual cryptographic primitives.

### 2. Formal Security Proofs
Verify the "Pairwise Link Security" property (Phase 4) using a standalone proof script.
```powershell
python verify_link_layer_demo.py
```
This script proves that without the correct ephemeral key or ACI salt, intermediate neighbors cannot recover the encrypted onion layers.

---

# 🎓 Academic Significance

This project demonstrates:

* **Distributed Accountability**: Identity validation via Trustee and Management Entities (MEs).
* **Cryptographic Layering**: Hybrid onion (RSA-OAEP + Fernet) combined with per-link session encryption (X25519 + HKDF + AES-GCM).
* **Controlled Traceability**: Reconstructing identity from distributed fragments only upon authorization (Phase 5).
* **Microservice Security**: Independent trust boundaries between identity, routing, and reception layers.

---

# 🏁 Current Status

✔ **Phase 1 Completed** — Identity & validation (Trustee, ME signatures, MongoDB)
✔ **Phase 2A Completed** — Multi-hop REST routing
✔ **Phase 2B Completed** — ACI + `/init` + routing table
✔ **Phase 3 Completed** — Hybrid onion (RSA-OAEP + AES-256 Fernet per hop)
✔ **Phase 4 Completed** — X25519 ECDH at `/init`, HKDF (ACI-bound), AES-GCM link forwarding
✔ **Phase 5 Completed** — Authorized trace: ME `/trace/fragments`, Trustee `/trace/reconstruct`, RSA signature verification, IP reconstruction
✔ **Research Suite Completed** — Benchmarking scripts, security proofs, and automated visualization
