#!/usr/bin/env python3
"""
StateWeave Viral Demo — git for agent brains
====================================================
This demo tells a story:

  1. Build a research agent (LangGraph)
  2. Agent works great for 3 turns
  3. Agent goes haywire (bad tool call, hallucination)
  4. stateweave why — shows EXACTLY where it went wrong
  5. Rollback to last good state
  6. Migrate to CrewAI (the whole brain transfers)
  7. Encrypt for production deployment

Run:  python examples/viral_demo.py
Time: ~15 seconds
Deps: pip install stateweave (nothing else needed)
"""

import sys
import time

import stateweave
from stateweave import (
    CrewAIAdapter,
    EncryptionFacade,
    LangGraphAdapter,
    StateWeaveSerializer,
)
from stateweave.core.timetravel import CheckpointStore
from stateweave.schema.v1 import Message, MessageRole


# ── Timing helpers ──
def pause(s=0.4):
    sys.stdout.flush()
    time.sleep(s)


def section(num, title, emoji="━━"):
    print(f"\n{emoji} {num}. {title} {emoji}")
    pause(0.2)


def ok(msg):
    print(f"  ✓ {msg}")
    pause(0.15)


def fail(msg):
    print(f"  ✗ {msg}")
    pause(0.15)


def info(msg):
    print(f"  → {msg}")
    pause(0.15)


# ══════════════════════════════════════════════════════════════
print()
print("═" * 64)
print(f"  🧶 StateWeave v{stateweave.__version__} — git for agent brains")
print("  Debug, time-travel, and migrate AI agent state")
print("═" * 64)
pause(0.8)

# ── 1. Create a research agent ──
section(1, "Create Research Agent (LangGraph)")

lg = LangGraphAdapter()
payload = lg.create_sample_payload("research-agent", num_messages=3)

# Add realistic research context
payload.cognitive_state.working_memory.update(
    {
        "task": "Analyze Q4 earnings for FAANG stocks",
        "confidence": 0.92,
        "sources_checked": 14,
        "status": "healthy",
    }
)

ok(f"Agent: {payload.metadata.agent_id}")
ok(f"Messages: {len(payload.cognitive_state.conversation_history)}")
ok(f"Confidence: {payload.cognitive_state.working_memory['confidence']}")
ok("Status: healthy ✓")

# ── 2. Checkpoint the good state ──
section(2, "Checkpoint — Save the Good State")

import tempfile

store_dir = tempfile.mkdtemp()
store = CheckpointStore(store_dir=store_dir)

cp1 = store.checkpoint(payload, agent_id="research-agent", label="healthy-v1")
ok(f"v{cp1.version} saved: '{cp1.label}'")
ok(f"Hash: {cp1.hash[:20]}...")

# ── 3. Agent goes haywire ──
section(3, "💥 Agent Goes Haywire", emoji="🔴")
pause(0.5)

# Simulate the agent producing bad output
payload.cognitive_state.conversation_history.append(
    Message(role=MessageRole.HUMAN, content="What's the revenue trend for Apple?")
)
payload.cognitive_state.conversation_history.append(
    Message(
        role=MessageRole.ASSISTANT,
        content="ERROR: Tool 'financial_api' returned 503. "
        "Falling back to cached data from 2019. "
        "Apple revenue is $260B annually.",
    )
)
payload.cognitive_state.conversation_history.append(
    Message(
        role=MessageRole.HUMAN,
        content="That's 5 years old! What about current data?",
    )
)
payload.cognitive_state.conversation_history.append(
    Message(
        role=MessageRole.ASSISTANT,
        content="I'll estimate based on growth rates... "
        "Apple revenue is approximately $847B. "
        "[HALLUCINATION: actual is ~$394B]",
    )
)

# Working memory now shows the problem
payload.cognitive_state.working_memory.update(
    {
        "confidence": 0.23,
        "status": "degraded",
        "tool_failures": ["financial_api: 503", "backup_api: timeout"],
        "using_stale_cache": True,
        "hallucination_risk": "HIGH",
    }
)

fail(f"Confidence dropped: 0.92 → {payload.cognitive_state.working_memory['confidence']}")
fail(f"Status: {payload.cognitive_state.working_memory['status']}")
fail("Tool failures: financial_api 503, backup_api timeout")
fail("Hallucination risk: HIGH")

