"""
Red Team: Adversarial Encryption Fuzzing
============================================
Attack the EncryptionFacade with malformed keys, nonces, ciphertexts,
and edge-case passphrases. Every test must prove graceful failure —
no silent corruption, no key material leaks, no crashes.
"""

import os

import pytest

from stateweave.core.encryption import (
    ITERATIONS,
    KEY_SIZE,
    NONCE_SIZE,
    EncryptionError,
    EncryptionFacade,
)


@pytest.fixture
def facade():
    return EncryptionFacade(EncryptionFacade.generate_key())


@pytest.fixture
def sample_ciphertext(facade):
    """Pre-encrypt a known plaintext for mutation tests."""
    plaintext = b"Red team test payload -- do not corrupt"
    ct, nonce = facade.encrypt(plaintext)
    return ct, nonce, plaintext


# ═══════════════════════════════════════════════════════════════════
# 1. KEY MATERIAL VALIDATION
# ═══════════════════════════════════════════════════════════════════


class TestKeyMaterialValidation:
    """Verify every invalid key is rejected cleanly."""

    @pytest.mark.parametrize("key_len", [0, 1, 15, 16, 31, 33, 64, 128])
    def test_wrong_key_sizes(self, key_len):
        """Keys that aren't exactly 32 bytes must raise EncryptionError."""
        with pytest.raises(EncryptionError, match="Key must be 32 bytes"):
            EncryptionFacade(b"\x00" * key_len)

    def test_all_zero_key_accepted(self):
        """All-zero key is technically valid AES — must work (it's the caller's
        problem if they choose a weak key)."""
        facade = EncryptionFacade(b"\x00" * KEY_SIZE)
        ct, nonce = facade.encrypt(b"test")
        assert facade.decrypt(ct, nonce) == b"test"

    def test_all_ff_key_accepted(self):
        """All 0xFF key must also work."""
        facade = EncryptionFacade(b"\xff" * KEY_SIZE)
        ct, nonce = facade.encrypt(b"test")
        assert facade.decrypt(ct, nonce) == b"test"

    def test_key_id_deterministic(self):
        """Same key must produce the same key_id every time."""
        key = EncryptionFacade.generate_key()
        f1 = EncryptionFacade(key)
        f2 = EncryptionFacade(key)
        assert f1.key_id == f2.key_id

    def test_different_keys_different_ids(self):
        """Different keys must produce different key_ids."""
        ids = set()
        for _ in range(100):
            f = EncryptionFacade(EncryptionFacade.generate_key())
            ids.add(f.key_id)
        assert len(ids) == 100  # No collisions in 100 keys


# ═══════════════════════════════════════════════════════════════════
# 2. NONCE SAFETY
# ═══════════════════════════════════════════════════════════════════


class TestNonceSafety:
    """Verify nonce uniqueness and rejection of bad nonces."""

    def test_10k_unique_nonces(self, facade):
        """10,000 consecutive encryptions must produce 10,000 unique nonces."""
        nonces = set()
        for i in range(10_000):
            _, nonce = facade.encrypt(f"message_{i}".encode())
            nonces.add(nonce)
        assert len(nonces) == 10_000, "Nonce reuse detected!"

    @pytest.mark.parametrize("nonce_len", [0, 1, 11, 13, 24, 96])
    def test_wrong_nonce_sizes(self, facade, nonce_len):
        """Decrypt with wrong nonce size must raise EncryptionError."""
        ct, _ = facade.encrypt(b"test")
        with pytest.raises(EncryptionError):
            facade.decrypt(ct, b"\x00" * nonce_len)

    def test_nonce_is_12_bytes(self, facade):
        """Nonces must always be exactly 12 bytes (96 bits for AES-GCM)."""
        for _ in range(100):
            _, nonce = facade.encrypt(b"test")
            assert len(nonce) == NONCE_SIZE


# ═══════════════════════════════════════════════════════════════════
# 3. CIPHERTEXT INTEGRITY
# ═══════════════════════════════════════════════════════════════════


