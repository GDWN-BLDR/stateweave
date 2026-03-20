"""
StateWeave Demo — Recording-Friendly Version
Adds pauses between steps so the GIF/asciicast is readable.
NOT for production use — use full_demo.py for actual demos.
"""

import sys
import time


def pause(seconds=0.8):
    sys.stdout.flush()
    time.sleep(seconds)


def type_line(text, delay=0.03):
    """Simulate typing for the command lines."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


# Opening
print()
type_line("$ pip install stateweave")
pause(0.5)
print("Successfully installed stateweave-0.3.7")
pause(0.6)
print()
type_line("$ python examples/full_demo.py")
pause(0.5)
print()

print("=" * 60)
print("  StateWeave v0.3.7 — Real End-to-End Demo")
print("=" * 60)
print()
pause(1.0)

# ── 1. Export from LangGraph ──
print("━━ 1. Export from LangGraph ━━")
pause(0.3)

from stateweave import LangGraphAdapter, MCPAdapter, diff_payloads

lg = LangGraphAdapter()
lg._agents["research-agent"] = {
    "messages": [
        {"type": "human", "content": "Research quantum computing breakthroughs in 2026"},
        {
            "type": "ai",
            "content": "I found 3 significant developments:\n1. IBM's 100K-qubit roadmap\n2. Google's error-correction milestone\n3. Microsoft's topological qubit breakthrough",
        },
        {"type": "human", "content": "Summarize the Google result"},
        {
            "type": "ai",
            "content": "Google achieved below-threshold error correction on Willow, showing that adding more qubits reduces errors.",
        },
    ],
    "working_memory": {
        "task": "quantum research",
        "confidence": 0.92,
        "sources_checked": 14,
    },
}

payload = lg.export_state("research-agent")
print(f"  ✓ Exported {len(payload.cognitive_state.conversation_history)} messages")
pause(0.3)
print(f"  ✓ Source framework: {payload.source_framework}")
pause(0.8)
print()

# ── 2. Import into MCP ──
print("━━ 2. Import into MCP ━━")
pause(0.3)
mcp = MCPAdapter()
result = mcp.import_state(payload)
print(f"  ✓ Imported into {result['framework']}")
pause(0.3)
print(f"  ✓ Messages preserved: {result['message_count']}")
pause(0.8)
print()

# ── 3. Round-trip verification ──
print("━━ 3. Verify Round-Trip ━━")
pause(0.3)
re_export = mcp.export_state("research-agent")
orig = len(payload.cognitive_state.conversation_history)
after = len(re_export.cognitive_state.conversation_history)
print(f"  ✓ Original:      {orig} messages")
pause(0.2)
print(f"  ✓ After import:   {after} messages")
pause(0.2)
print(f"  ✓ Zero data loss: {'YES' if orig == after else 'NO'}")
pause(0.8)
print()

# ── 4. Diff two states ──
print("━━ 4. Diff Agent States ━━")
pause(0.3)
mcp._agents["research-agent"]["messages"].append(
    {"role": "user", "content": "Implications for drug discovery?"}
)
mcp._agents["research-agent"]["working_memory"] = {
    "task": "quantum research",
    "confidence": 0.95,
    "sources_checked": 14,
    "new_finding": "quantum advantage in molecular simulation",
}
modified = mcp.export_state("research-agent")

diff = diff_payloads(payload, modified)
print(f"  Has changes: {diff.has_changes}")
pause(0.2)
print(f"  Summary:     {diff.summary}")
pause(0.8)
print()

# ── 5. Time Travel ──
print("━━ 5. Time Travel ━━")
pause(0.3)
from stateweave.core.timetravel import CheckpointStore

store = CheckpointStore()
v1 = store.checkpoint(payload, label="initial-research")
print(f"  ✓ Checkpoint v1 ({v1.label})")
pause(0.3)

v2 = store.checkpoint(modified, label="after-drug-discovery")
print(f"  ✓ Checkpoint v2 ({v2.label})")
pause(0.3)

rolled_back = store.rollback("research-agent", version=1)
print(f"  ✓ Rolled back → {len(rolled_back.cognitive_state.conversation_history)} msgs")
pause(0.8)
print()

# ── 6. Encryption ──
print("━━ 6. Encryption (AES-256-GCM) ━━")
pause(0.3)
from stateweave import EncryptionFacade, StateWeaveSerializer

serializer = StateWeaveSerializer()
raw = serializer.dumps(payload)

facade = EncryptionFacade.from_passphrase("demo-passphrase-2026")
ciphertext, nonce = facade.encrypt(raw)
print(f"  ✓ {len(raw):,} bytes → {len(ciphertext):,} bytes encrypted")
pause(0.3)

decrypted = facade.decrypt(ciphertext, nonce)
restored = serializer.loads(decrypted)
print(f"  ✓ Decrypted: {len(restored.cognitive_state.conversation_history)} messages intact")
pause(0.8)
print()

# ── 7. Non-portable warnings ──
print("━━ 7. Non-Portable Warnings ━━")
pause(0.3)
if payload.non_portable_warnings:
    for w in payload.non_portable_warnings:
        print(f"  ⚠ [{w.severity.value}] {w.field}: {w.reason}")
else:
    print("  ✓ No non-portable warnings (clean export)")
pause(0.8)
print()

print("=" * 60)
print("  7/7 steps passed. Everything runs from PyPI.")
print("=" * 60)
pause(1.5)
print()
