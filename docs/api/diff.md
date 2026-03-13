# Diff Engine

Compare two `StateWeavePayload` instances and get a detailed change report.

## Usage

```python
from stateweave import diff_payloads

diff = diff_payloads(state_before, state_after)

print(diff.to_report())
print(f"Added: {diff.added_count}")
print(f"Removed: {diff.removed_count}")
print(f"Modified: {diff.modified_count}")
print(f"Has changes: {diff.has_changes}")
```

## StateDiff

| Property | Type | Description |
|----------|------|-------------|
| `entries` | `list[DiffEntry]` | All differences found |
| `has_changes` | `bool` | Whether any differences exist |
| `added_count` | `int` | Number of added fields |
| `removed_count` | `int` | Number of removed fields |
| `modified_count` | `int` | Number of modified fields |
| `summary` | `str` | Human-readable summary |
| `to_report()` | `str` | Full formatted report |

## DiffEntry

| Field | Type | Description |
|-------|------|-------------|
| `path` | `str` | Dot-separated path (e.g., `cognitive_state.working_memory.key`) |
| `diff_type` | `str` | `"added"`, `"removed"`, or `"modified"` |
| `old_value` | `Any` | Previous value (for removed/modified) |
| `new_value` | `Any` | New value (for added/modified) |