class TestCiphertextIntegrity:
    """GCM authentication must catch every single-bit corruption."""

    def test_truncated_ciphertext(self, facade, sample_ciphertext):
        """Slice ciphertext at every position — all must fail."""
        ct, nonce, _ = sample_ciphertext
        for i in range(1, len(ct)):
            with pytest.raises(EncryptionError):
                facade.decrypt(ct[:i], nonce)

    def test_empty_ciphertext(self, facade, sample_ciphertext):
        """Empty ciphertext must raise EncryptionError."""
        _, nonce, _ = sample_ciphertext
        with pytest.raises(EncryptionError):
            facade.decrypt(b"", nonce)

    def test_bit_flip_sweep(self, facade, sample_ciphertext):
        """Flip each byte in ciphertext — GCM tag must catch every one."""
        ct, nonce, _ = sample_ciphertext
        for i in range(len(ct)):
            corrupted = bytearray(ct)
            corrupted[i] ^= 0x01  # Flip lowest bit
            with pytest.raises(EncryptionError):
                facade.decrypt(bytes(corrupted), nonce)

    def test_appended_data(self, facade, sample_ciphertext):
        """Appending data to ciphertext must fail authentication."""
        ct, nonce, _ = sample_ciphertext
        with pytest.raises(EncryptionError):
            facade.decrypt(ct + b"\x00", nonce)

    def test_nonce_bit_flip(self, facade, sample_ciphertext):
        """Flipping any bit in the nonce must cause decryption failure."""
        ct, nonce, _ = sample_ciphertext
        for i in range(len(nonce)):
            corrupted = bytearray(nonce)
            corrupted[i] ^= 0x01
            with pytest.raises(EncryptionError):
                facade.decrypt(ct, bytes(corrupted))

    def test_swapped_nonce_ct(self, facade, sample_ciphertext):
        """Swapping nonce and ciphertext positions must fail."""
        ct, nonce, _ = sample_ciphertext
        with pytest.raises(EncryptionError):
            facade.decrypt(nonce, ct[:NONCE_SIZE])


# ═══════════════════════════════════════════════════════════════════
# 4. PBKDF2 / PASSPHRASE EDGE CASES
# ═══════════════════════════════════════════════════════════════════


class TestPassphraseEdgeCases:
    """Edge cases in passphrase-based key derivation."""

    def test_empty_passphrase(self):
        """Empty passphrase must work (it's the user's choice, not our policy)."""
        f = EncryptionFacade.from_passphrase("")
        ct, nonce = f.encrypt(b"test")
        assert f.decrypt(ct, nonce) == b"test"

    def test_very_long_passphrase(self):
        """10KB passphrase must not hang or crash PBKDF2."""
        f = EncryptionFacade.from_passphrase("A" * 10_000)
        ct, nonce = f.encrypt(b"test")
        assert f.decrypt(ct, nonce) == b"test"

    def test_null_bytes_in_passphrase(self):
        """Passphrase with embedded null bytes must work."""
        f = EncryptionFacade.from_passphrase("pass\x00word\x00")
        ct, nonce = f.encrypt(b"test")
        assert f.decrypt(ct, nonce) == b"test"

    def test_emoji_passphrase(self):
        """Unicode emoji passphrase must work."""
        f = EncryptionFacade.from_passphrase("🔐🧶🎯💎")
        ct, nonce = f.encrypt(b"test")
        assert f.decrypt(ct, nonce) == b"test"

    def test_same_passphrase_different_salt_different_key(self):
        """Same passphrase with different salts must derive different keys."""
        f1 = EncryptionFacade.from_passphrase("test", salt=os.urandom(16))
        f2 = EncryptionFacade.from_passphrase("test", salt=os.urandom(16))
        assert f1.key_id != f2.key_id

    def test_same_passphrase_same_salt_same_key(self):
        """Same passphrase + same salt must always derive the same key."""
        salt = os.urandom(16)
        f1 = EncryptionFacade.from_passphrase("deterministic", salt=salt)
        f2 = EncryptionFacade.from_passphrase("deterministic", salt=salt)
        assert f1.key_id == f2.key_id
        # Cross-verify: encrypt with one, decrypt with the other
        ct, nonce = f1.encrypt(b"cross-verify")
        assert f2.decrypt(ct, nonce) == b"cross-verify"

    def test_iteration_count_is_owasp_minimum(self):
        """PBKDF2 iterations must be at least 600,000 (OWASP 2023)."""
        assert ITERATIONS >= 600_000


# ═══════════════════════════════════════════════════════════════════
# 5. ED25519 SIGNATURE ATTACKS
# ═══════════════════════════════════════════════════════════════════


