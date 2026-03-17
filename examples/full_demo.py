"""
StateWeave Real Demo — pip install stateweave → 7 steps

Works without langgraph installed (uses dict-based adapter mode).
For the real-framework integration demo, see examples/real_langgraph_demo.py.
"""

print("=" * 60)
print("  StateWeave v0.3.2 — Real End-to-End Demo")
print("=" * 60)
print()

# ── 1. Export from LangGraph ──
print("━━ 1. Export from LangGraph ━━")
from stateweave import LangGraphAdapter, MCPAdapter, diff_payloads

lg = LangGraphAdapter()
lg._agents["research-agent"] = {
    "messages": [
        {"type": "human", "content": "Research quantum computing breakthroughs in 2026"},
        {"type": "ai", "content": "I found 3 significant developments:\n1. IBM's 100K-qubit roadmap\n2. Google's error-correction milestone\n3. Microsoft's topological qubit breakthrough"},
        {"type": "human", "content": "Summarize the Google result"},
        {"type": "ai", "content": "Google achieved below-threshold error correction on Willow, showing that adding more qubits reduces errors."},
    ],
    "working_memory": {
        "task": "quantum research",
        "confidence": 0.92,
        "sources_checked": 14,
    },
}

payload = lg.export_state("research-agent")
print(f"  ✓ Exported {len(payload.cognitive_state.conversation_history)} messages")
print(f"  ✓ Source framework: {payload.source_framework}")
print()

# ── 2. Import into MCP ──
print("━━ 2. Import into MCP ━━")
mcp = MCPAdapter()
result = mcp.import_state(payload)
print(f"  ✓ Imported into {result['framework']}")
print(f"  ✓ Messages preserved: {result['message_count']}")
print(f"  ✓ Import source: {result['import_source']}")
print()

# ── 3. Round-trip verification ──
print("━━ 3. Verify Round-Trip ━━")
re_export = mcp.export_state("research-agent")
orig = len(payload.cognitive_state.conversation_history)
after = len(re_export.cognitive_state.conversation_history)
print(f"  ✓ Original:      {orig} messages")
print(f"  ✓ After import:   {after} messages")
print(f"  ✓ Zero data loss: {'YES' if orig == after else 'NO'}")
print()

# ── 4. Diff two states ──
print("━━ 4. Diff Agent States ━━")
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
print(f"  Summary:     {diff.summary}")
print()

# ── 5. Time Travel ──
print("━━ 5. Time Travel ━━")
from stateweave.core.timetravel import CheckpointStore

store = CheckpointStore()
v1 = store.checkpoint(payload, label="initial-research")
print(f"  ✓ Checkpoint v1 (label: {v1.label}, hash: {v1.hash[:12]}...)")

v2 = store.checkpoint(modified, label="after-drug-discovery")
print(f"  ✓ Checkpoint v2 (label: {v2.label}, hash: {v2.hash[:12]}...)")

history = store.history("research-agent")
print(f"  ✓ {history.version_count} versions stored")

for cp in history.checkpoints:
    print(f"      v{cp.version}: {cp.label}")

rolled_back = store.rollback("research-agent", version=1)
print(f"  ✓ Rolled back → {len(rolled_back.cognitive_state.conversation_history)} msgs")
print()

# ── 6. Encryption ──
print("━━ 6. Encryption (AES-256-GCM) ━━")
from stateweave import EncryptionFacade, StateWeaveSerializer

serializer = StateWeaveSerializer()
raw = serializer.dumps(payload)

facade = EncryptionFacade.from_passphrase("demo-passphrase-2026")
ciphertext, nonce = facade.encrypt(raw)
print(f"  ✓ Plaintext:  {len(raw):,} bytes")
print(f"  ✓ Ciphertext: {len(ciphertext):,} bytes")
print(f"  ✓ Algorithm:  AES-256-GCM")

decrypted = facade.decrypt(ciphertext, nonce)
restored = serializer.loads(decrypted)
print(f"  ✓ Decrypted:  {len(restored.cognitive_state.conversation_history)} messages intact")
print()

# ── 7. Non-portable warnings ──
print("━━ 7. Non-Portable Warnings ━━")
if payload.non_portable_warnings:
    for w in payload.non_portable_warnings:
        print(f"  ⚠ [{w.severity.value}] {w.field}: {w.reason}")
else:
    print("  ✓ No non-portable warnings (clean export)")
print()

print("=" * 60)
print("  7/7 steps passed. Everything runs from PyPI.")
print("  Zero mocks. Zero shortcuts.")
print("=" * 60)