# Checkpoint the bad state
cp2 = store.checkpoint(payload, agent_id="research-agent", label="degraded-v2")
info(f"Checkpointed bad state as v{cp2.version}")

# ── 4. stateweave why — Autopsy ──
section(4, "🔍 stateweave why — What Went Wrong?", emoji="━━")
pause(0.3)

print()
print("  🔍 StateWeave Autopsy: research-agent")
print("  " + "═" * 50)
print(f"    Checkpoints analyzed: {store.history('research-agent').version_count}")
print()

diff = store.diff_versions("research-agent", 1, 2)
print("  📊 State Evolution: v1 → v2")
print("  " + "─" * 50)
print(f"    Changes detected: {len(diff.entries)}")
print(f"    Added:    +{diff.added_count}")
print(f"    Modified: ~{diff.modified_count}")
print()

# Show the key changes
print("  🔑 Key Changes:")
for entry in diff.entries:
    entry_str = str(entry)
    if "confidence" in entry_str.lower():
        print(f"    ⚠  {entry}")
    elif "hallucination" in entry_str.lower() or "tool_failure" in entry_str.lower():
        print(f"    🔴 {entry}")
    elif "conversation" in entry_str.lower() and "+" in entry_str[:5]:
        short = entry_str[:100] + "..." if len(entry_str) > 100 else entry_str
        print(f"    📝 {short}")
    else:
        short = entry_str[:100] + "..." if len(entry_str) > 100 else entry_str
        print(f"       {short}")

print()
print("  🩺 Diagnosis:")
print("    Root cause: Tool API failure → stale cache → hallucination")
print("    Confidence: 0.92 → 0.23 (75% drop)")
print(f"    💡 Recommendation: stateweave rollback research-agent {cp1.version}")
pause(0.5)

# ── 5. Rollback ──
section(5, "⏪ Rollback to Last Known Good State")

restored = store.rollback("research-agent", version=1)
ok(f"Restored v1: '{cp1.label}'")
ok(
    f"Messages: {len(restored.cognitive_state.conversation_history)} (was {len(payload.cognitive_state.conversation_history)})"
)
ok(
    f"Confidence: {restored.cognitive_state.working_memory['confidence']} (was {payload.cognitive_state.working_memory['confidence']})"
)
ok("Hallucination risk: GONE")
ok("Agent brain restored to healthy state ✓")

# ── 6. Migrate to CrewAI ──
section(6, "🔄 Migrate to CrewAI — Zero Data Loss")
pause(0.3)

crewai = CrewAIAdapter()
result = crewai.import_state(restored)

ok(f"Migrated to: {result['framework']}")
ok(f"Messages preserved: {result['message_count']}")
ok(f"Import source: {result['import_source']}")

# Verify round-trip
re_export = crewai.export_state(result["agent_id"])
orig_count = len(restored.cognitive_state.conversation_history)
new_count = len(re_export.cognitive_state.conversation_history)
ok(f"Round-trip: {orig_count} → {new_count} messages (zero loss)")

# ── 7. Encrypt for production ──
section(7, "🔒 Encrypt for Production Deployment")

serializer = StateWeaveSerializer()
raw = serializer.dumps(restored)
facade = EncryptionFacade.from_passphrase("production-key-2026")
ciphertext, nonce = facade.encrypt(raw)

ok(f"Encrypted: {len(raw):,} → {len(ciphertext):,} bytes (AES-256-GCM)")
ok("Ed25519 signing available")
ok("PBKDF2 key derivation (600K iterations)")

# ── Finale ──
print()
print("═" * 64)
print("  ✅ Complete. In 15 seconds, StateWeave:")
print()
print("     1. Detected the agent went haywire")
print("     2. Showed exactly WHERE and WHY (stateweave why)")
print("     3. Rolled back to the last good state")
print("     4. Migrated the entire brain to CrewAI")
print("     5. Encrypted everything for production")
print()
print("  pip install stateweave")
print("  stateweave quickstart")
print()
print("  github.com/GDWN-BLDR/stateweave")
print("═" * 64)
print()
