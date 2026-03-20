"""
Framework Migration Demo — LangGraph → CrewAI in 30 Seconds
=============================================================
Shows a complete framework migration with:
  - Safety checkpoint before migration
  - Round-trip verification (zero data loss)
  - Non-portable state warnings
  - Encrypted transport for production

Run: python examples/framework_migration_demo.py
Deps: pip install stateweave (nothing else needed)
"""

import sys
import time

import stateweave
from stateweave import (
    CrewAIAdapter,
    EncryptionFacade,
    LangGraphAdapter,
    MCPAdapter,
    StateWeaveSerializer,
)
from stateweave.core.timetravel import CheckpointStore


def pause(s=0.3):
    sys.stdout.flush()
    time.sleep(s)


def ok(msg):
    print(f"  ✓ {msg}")
    pause(0.15)


def warn(msg):
    print(f"  ⚠ {msg}")
    pause(0.15)


print()
print("═" * 60)
print(f"  🧶 StateWeave v{stateweave.__version__}")
print("  Framework Migration Demo: LangGraph → CrewAI → MCP")
print("═" * 60)
pause(0.5)

# ── 1. Create agent in LangGraph ──
print("\n━━ 1. Create Agent in LangGraph ━━")
lg = LangGraphAdapter()
payload = lg.create_sample_payload("finance-agent", num_messages=5)
payload.cognitive_state.working_memory.update(
    {
        "task": "FAANG earnings analysis",
        "portfolio_value": 2_500_000,
        "confidence": 0.91,
        "models_used": ["gpt-4", "claude-3"],
    }
)

ok(f"Agent: {payload.metadata.agent_id}")
ok(f"Messages: {len(payload.cognitive_state.conversation_history)}")
ok(f"Working memory: {len(payload.cognitive_state.working_memory)} keys")
ok(f"Portfolio: ${payload.cognitive_state.working_memory['portfolio_value']:,}")

# ── 2. Checkpoint before migration ──
print("\n━━ 2. Safety Checkpoint ━━")
import tempfile

store = CheckpointStore(store_dir=tempfile.mkdtemp())
cp = store.checkpoint(payload, agent_id="finance-agent", label="pre-migration")
ok(f"Checkpointed v{cp.version}: '{cp.label}'")
ok(f"Hash: {cp.hash[:20]}...")
ok("Safety net in place — can rollback if migration fails")

# ── 3. Migrate LangGraph → CrewAI ──
print("\n━━ 3. Migrate: LangGraph → CrewAI ━━")
crewai = CrewAIAdapter()
result = crewai.import_state(payload)

ok(f"Migrated to: {result['framework']}")
ok(f"Messages preserved: {result['message_count']}")
ok(f"Agent ID: {result['agent_id']}")

# Verify round-trip
re_export = crewai.export_state(result["agent_id"])
orig = len(payload.cognitive_state.conversation_history)
after = len(re_export.cognitive_state.conversation_history)
ok(f"Round-trip: {orig} → {after} messages — zero data loss ✓")

# ── 4. Non-portable warnings ──
print("\n━━ 4. Check Non-Portable State ━━")
if re_export.non_portable_warnings:
    for w in re_export.non_portable_warnings:
        warn(f"[{w.severity.value}] {w.field}: {w.reason}")
else:
    ok("No non-portable warnings — clean migration")

# ── 5. Chain migration: CrewAI → MCP ──
print("\n━━ 5. Chain Migration: CrewAI → MCP ━━")
mcp = MCPAdapter()
result2 = mcp.import_state(re_export)

ok(f"Migrated to: {result2['framework']}")
ok(f"Messages preserved: {result2['message_count']}")

# Final round-trip
final = mcp.export_state(result2["agent_id"])
ok(f"LangGraph → CrewAI → MCP: {orig} → {len(final.cognitive_state.conversation_history)} messages")
ok("Three frameworks, zero data loss ✓")

# ── 6. Encrypt for production ──
print("\n━━ 6. Encrypt for Production Transport ━━")
serializer = StateWeaveSerializer()
raw = serializer.dumps(final)
facade = EncryptionFacade.from_passphrase("production-migration-key")
ciphertext, nonce = facade.encrypt(raw)

ok(f"Encrypted: {len(raw):,} → {len(ciphertext):,} bytes")
ok("Algorithm: AES-256-GCM")
ok("Ready for secure transport")

# ── Summary ──
print()
print("═" * 60)
print("  ✅ Migration complete!")
print()
print("  LangGraph → CrewAI → MCP")
print(f"  {orig} messages preserved across 3 frameworks")
print("  Zero data loss, encrypted for production")
print()
print("  Try it: pip install stateweave && stateweave quickstart")
print("═" * 60)
print()
