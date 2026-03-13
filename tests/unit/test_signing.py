"""
Unit Tests: Payload Signing (Ed25519)
=======================================
Tests for key generation, sign/verify roundtrip, tamper detection,
and wrong-key rejection.
"""

import pytest

from stateweave.core.encryption import EncryptionFacade


class TestSigningKeyGeneration:
    def test_generate_keypair(self):
        private_key, public_key = EncryptionFacade.generate_signing_keypair()
        assert isinstance(private_key, bytes)
        assert isinstance(public_key, bytes)
        assert len(private_key) == 32
        assert len(public_key) == 32

    def test_keypairs_are_unique(self):
        pair1 = EncryptionFacade.generate_signing_keypair()
        pair2 = EncryptionFacade.generate_signing_keypair()
        assert pair1[0] != pair2[0]
        assert pair1[1] != pair2[1]


class TestSignAndVerify:
    @pytest.fixture
    def keypair(self):
        return EncryptionFacade.generate_signing_keypair()

    def test_sign_returns_string(self, keypair):
        private_key, _ = keypair
        signature = EncryptionFacade.sign(b"test data", private_key)
        assert isinstance(signature, str)
        assert len(signature) > 0

    def test_verify_valid_signature(self, keypair):
        private_key, public_key = keypair
        data = b"important payload data"
        signature = EncryptionFacade.sign(data, private_key)
        assert EncryptionFacade.verify(data, signature, public_key) is True

    def test_verify_detects_tampered_data(self, keypair):
        private_key, public_key = keypair
        data = b"original data"
        signature = EncryptionFacade.sign(data, private_key)
        # Tamper with data
        tampered = b"tampered data"
        assert EncryptionFacade.verify(tampered, signature, public_key) is False

    def test_verify_rejects_wrong_key(self, keypair):
        private_key, _ = keypair
        _, other_public = EncryptionFacade.generate_signing_keypair()
        data = b"test data"
        signature = EncryptionFacade.sign(data, private_key)
        assert EncryptionFacade.verify(data, signature, other_public) is False

    def test_sign_empty_data(self, keypair):
        private_key, public_key = keypair
        data = b""
        signature = EncryptionFacade.sign(data, private_key)
        assert EncryptionFacade.verify(data, signature, public_key) is True

    def test_sign_large_data(self, keypair):
        private_key, public_key = keypair
        data = b"x" * 1_000_000  # 1MB
        signature = EncryptionFacade.sign(data, private_key)
        assert EncryptionFacade.verify(data, signature, public_key) is True

    def test_different_data_different_signatures(self, keypair):
        private_key, _ = keypair
        sig1 = EncryptionFacade.sign(b"data1", private_key)
        sig2 = EncryptionFacade.sign(b"data2", private_key)
        assert sig1 != sig2

    def test_same_data_deterministic_signatures(self, keypair):
        """Ed25519 signatures are deterministic for the same key+data."""
        private_key, _ = keypair
        data = b"deterministic test"
        sig1 = EncryptionFacade.sign(data, private_key)
        sig2 = EncryptionFacade.sign(data, private_key)
        assert sig1 == sig2
