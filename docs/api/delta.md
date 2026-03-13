# Delta Transport

Send only state differences instead of full payloads for bandwidth-efficient synchronization.

## Usage

```python
from stateweave.core.delta import create_delta, apply_delta

# Create delta (only the changes)
delta = create_delta(old_payload, new_payload)
print(f"Delta has {delta.size} entries (vs full payload)")

# Apply delta on the receiver side
updated = apply_delta(base_payload, delta)
```

## DeltaPayload

| Field | Type | Description |
|-------|------|-------------|
| `stateweave_version` | `str` | Schema version |
| `base_hash` | `str` | SHA-256 hash of the base payload |
| `source_framework` | `str` | Framework of the updated state |
| `created_at` | `datetime` | When the delta was created |
| `entries` | `list[DeltaEntry]` | The state changes |
| `is_empty` | `bool` | Whether no changes exist |
| `size` | `int` | Number of entries |

## DeltaEntry

| Field | Type | Description |
|-------|------|-------------|
| `path` | `str` | Dot-separated path to the changed field |
| `operation` | `str` | `"set"`, `"delete"`, or `"append"` |
| `value` | `Any` | New value (for set/append operations) |

## Hash Verification

The receiver must have the exact base state. If the base has diverged, `apply_delta` raises `DeltaHashMismatchError`:

```python
from stateweave.core.delta import DeltaHashMismatchError

try:
    updated = apply_delta(wrong_base, delta)
except DeltaHashMismatchError:
    # Base state has diverged — request full payload
    pass
```