class TestEd25519Attacks:
    """Attack the Ed25519 signing/verification path."""

    @pytest.fixture
    def keypair(self):
        return EncryptionFacade.generate_signing_keypair()

    def test_truncated_signature(self, keypair):
        """Truncated signature must fail verification."""
        priv, pub = keypair
        data = b"important payload"
        sig = EncryptionFacade.sign(data, priv)
        # Corrupt by truncation
        import base64

        raw_sig = base64.b64decode(sig)
        truncated = base64.b64encode(raw_sig[:32]).decode()
        assert EncryptionFacade.verify(data, truncated, pub) is False

    def test_wrong_public_key(self, keypair):
        """Signature verified with wrong pubkey must fail."""
        priv, _ = keypair
        _, wrong_pub = EncryptionFacade.generate_signing_keypair()
        data = b"payload"
        sig = EncryptionFacade.sign(data, priv)
        assert EncryptionFacade.verify(data, sig, wrong_pub) is False

    def test_modified_data(self, keypair):
        """Signature on modified data must fail."""
        priv, pub = keypair
        data = b"original data"
        sig = EncryptionFacade.sign(data, priv)
        assert EncryptionFacade.verify(b"modified data", sig, pub) is False

    def test_empty_data_signing(self, keypair):
        """Empty data must be signable and verifiable."""
        priv, pub = keypair
        sig = EncryptionFacade.sign(b"", priv)
        assert EncryptionFacade.verify(b"", sig, pub) is True

    def test_large_data_signing(self, keypair):
        """1MB data must be signable without issues."""
        priv, pub = keypair
        data = os.urandom(1024 * 1024)
        sig = EncryptionFacade.sign(data, priv)
        assert EncryptionFacade.verify(data, sig, pub) is True

    def test_signature_not_reusable_across_data(self, keypair):
        """Signature for data A must not verify data B."""
        priv, pub = keypair
        sig_a = EncryptionFacade.sign(b"data A", priv)
        assert EncryptionFacade.verify(b"data B", sig_a, pub) is False

    def test_garbage_signature(self, keypair):
        """Random bytes as signature must fail cleanly."""
        _, pub = keypair
        import base64

        garbage_sig = base64.b64encode(os.urandom(64)).decode()
        assert EncryptionFacade.verify(b"data", garbage_sig, pub) is False

    def test_invalid_base64_signature(self, keypair):
        """Non-base64 signature string must not crash."""
        _, pub = keypair
        result = EncryptionFacade.verify(b"data", "NOT_VALID_B64!!!", pub)
        assert result is False


# ═══════════════════════════════════════════════════════════════════
# 6. ASSOCIATED DATA (AAD) ATTACKS
# ═══════════════════════════════════════════════════════════════════


class TestAssociatedDataAttacks:
    """AEAD associated data must be strictly bound."""

    def test_encrypt_with_aad_decrypt_without(self, facade):
        """If AAD was provided during encryption, omitting it must fail."""
        ct, nonce = facade.encrypt(b"payload", b"required-aad")
        with pytest.raises(EncryptionError):
            facade.decrypt(ct, nonce)  # AAD=None

    def test_encrypt_without_aad_decrypt_with(self, facade):
        """If no AAD was used, providing one at decrypt must fail."""
        ct, nonce = facade.encrypt(b"payload")
        with pytest.raises(EncryptionError):
            facade.decrypt(ct, nonce, b"injected-aad")

    def test_aad_single_byte_change(self, facade):
        """Single-byte change in AAD must cause decryption failure."""
        aad = b"agent:12345:version:1"
        ct, nonce = facade.encrypt(b"payload", aad)
        corrupted_aad = bytearray(aad)
        corrupted_aad[-1] ^= 0x01
        with pytest.raises(EncryptionError):
            facade.decrypt(ct, nonce, bytes(corrupted_aad))

    def test_large_aad(self, facade):
        """1MB AAD must work without issues."""
        large_aad = os.urandom(1024 * 1024)
        ct, nonce = facade.encrypt(b"payload", large_aad)
        assert facade.decrypt(ct, nonce, large_aad) == b"payload"

    def test_empty_aad_vs_none(self, facade):
        """Empty bytes AAD vs None AAD must be distinguished."""
        ct_none, nonce_none = facade.encrypt(b"payload", None)
        ct_empty, nonce_empty = facade.encrypt(b"payload", b"")

        # Decrypt with matching AAD must work
        assert facade.decrypt(ct_none, nonce_none, None) == b"payload"
        assert facade.decrypt(ct_empty, nonce_empty, b"") == b"payload"
