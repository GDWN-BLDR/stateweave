#!/usr/bin/env python3
"""
🧶 StateWeave: Encrypted + Signed Migration
==============================================
Demonstrates the full security pipeline:
  1. Export agent state
  2. Sign it (Ed25519) for sender verification
  3. Encrypt it (AES-256-GCM) for confidentiality
  4. Transport (simulated)
  5. Decrypt
  6. Verify signature (tamper detection)
  7. Import into target framework

Run:
    pip install stateweave
    python examples/encrypted_signed_migration.py
"""

from stateweave import (
    EncryptionFacade,
    LangGraphAdapter,
    MCPAdapter,
    StateWeaveSerializer,
)
from stateweave.schema.v1 import PayloadSignature


def main():
    # ── Setup ──
    serializer = StateWeaveSerializer()

    # Generate encryption key and signing keypair
    encryption_key = EncryptionFacade.generate_key()
    encryptor = EncryptionFacade(encryption_key)
    private_key, public_key = EncryptionFacade.generate_signing_keypair()

    print("🔐 Security Setup:")
    print(f"   Encryption: AES-256-GCM")
    print(f"   Signing: Ed25519")
    print(f"   Key ID: {EncryptionFacade._compute_key_id(encryption_key)}")

    # ── Step 1: Create and export agent state ──
    print("\n📤 Step 1: Exporting agent state from LangGraph...")

    lg = LangGraphAdapter()
    lg._agents["classified-agent"] = {
        "messages": [
            {"type": "human", "content": "Analyze quarterly revenue trends"},
            {"type": "ai", "content": "Revenue increased 23% QoQ driven by enterprise segment..."},
            {"type": "human", "content": "What's the risk assessment?"},
            {"type": "ai", "content": "Key risks: 1) Supply chain concentration 2) FX exposure..."},
        ],
        "analysis_confidence": 0.94,
        "data_sources": ["bloomberg", "sec_filings", "internal_crm"],
        "classification": "confidential",
    }

    payload = lg.export_state("classified-agent")
    print(f"   Messages: {len(payload.cognitive_state.conversation_history)}")
    print(f"   Working memory keys: {len(payload.cognitive_state.working_memory)}")

    # ── Step 2: Serialize ──
    raw_bytes = serializer.dumps(payload)
    print(f"\n📦 Step 2: Serialized → {len(raw_bytes):,} bytes")

    # ── Step 3: Sign ──
    print("\n✍️  Step 3: Signing payload...")
    signature_b64 = EncryptionFacade.sign(raw_bytes, private_key)
    print(f"   Signature: {signature_b64[:40]}...")

    # Attach signature metadata to payload
    payload.signature = PayloadSignature(
        algorithm="Ed25519",
        public_key_id="demo-key-001",
        signature_b64=signature_b64,
    )

    # ── Step 4: Encrypt ──
    print("\n🔒 Step 4: Encrypting...")
    ciphertext, nonce = encryptor.encrypt(raw_bytes)
    print(f"   Ciphertext: {len(ciphertext):,} bytes")
    print(f"   Nonce: {nonce.hex()[:24]}...")

    # ── TRANSPORT (simulated) ──
    print("\n📡 --- TRANSPORT (encrypted bytes travel over network) ---")

    # ── Step 5: Decrypt ──
    print("\n🔓 Step 5: Decrypting...")
    decrypted = encryptor.decrypt(ciphertext, nonce)
    print(f"   Decrypted: {len(decrypted):,} bytes")

    # ── Step 6: Verify signature ──
    print("\n✅ Step 6: Verifying signature...")
    is_authentic = EncryptionFacade.verify(decrypted, signature_b64, public_key)
    print(f"   Authentic: {is_authentic}")

    if not is_authentic:
        print("   ❌ SIGNATURE VERIFICATION FAILED — payload may have been tampered!")
        return

    # ── Step 7: Deserialize and import ──
    print("\n📥 Step 7: Importing into MCP...")
    restored = serializer.loads(decrypted)
    mcp = MCPAdapter()
    mcp.import_state(restored)

    # Verify
    agents = mcp.list_agents()
    assert len(agents) == 1
    assert agents[0].agent_id == "classified-agent"

    re_exported = mcp.export_state("classified-agent")
    original_msgs = len(payload.cognitive_state.conversation_history)
    final_msgs = len(re_exported.cognitive_state.conversation_history)

    print(f"   Agent imported: {agents[0].agent_id}")
    print(f"   Messages preserved: {final_msgs}/{original_msgs}")

    # ── Bonus: Tamper detection demo ──
    print("\n🕵️  Bonus: Tamper detection demo...")
    tampered_bytes = decrypted + b"INJECTED_MALICIOUS_DATA"
    is_tampered = EncryptionFacade.verify(tampered_bytes, signature_b64, public_key)
    print(f"   Tampered payload verification: {is_tampered}")
    print(f"   ✅ Tampering correctly detected!" if not is_tampered else "   ❌ BUG!")

    print("\n🧶 Full pipeline complete: Export → Sign → Encrypt → Decrypt → Verify → Import")


if __name__ == "__main__":
    main()
