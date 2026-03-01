# 🧅 Anon-Network

### Reverse Onion Routing – Phase 1 & Phase 2 Implementation

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
* Circuit establishment using ACI
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

* Sender registers with Trustee
* IP address is fragmented
* Each fragment is signed by distributed ME servers
* MongoDB stores identity and fragment mappings
* Multiple ME instances supported
* REST-based microservice communication

### Achievements

✔ Distributed trust
✔ Fragment-based identity protection
✔ Digital signature validation
✔ Cloud MongoDB integration

---

## 🔹 Phase 2A – Multi-Hop Routing

* Built independent router services
* Configured routers using environment variables
* Implemented REST-based forwarding
* Simulated multi-terminal distributed network

Message flow:

```
Sender → Router S → Router X → Router Y → Receiver
```

---

## 🔹 Phase 2B – Circuit Establishment (ACI)

* Added Anonymous Connection Identifier (ACI)
* Implemented `/init` endpoint for circuit setup
* Distributed ACI propagation across routers
* Per-router routing table implementation
* Stateful message forwarding

Now the system behaves as a circuit-based anonymous network.

---

# 🛠 Tech Stack

* Python 3.x
* Flask (REST services)
* MongoDB (Cloud Atlas)
* Requests (inter-service communication)
* Cryptography (RSA signing)

---

# 📁 Project Structure

```
anon-network/
│
├── config.py
├── common/
│   ├── crypto.py
│   └── shamir.py
│
├── trustee/
│   └── app.py
│
├── me/
│   └── app.py
│
├── router/
│   └── app.py
│
├── receiver/
│   └── app.py
│
├── sender/
│   └── sender.py
│
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

Open multiple PowerShell terminals.

---

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
python -m sender.sender
```

---

# 🎬 Expected Output

* Trustee registers sender
* ME servers sign fragments
* Router S initializes ACI
* ACI propagates to all routers
* Message flows across routers
* Receiver prints final message

Example:

```
[Receiver] ACI ACI-xxxx → Message: Hello Anonymous Circuit
```

---

# 🧠 What The System Currently Simulates

* Circuit-based anonymous routing
* Distributed identity validation
* Stateful connection management
* Multi-hop communication model

---

# 🚧 Remaining Phases

## 🔐 Phase 3 – Onion Layered Encryption

* Add multi-layer encryption
* Each router decrypts one layer

## 🔑 Phase 4 – Session Keys

* Per-hop encryption
* Secure payload forwarding

## 🔄 Phase 5 – Reverse Trace Mechanism

* IP reconstruction using fragments
* Controlled identity recovery

## 🤖 Phase 6 – Neural Network Integration (Optional)

* Malicious traffic detection
* Abuse-triggered trace

---

# 🎓 Academic Significance

This project demonstrates:

* Distributed systems design
* Microservice architecture
* Cryptographic identity validation
* Circuit-based anonymous communication
* Reverse traceable anonymity

# 🏁 Current Status

✔ Phase 1 Completed
✔ Phase 2A Completed
✔ Phase 2B Completed
