# common/crypto.py

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
import base64
import json

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
#single layer encryption using the recipient's public key.
    json_data = json.dumps(data).encode()
    encrypted = public_key.encrypt(
        json_data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return base64.b64encode(encrypted).decode()

def decrypt_layer(private_key, encrypted_base64: str) -> dict:
#Decrypts a single layer using node's private key.
    encrypted_data = base64.b64decode(encrypted_base64)
    decrypted = private_key.decrypt(
        encrypted_data,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )
    return json.loads(decrypted.decode())

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