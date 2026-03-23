# common/crypto.py

import base64
import json
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.fernet import Fernet

def generate_keys():
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )
    public_key = private_key.public_key()
    return private_key, public_key


def sign_data(private_key, data: str) -> str:
    signature = private_key.sign(
        data.encode(),
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode()


def verify_signature(public_key, data: str, signature: str) -> bool:
    try:
        public_key.verify(
            base64.b64decode(signature),
            data.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except:
        return False


def serialize_public_key(public_key):
    return public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()


def load_public_key(pem_data: str):
    return serialization.load_pem_public_key(pem_data.encode())

def encrypt_layer(public_key, data: dict) -> str:
    # 1. Generate a one-time symmetric AES key
    sym_key = Fernet.generate_key()
    f = Fernet(sym_key)
    
    # 2. Encrypt the actual payload with the AES key
    payload_json = json.dumps(data).encode()
    encrypted_payload = f.encrypt(payload_json)
    
    # 3. Encrypt the AES key with the RSA Public Key
    encrypted_sym_key = public_key.encrypt(
        sym_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    # 4. Bundle them together in a JSON package
    package = {
        "k": base64.b64encode(encrypted_sym_key).decode(),
        "p": base64.b64encode(encrypted_payload).decode()
    }
    return base64.b64encode(json.dumps(package).encode()).decode()

def decrypt_layer(private_key, encrypted_base64: str) -> dict:
    # 1. Decode the outer package
    package = json.loads(base64.b64decode(encrypted_base64).decode())
    
    # 2. Decrypt the AES key using the RSA Private Key
    encrypted_key_bytes = base64.b64decode(package['k'])
    sym_key = private_key.decrypt(
        encrypted_key_bytes,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    
    # 3. Decrypt the actual payload using the AES key
    f = Fernet(sym_key)
    encrypted_payload_bytes = base64.b64decode(package['p'])
    
    # Fernet.decrypt expects bytes, returns bytes
    decrypted_bytes = f.decrypt(encrypted_payload_bytes)
    
    # 4. Convert bytes back to JSON dict
    return json.loads(decrypted_bytes.decode('utf-8'))

def create_onion(final_message: str, hops: list) -> str:
    """
    Constructs the full onion.
    hops: List of tuples [(public_key_B, None), (public_key_Y, url_B), (public_key_X, url_Y), (public_key_S, url_X)]
    Note: We wrap from the inside (Receiver) to the outside (Agent Router).
    """
    current_layer = final_message
    
    for pub_key, next_hop in hops:
        # Each layer contains the data for the next hop and the encrypted inner onion
        data_to_encrypt = {
            "message": current_layer,
            "next_hop": next_hop
        }
        current_layer = encrypt_layer(pub_key, data_to_encrypt)
        
    return current_layer

def load_private_key(node_name):
#Loads a private key from the keys/ directory
    with open(f"keys/{node_name}_priv.pem", "rb") as f:
        return serialization.load_pem_private_key(
            f.read(),
            password=None
        )

def load_public_key_from_file(node_name):
#Loads a public key from the keys/ directory
    with open(f"keys/{node_name}_pub.pem", "rb") as f:
        return serialization.load_pem_public_key(f.read())