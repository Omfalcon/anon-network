#!/bin/bash

# 1. Cleanup: Kill any existing python processes on the network ports
echo "Cleaning up existing network processes..."
fuser -k 5000/tcp 5001/tcp 5002/tcp 6001/tcp 6002/tcp 6003/tcp 6004/tcp 7000/tcp 2>/dev/null

# 2. Environment Setup: Set root directory for module imports
export PYTHONPATH=$PYTHONPATH:$(pwd)

# 3. Provisioning: Generate the Keyring
echo "Generating fresh RSA Keyring for Phase 3..."
python generate_keyring.py

if [ $? -ne 0 ]; then
    echo "Error: Keyring generation failed. Aborting startup."
    exit 1
fi

echo "Starting Anon-Network Phase 3 Nodes..."

# 4. Start the Trustee (Identity Mapping)
PORT=5000 python trustee/app.py & 
sleep 1

# 5. Start Management Entities (Distributed Signing)
PORT=5001 NODE_NAME=ME1 python me/app.py &
PORT=5002 NODE_NAME=ME2 python me/app.py &
sleep 1

# 6. Start Onion Routers (S, X, Y)
PORT=6001 NODE_NAME=routerS python router/app.py &
PORT=6002 NODE_NAME=routerX python router/app.py &
PORT=6003 NODE_NAME=routerY python router/app.py &
sleep 1

# 7. Start the Receiver
PORT=7000 NODE_NAME=receiverB python receiver/app.py &

echo "----------------------------------------------------------------"
echo "All nodes are live with fresh keys. Run 'python -m sender.sender'"
echo "----------------------------------------------------------------"

# Keep script alive for background processes
wait