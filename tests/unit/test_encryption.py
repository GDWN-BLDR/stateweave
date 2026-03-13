"""
Unit Tests: Encryption Facade
================================
Encrypt/decrypt round-trips, key rotation, error handling.
"""

import pytest

from stateweave.core.encryption import EncryptionError, EncryptionFacade


class TestEncryptionFacade:
    @pytest.fixture
    def facade(self):
        key = EncryptionFacade.generate_key()
        return EncryptionFacade(key)

    @pytest.fixture
    def passphrase_facade(self):
        return EncryptionFacade.from_passphrase("test-passphrase-12345")

    def test_generate_key(self):
        key = EncryptionFacade.generate_key()
        assert len(key) == 32  # 256 bits

    def test_invalid_key_size(self):
        with pytest.raises(EncryptionError, match="Key must be 32 bytes"):
            EncryptionFacade(b"too-short")

    def test_encrypt_decrypt_roundtrip(self, facade):
        plaintext = b"Hello, StateWeave!"
        ciphertext, nonce = facade.encrypt(plaintext)
        decrypted = facade.decrypt(ciphertext, nonce)
        assert decrypted == plaintext

    def test_encrypt_large_payload(self, facade):
        plaintext = b"x" * 1_000_000  # 1MB
        ciphertext, nonce = facade.encrypt(plaintext)
        decrypted = facade.decrypt(ciphertext, nonce)
        assert decrypted == plaintext

    def test_encrypt_empty_data(self, facade):
        ciphertext, nonce = facade.encrypt(b"")
        decrypted = facade.decrypt(ciphertext, nonce)
        assert decrypted == b""

    def test_unique_nonce_per_operation(self, facade):
        _, nonce1 = facade.encrypt(b"data1")
        _, nonce2 = facade.encrypt(b"data2")
        assert nonce1 != nonce2  # Each op gets unique nonce

    def test_wrong_key_fails(self):
        key1 = EncryptionFacade.generate_key()
        key2 = EncryptionFacade.generate_key()
        facade1 = EncryptionFacade(key1)
        facade2 = EncryptionFacade(key2)

        ciphertext, nonce = facade1.encrypt(b"secret")
        with pytest.raises(EncryptionError, match="Decryption failed"):
            facade2.decrypt(ciphertext, nonce)

    def test_tampered_data_fails(self, facade):
        ciphertext, nonce = facade.encrypt(b"sensitive data")
        tampered = bytearray(ciphertext)
        tampered[0] ^= 0xFF  # Flip bits
        with pytest.raises(EncryptionError, match="Decryption failed"):
            facade.decrypt(bytes(tampered), nonce)

    def test_associated_data(self, facade):
        aad = b"metadata:agent-123"
        ciphertext, nonce = facade.encrypt(b"payload", aad)
        decrypted = facade.decrypt(ciphertext, nonce, aad)
        assert decrypted == b"payload"

    def test_wrong_associated_data_fails(self, facade):
        aad = b"metadata:agent-123"
        ciphertext, nonce = facade.encrypt(b"payload", aad)
        with pytest.raises(EncryptionError):
            facade.decrypt(ciphertext, nonce, b"wrong-aad")

    def test_passphrase_roundtrip(self, passphrase_facade):
        plaintext = b"encrypted with passphrase"
        ciphertext, nonce = passphrase_facade.encrypt(plaintext)
        decrypted = passphrase_facade.decrypt(ciphertext, nonce)
        assert decrypted == plaintext

    def test_key_id_is_stable(self, facade):
        assert isinstance(facade.key_id, str)
        assert len(facade.key_id) == 16  # SHA-256 truncated to 16 hex chars

    def test_b64_encrypt_decrypt(self, facade):
        plaintext = b"base64 transport test"
        b64_ct, b64_nonce = facade.encrypt_b64(plaintext)
        decrypted = facade.decrypt_b64(b64_ct, b64_nonce)
        assert decrypted == plaintext
        assert isinstance(b64_ct, str)  # JSON-safe
        assert isinstance(b64_nonce, str)

    def test_different_passphrases_different_keys(self):
        f1 = EncryptionFacade.from_passphrase("pass1", salt=b"x" * 16)
        f2 = EncryptionFacade.from_passphrase("pass2", salt=b"x" * 16)
        assert f1.key_id != f2.key_id
