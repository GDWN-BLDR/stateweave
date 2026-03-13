# Observability

StateWeave includes structured logging and in-memory metrics for production monitoring.

## Structured Logging

All modules use Python's `logging` with the `stateweave.*` namespace convention:

```python
import logging
logging.basicConfig(level=logging.INFO)

# All StateWeave logs use the stateweave.* prefix:
# stateweave.core.encryption
# stateweave.core.migration
# stateweave.core.serializer
# stateweave.adapters.langgraph_adapter
```

## JSON Log Format

Set `STATEWEAVE_LOG_FORMAT=json` for structured output compatible with log aggregation tools (ELK, Datadog, etc.).

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STATEWEAVE_LOG_LEVEL` | `INFO` | Python logging level |
| `STATEWEAVE_LOG_FORMAT` | `text` | `json` for structured output |

## UCE Compliance

The `logger_naming` scanner in the Universal Compliance Engine enforces that all loggers follow the `stateweave.*` convention.
