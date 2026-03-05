import base64
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

from app.config import get_settings


backend = default_backend()
settings = get_settings()


def _get_aes_key() -> bytes:
    # Derive a 32-byte key from the configured encryption_key string
    digest = hashes.Hash(hashes.SHA256(), backend=backend)
    digest.update(settings.encryption_key.encode("utf-8"))
    return digest.finalize()


@dataclass
class EncryptedPayload:
    ciphertext: str
    nonce: str
    tag: str


def encrypt_bytes(plaintext: bytes) -> EncryptedPayload:
    key = _get_aes_key()
    nonce = os.urandom(12)
    encryptor = Cipher(
        algorithms.AES(key),
        modes.GCM(nonce),
        backend=backend,
    ).encryptor()
    ciphertext = encryptor.update(plaintext) + encryptor.finalize()
    return EncryptedPayload(
        ciphertext=base64.b64encode(ciphertext).decode("utf-8"),
        nonce=base64.b64encode(nonce).decode("utf-8"),
        tag=base64.b64encode(encryptor.tag).decode("utf-8"),
    )


def decrypt_bytes(ciphertext_b64: str, nonce_b64: str, tag_b64: str) -> bytes:
    key = _get_aes_key()
    ciphertext = base64.b64decode(ciphertext_b64)
    nonce = base64.b64decode(nonce_b64)
    tag = base64.b64decode(tag_b64)
    decryptor = Cipher(
        algorithms.AES(key),
        modes.GCM(nonce, tag),
        backend=backend,
    ).decryptor()
    return decryptor.update(ciphertext) + decryptor.finalize()


def encrypt_text(plaintext: str) -> EncryptedPayload:
    return encrypt_bytes(plaintext.encode("utf-8"))


def decrypt_text(ciphertext_b64: str, nonce_b64: str, tag_b64: str) -> str:
    return decrypt_bytes(ciphertext_b64, nonce_b64, tag_b64).decode("utf-8")

