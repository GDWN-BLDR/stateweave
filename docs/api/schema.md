# Universal Schema

The `StateWeavePayload` is the canonical representation of all agent cognitive state.

## StateWeavePayload

| Field | Type | Description |
|-------|------|-------------|
| `stateweave_version` | `str` | Schema version (currently `"0.2.0"`) |
| `source_framework` | `str` | Framework that exported this state |
| `source_version` | `str` | Version of the source framework |
| `exported_at` | `datetime` | When the export occurred |
| `cognitive_state` | `CognitiveState` | All agent knowledge |
| `metadata` | `AgentMetadata` | Agent identity and policies |
| `audit_trail` | `list[AuditEntry]` | Full operation history |
| `non_portable_warnings` | `list[NonPortableWarning]` | Explicit data loss docs |
| `signature` | `PayloadSignature` | Optional Ed25519 signature |

## CognitiveState

| Field | Type | Description |
|-------|------|-------------|
| `conversation_history` | `list[Message]` | Complete message thread |
| `working_memory` | `dict` | Current task state, key-value pairs |
| `goal_tree` | `dict[str, GoalNode]` | Active goals and sub-goals |
| `tool_results_cache` | `dict` | Cached tool outputs |
| `trust_parameters` | `dict` | Confidence scores, reliability metrics |
| `long_term_memory` | `dict` | Persistent knowledge |
| `episodic_memory` | `list` | Past experiences |

## Message

| Field | Type | Values |
|-------|------|--------|
| `role` | `MessageRole` | `human`, `ai`, `system`, `tool` |
| `content` | `str` | Message text |
| `metadata` | `dict` | Optional extra data |

## JSON Schema

Export the schema programmatically:

```python
from stateweave import get_schema_json

schema = get_schema_json()
# Returns a Python dict of the JSON Schema
```

Or via CLI:

```bash
stateweave schema -o schema.json
```

## Validation

```python
from stateweave import validate_payload

is_valid, errors = validate_payload(payload_dict)
```

Or via CLI:

```bash
stateweave validate state.json
```
