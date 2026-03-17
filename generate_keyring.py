# generate_keyring.py
import os
import sys

# Step 1: Force the current directory into the path so it finds 'common'
sys.path.append(os.getcwd())

try:
    from common.crypto import generate_keys, serialize_public_key
    from cryptography.hazmat.primitives import serialization
    print("Crypto modules loaded successfully.")
except ImportError as e:
    print(f"Import Error: {e}")
    print("Ensure you have 'common/crypto.py' and an empty 'common/__init__.py' file.")
    sys.exit(1)

def save_keypair(node_name):
    key_dir = 'keys'
    if not os.path.exists(key_dir):
        os.makedirs(key_dir)
        print(f"Created directory: {key_dir}")
        
    priv, pub = generate_keys()
    
    # Save Private Key
    priv_path = f"{key_dir}/{node_name}_priv.pem"
    with open(priv_path, "wb") as f:
        f.write(priv.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
        
    # Save Public Key
    pub_path = f"{key_dir}/{node_name}_pub.pem"
    with open(pub_path, "wb") as f:
        f.write(serialize_public_key(pub).encode())
    
    print(f"Keys generated for: {node_name}")

if __name__ == "__main__":
    nodes = ["routerS", "routerX", "routerY", "receiverB", "trustee", "ME1", "ME2"]
    print(f"Starting keyring generation for {len(nodes)} nodes...")
    
    for node in nodes:
        save_keypair(node)
        
    print("\n Done! Check the 'keys/' directory for your PEM files.")