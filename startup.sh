#!/bin/bash

#Kill any existing python processes on our ports
fuser -k 5000/tcp 5001/tcp 5002/tcp 6001/tcp 6002/tcp 6003/tcp 7000/tcp 2>/dev/null

echo "Starting Anon-Network Phase 3..."

#root directory for imports
export PYTHONPATH=$PYTHONPATH:.

# 1. Start the Trustee (Port 5000)
PORT=5000 python trustee/app.py & 
sleep 1

# 2. Start Management Entities (Port 5001, 5002)
PORT=5001 NODE_NAME=ME1 python me/app.py &
PORT=5002 NODE_NAME=ME2 python me/app.py &
sleep 1

# 3. Start Onion Routers (S, X, Y)
# These names must match your .pem filenames in /keys
PORT=6001 NODE_NAME=routerS python router/app.py &
PORT=6002 NODE_NAME=routerX python router/app.py &
PORT=6003 NODE_NAME=routerY python router/app.py &
sleep 1

# 4. Start the Receiver
PORT=6004 NODE_NAME=receiverB python receiver/app.py &

echo "All nodes are live. Run 'python sender/sender.py' in a new terminal."

#Keeps the script running so the background processes don't die
wait