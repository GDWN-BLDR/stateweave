# Merge Engine

Merge state from parallel agents with configurable conflict resolution.

## Usage

```python
from stateweave.core.merge import merge_payloads, ConflictResolutionPolicy

result = merge_payloads(
    agent_a_state,
    agent_b_state,
    policy=ConflictResolutionPolicy.LAST_WRITER_WINS,
)

merged = result.payload
print(f"Resolved {result.conflicts_resolved} conflicts")
```

## Conflict Resolution Policies

| Policy | Behavior |
|--------|----------|
| `LAST_WRITER_WINS` | Newer `exported_at` timestamp wins for conflicting fields |
| `UNION` | Keep all unique entries; recursively merge dicts and lists |
| `MANUAL` | Raise `MergeConflictError` for human resolution |

## Merge Strategies by Field

| Field | Strategy |
|-------|----------|
| `conversation_history` | Union (deduplicate by role + content) |
| `working_memory` | Dict merge with selected policy |
| `goal_tree` | Union of goal nodes (prefer completed over pending) |
| `tool_results_cache` | Dict merge with selected policy |
| `trust_parameters` | Dict merge with selected policy |
| `long_term_memory` | Dict merge with selected policy |
| `episodic_memory` | Union (append-only) |
| `audit_trail` | Always union (sorted by timestamp) |
| `non_portable_warnings` | Union (deduplicate by field) |

## MergeResult

| Field | Type | Description |
|-------|------|-------------|
| `payload` | `StateWeavePayload` | The merged result |
| `conflicts_resolved` | `int` | Number of conflicts that were auto-resolved |
| `policy_used` | `ConflictResolutionPolicy` | Policy applied |
