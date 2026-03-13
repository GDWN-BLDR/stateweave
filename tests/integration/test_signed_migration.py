"""
Integration Tests: Signed + Encrypted Migration
==================================================
Full end-to-end signed and encrypted migration pipeline:
export → sign → encrypt → decrypt → verify → import.
"""

import pytest

from stateweave.adapters.langgraph_adapter import LangGraphAdapter
from stateweave.adapters.mcp_adapter import MCPAdapter
from stateweave.core.encryption import EncryptionFacade
from stateweave.core.serializer import StateWeaveSerializer
from stateweave.schema.v1 import PayloadSignature


class TestSignedMigration:
    @pytest.fixture
    def langgraph_adapter(self):
        adapter = LangGraphAdapter()
        adapter._agents["signed-thread"] = {
            "messages": [
                {"type": "human", "content": "Top secret research query"},
                {"type": "ai", "content": "Here are the classified results."},
            ],
            "clearance_level": "top_secret",
            "session_id": "ts-001",
        }
        return adapter

    @pytest.fixture
    def mcp_adapter(self):
        return MCPAdapter()

    @pytest.fixture
    def serializer(self):
        return StateWeaveSerializer()

    @pytest.fixture
    def encryption(self):
        return EncryptionFacade(EncryptionFacade.generate_key())

    @pytest.fixture
    def signing_keys(self):
        return EncryptionFacade.generate_signing_keypair()

    def test_sign_and_verify_roundtrip(self, langgraph_adapter, serializer, signing_keys):
        private_key, public_key = signing_keys

        # Export
        payload = langgraph_adapter.export_state("signed-thread")

        # Serialize
        raw_bytes = serializer.dumps(payload)

        # Sign
        signature_b64 = EncryptionFacade.sign(raw_bytes, private_key)

        # Attach signature to payload
        payload.signature = PayloadSignature(
            algorithm="Ed25519",
            public_key_id="test-key-001",
            signature_b64=signature_b64,
        )

        # Verify
        assert EncryptionFacade.verify(raw_bytes, signature_b64, public_key) is True

    def test_signed_encrypted_full_pipeline(
        self, langgraph_adapter, mcp_adapter, serializer, encryption, signing_keys
    ):
        private_key, public_key = signing_keys

        # Export
        payload = langgraph_adapter.export_state("signed-thread")

        # Serialize
        raw_bytes = serializer.dumps(payload)

        # Sign
        signature_b64 = EncryptionFacade.sign(raw_bytes, private_key)

        # Encrypt
        ciphertext, nonce = encryption.encrypt(raw_bytes)

        # --- TRANSPORT ---

        # Decrypt
        decrypted = encryption.decrypt(ciphertext, nonce)

        # Verify signature
        assert EncryptionFacade.verify(decrypted, signature_b64, public_key) is True

        # Deserialize
        restored = serializer.loads(decrypted)

        # Import
        mcp_adapter.import_state(restored)

        # Verify import
        agents = mcp_adapter.list_agents()
        assert any(a.agent_id == "signed-thread" for a in agents)

    def test_tampered_payload_fails_verification(
        self, langgraph_adapter, serializer, encryption, signing_keys
    ):
        private_key, public_key = signing_keys

        # Export and serialize
        payload = langgraph_adapter.export_state("signed-thread")
        raw_bytes = serializer.dumps(payload)

        # Sign
        signature_b64 = EncryptionFacade.sign(raw_bytes, private_key)

        # Encrypt
        ciphertext, nonce = encryption.encrypt(raw_bytes)

        # Decrypt
        decrypted = encryption.decrypt(ciphertext, nonce)

        # Tamper with the decrypted data
        tampered = decrypted + b"TAMPERED"

        # Verify should fail
        assert EncryptionFacade.verify(tampered, signature_b64, public_key) is False

    def test_wrong_key_fails_verification(self, langgraph_adapter, serializer, signing_keys):
        private_key, _ = signing_keys
        _, other_public = EncryptionFacade.generate_signing_keypair()

        payload = langgraph_adapter.export_state("signed-thread")
        raw_bytes = serializer.dumps(payload)
        signature_b64 = EncryptionFacade.sign(raw_bytes, private_key)

        # Verify with wrong public key should fail
        assert EncryptionFacade.verify(raw_bytes, signature_b64, other_public) is False
