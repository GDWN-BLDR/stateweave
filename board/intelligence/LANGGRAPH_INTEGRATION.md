# LangGraph Integration Map

**Owner:** Engineer / Architect
**Last Updated:** 2026-03-13
**Status:** ✅ FEASIBILITY CONFIRMED

---

## State Internals

### Core State Access
- **`graph.get_state(config)`** → `StateSnapshot` object
- **`SerializerProtocol`** interface: `dumps_typed()` / `loads_typed()` methods
- **Default serializer**: `JsonPlusSerializer` (ormsgpack → JSON fallback)
- **Storage backends**: `InMemorySaver`, `SqliteSaver`, `PostgresSaver`

### StateSnapshot Contents
| Field | Type | Maps To (Universal Schema) |
|-------|------|---------------------------|
| `values` | `dict` | `cognitive_state.working_memory` |
| `next` | `tuple[str]` | `cognitive_state.goal_tree.pending_nodes` |
| `config` | `RunnableConfig` | `metadata.agent_config` |
| `metadata` | `CheckpointMetadata` | `metadata` + `audit_trail` |
| `created_at` | `str` | `exported_at` |
| `parent_config` | `Optional[RunnableConfig]` | `audit_trail[-1]` |

### SerializerProtocol Hook Point
```python
class StateWeaveSerializer:
    """Wraps LangGraph's SerializerProtocol to intercept state I/O."""
    
    def dumps_typed(self, obj: Any) -> tuple[str, bytes]:
        # 1. Call original serializer
        type_str, data = self._inner.dumps_typed(obj)
        # 2. Translate to Universal Schema
        payload = self._translate_to_universal(type_str, data)
        # 3. Return wrapped result
        return ("stateweave.v1", self._encode(payload))
    
    def loads_typed(self, data: tuple[str, bytes]) -> Any:
        type_str, raw = data
        if type_str.startswith("stateweave."):
            # StateWeave payload — translate from Universal Schema
            payload = self._decode(raw)
            return self._translate_from_universal(payload)
        else:
            # Native LangGraph payload — pass through
            return self._inner.loads_typed(data)
```

### Version Stability
- **LangGraph v1.0** (Oct 2025): Stable API, no breaking changes until v2.0
- **2026 roadmap**: "Real-Time Persistence & Memory 2.0" — internal state enhancements, NOT cross-framework portability

---

## Type Mapping: LangGraph → Universal Schema

| LangGraph Type | Universal Schema Field | Translation |
|---------------|----------------------|-------------|
| `HumanMessage` | `conversation_history[].role="human"` | Direct map |
| `AIMessage` | `conversation_history[].role="assistant"` | Direct map |
| `SystemMessage` | `conversation_history[].role="system"` | Direct map |
| `ToolMessage` | `conversation_history[].role="tool"` | Direct map + `tool_results_cache` |
| `dict` (channel values) | `working_memory` | Direct map |
| `datetime` | ISO-8601 string | `isoformat()` |
| `enum` | `str` | `.value` |
| `bytes` | Base64 string | `base64.b64encode()` |
| `set` | `list` | `sorted(list(s))` |
| `Decimal` | `str` | `str(d)` |

### Non-Portable Elements (LangGraph-Specific)
| Element | Reason | Warning Severity |
|---------|--------|-----------------|
| Channel metadata (`__channel_versions__`) | LangGraph internal tracking | WARN |
| Checkpoint ID (`checkpoint_id`) | UUID specific to storage backend | INFO |
| Pending writes (`pending_writes`) | In-progress operations, not settled state | WARN |
| Task ID (`task.id`) | Execution-specific identifier | INFO |
