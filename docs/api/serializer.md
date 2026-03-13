# Serializer

`StateWeaveSerializer` is the central serialization chokepoint. All state serialization passes through this module.

## Usage

```python
from stateweave import StateWeaveSerializer

serializer = StateWeaveSerializer(pretty=True)

# Serialize to bytes
raw_bytes = serializer.dumps(payload)

# Deserialize from bytes
restored = serializer.loads(raw_bytes)
```

## Methods

| Method | Description |
|--------|-------------|
| `dumps(payload)` | Serialize `StateWeavePayload` → UTF-8 JSON bytes |
| `loads(data)` | Deserialize bytes → `StateWeavePayload` |
| `dumps_typed(payload)` | LangGraph `SerializerProtocol` compatible (returns type tag + bytes) |
| `loads_typed(data)` | Deserialize from typed tuple |
| `to_dict(payload)` | Convert to plain dict |
| `from_dict(data)` | Create payload from dict |
| `encode_binary(data)` | Encode bytes as base64 for JSON transport |
| `decode_binary(data)` | Decode base64 back to bytes |

## LangGraph Compatibility

The serializer implements LangGraph's `SerializerProtocol` via `dumps_typed` / `loads_typed`.
