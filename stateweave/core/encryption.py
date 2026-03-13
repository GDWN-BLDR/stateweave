"""
Encryption Facade — AES-256-GCM AEAD encryption for state payloads.
=====================================================================
[LAW 5] All sensitive state transiting any boundary MUST be encrypted
through this facade. No raw cryptography calls elsewhere.
"""

import base64
import hashlib
import logging
import os
import secrets
from typing import Optional, Tuple

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger("stateweave.core.encryption")

# Constants
NONCE_SIZE = 12  # 96 bits for AES-GCM
KEY_SIZE = 32  # 256 bits for AES-256
SALT_SIZE = 16  # 128 bits for PBKDF2 salt
ITERATIONS = 600_000  # OWASP recommended for PBKDF2-SHA256


class EncryptionError(Exception):
    """Raised when encryption or decryption fails."""

    pass


class EncryptionFacade:
    """AES-256-GCM Authenticated Encryption with Associated Data (AEAD).

    Provides:
    - AES-256-GCM authenticated encryption
    - Unique nonce per encryption operation
    - Key derivation from passphrase (PBKDF2)
    - Key rotation via versioned key IDs

    Usage:
        # From passphrase
        facade = EncryptionFacade.from_passphrase("my-secret-key")
        ciphertext, nonce = facade.encrypt(plaintext_bytes)
        decrypted = facade.decrypt(ciphertext, nonce)

        # From raw key
        key = EncryptionFacade.generate_key()
        facade = EncryptionFacade(key)
    """

    def __init__(self, key: bytes, key_id: Optional[str] = None):
        """Initialize the encryption facade with a raw AES-256 key.

        Args:
            key: 32-byte AES-256 key.
            key_id: Optional key identifier for rotation tracking.

        Raises:
            EncryptionError: If key size is invalid.
        """
        if len(key) != KEY_SIZE:
            raise EncryptionError(f"Key must be {KEY_SIZE} bytes, got {len(key)}")
        self._key = key
        self._aesgcm = AESGCM(key)
        self._key_id = key_id or self._compute_key_id(key)

    @classmethod
    def from_passphrase(
        cls,
        passphrase: str,
        salt: Optional[bytes] = None,
        key_id: Optional[str] = None,
    ) -> "EncryptionFacade":
        """Create an EncryptionFacade from a passphrase using PBKDF2.

        Args:
            passphrase: Human-readable passphrase.
            salt: Optional salt bytes. Generated if not provided.
            key_id: Optional key identifier.

        Returns:
            EncryptionFacade instance.
        """
        if salt is None:
            salt = os.urandom(SALT_SIZE)

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=salt,
            iterations=ITERATIONS,
        )
        key = kdf.derive(passphrase.encode("utf-8"))
        instance = cls(key, key_id=key_id)
        instance._salt = salt
        return instance

    @staticmethod
    def generate_key() -> bytes:
        """Generate a cryptographically secure random AES-256 key."""
        return secrets.token_bytes(KEY_SIZE)

    @property
    def key_id(self) -> str:
        """Get the key identifier."""
        return self._key_id

    def encrypt(
        self,
        plaintext: bytes,
        associated_data: Optional[bytes] = None,
    ) -> Tuple[bytes, bytes]:
        """Encrypt plaintext using AES-256-GCM.

        Args:
            plaintext: The data to encrypt.
            associated_data: Additional data to authenticate but not encrypt.

        Returns:
            Tuple of (ciphertext, nonce). Both needed for decryption.

        Raises:
            EncryptionError: If encryption fails.
        """
        try:
            nonce = os.urandom(NONCE_SIZE)
            ciphertext = self._aesgcm.encrypt(nonce, plaintext, associated_data)
            return ciphertext, nonce
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}") from e

    def decrypt(
        self,
        ciphertext: bytes,
        nonce: bytes,
        associated_data: Optional[bytes] = None,
    ) -> bytes:
        """Decrypt ciphertext using AES-256-GCM.

        Args:
            ciphertext: The encrypted data.
            nonce: The nonce used during encryption.
            associated_data: The same associated data used during encryption.

        Returns:
            Decrypted plaintext bytes.

        Raises:
            EncryptionError: If decryption fails (wrong key, tampered data, etc.).
        """
        try:
            return self._aesgcm.decrypt(nonce, ciphertext, associated_data)
        except Exception as e:
            raise EncryptionError(f"Decryption failed (wrong key or tampered data): {e}") from e

    def encrypt_b64(
        self,
        plaintext: bytes,
        associated_data: Optional[bytes] = None,
    ) -> Tuple[str, str]:
        """Encrypt and return base64-encoded ciphertext and nonce.

        Convenient for JSON-safe transport.

        Returns:
            Tuple of (b64_ciphertext, b64_nonce).
        """
        ciphertext, nonce = self.encrypt(plaintext, associated_data)
        return (
            base64.b64encode(ciphertext).decode("ascii"),
            base64.b64encode(nonce).decode("ascii"),
        )

    def decrypt_b64(
        self,
        b64_ciphertext: str,
        b64_nonce: str,
        associated_data: Optional[bytes] = None,
    ) -> bytes:
        """Decrypt base64-encoded ciphertext and nonce.

        Args:
            b64_ciphertext: Base64-encoded ciphertext.
            b64_nonce: Base64-encoded nonce.
            associated_data: Associated data used during encryption.

        Returns:
            Decrypted plaintext bytes.
        """
        ciphertext = base64.b64decode(b64_ciphertext)
        nonce = base64.b64decode(b64_nonce)
        return self.decrypt(ciphertext, nonce, associated_data)

    @staticmethod
    def _compute_key_id(key: bytes) -> str:
        """Compute a stable key ID from the key bytes (SHA-256 truncated)."""
        return hashlib.sha256(key).hexdigest()[:16]

    # ── Ed25519 Digital Signatures ────────────────────────────────

    @staticmethod
    def generate_signing_keypair() -> tuple:
        """Generate an Ed25519 signing key pair.

        Returns:
            Tuple of (private_key_bytes, public_key_bytes) — both raw 32-byte keys.
        """
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        private_key = Ed25519PrivateKey.generate()
        private_bytes = private_key.private_bytes_raw()
        public_bytes = private_key.public_key().public_bytes_raw()
        return private_bytes, public_bytes

    @staticmethod
    def sign(data: bytes, private_key_bytes: bytes) -> str:
        """Sign data with Ed25519 and return base64-encoded signature.

        Args:
            data: The bytes to sign (typically serialized payload JSON).
            private_key_bytes: 32-byte Ed25519 private key.

        Returns:
            Base64-encoded signature string.
        """
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
        signature = private_key.sign(data)
        return base64.b64encode(signature).decode("utf-8")

    @staticmethod
    def verify(data: bytes, signature_b64: str, public_key_bytes: bytes) -> bool:
        """Verify an Ed25519 signature.

        Args:
            data: The original bytes that were signed.
            signature_b64: Base64-encoded signature to verify.
            public_key_bytes: 32-byte Ed25519 public key.

        Returns:
            True if signature is valid, False otherwise.
        """
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        try:
            public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
            signature = base64.b64decode(signature_b64)
            public_key.verify(signature, data)
            return True
        except InvalidSignature:
            logger.warning("Payload signature verification failed — possible tampering")
            return False
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False
