# Zero-Loss Translations

StateWeave preserves **every piece of state** during round-trips — including framework-specific internals that don't map to universal fields.

## How It Works

Every `CognitiveState` has three categories of data:

| Category | Storage | Round-Trip Behavior |
|----------|---------|-------------------|
| **Universal state** | `conversation_history`, `working_memory`, `goal_tree`, etc. | ✅ Fully portable across all frameworks |
| **Framework-specific state** | `framework_specific` dict | ✅ Preserved in same-framework round-trips |
| **Non-portable state** | `non_portable_warnings` | ⚠️ Stripped with explicit warnings |

### The `framework_specific` Field

When an adapter exports state, framework-internal fields that don't map to universal concepts are stored in `cognitive_state.framework_specific`:

```python
# LangGraph export
payload = lg_adapter.export_state("my-thread")

# LangGraph internals (__channel_versions__, checkpoint_id, etc.)
# are preserved here — not silently dropped:
print(payload.cognitive_state.framework_specific)
# {"__channel_versions__": {"messages": 5}, "checkpoint_id": "ckpt-abc"}
```

When importing back into the **same framework**, those fields are restored:

```python
# LangGraph → Universal → LangGraph = zero loss
target = LangGraphAdapter()
target.import_state(payload)
# __channel_versions__ and checkpoint_id are back in native state
```

### Cross-Framework Transfers

When migrating to a **different framework**, `framework_specific` is carried along but only applied if the target adapter recognizes the fields:

```
LangGraph ──export──▶ Universal Schema ──import──▶ CrewAI
                         │
                         ├─ conversation_history  ✅ applied
                         ├─ working_memory        ✅ applied
                         ├─ framework_specific     📦 carried (not applied)
                         └─ non_portable_warnings  ⚠️ reported
```

This means if the state ever comes **back** to LangGraph, the internal fields are still there.

## The Three Layers

```
┌─────────────────────────────────────────────┐
│  Layer 1: Universal State                   │
│  conversation_history, working_memory,      │
│  goal_tree, tool_results, trust_parameters  │
│  ── Always portable, always transferred ──  │
├─────────────────────────────────────────────┤
│  Layer 2: Framework-Specific State          │
│  framework_specific: {...}                  │
│  ── Carried through, restored to same fw ── │
├─────────────────────────────────────────────┤
│  Layer 3: Non-Portable State               │
│  DB cursors, OAuth tokens, thread locks     │
│  ── Stripped, explicit warning emitted ──   │
└─────────────────────────────────────────────┘
```

## Verifying Fidelity

Use `stateweave diff` to verify that a round-trip produced zero changes:

```bash
stateweave export -f langgraph -a my-agent -o before.json
# ... import into another framework and back ...
stateweave export -f langgraph -a my-agent -o after.json
stateweave diff before.json after.json
# ✅ States are identical
```
