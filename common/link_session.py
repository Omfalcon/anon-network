"""X25519 ECDH + HKDF link keys and AES-GCM framing between hops (Phase 4)."""

from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


def generate_x25519_pair() -> tuple[X25519PrivateKey, X25519PublicKey]:
    priv = X25519PrivateKey.generate()
    return priv, priv.public_key()


def public_key_to_b64(pub: X25519PublicKey) -> str:
    raw = pub.public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)
    return base64.b64encode(raw).decode("ascii")


def b64_to_public_key(b64: str) -> X25519PublicKey:
    raw = base64.b64decode(b64)
    return X25519PublicKey.from_public_bytes(raw)


def derive_link_key(shared_secret: bytes, aci: str, node_a: str, node_b: str) -> bytes:
    pair = "|".join(sorted([node_a, node_b]))
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=aci.encode("utf-8"),
        info=f"anon-link:{pair}".encode("utf-8"),
    )
    return hkdf.derive(shared_secret)


def link_encrypt(key: bytes, plaintext: bytes) -> str:
    aes = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aes.encrypt(nonce, plaintext, None)
    return base64.b64encode(nonce + ciphertext).decode("ascii")


def link_decrypt(key: bytes, token_b64: str) -> bytes:
    raw = base64.b64decode(token_b64)
    nonce, ciphertext = raw[:12], raw[12:]
    aes = AESGCM(key)
    return aes.decrypt(nonce, ciphertext, None)
