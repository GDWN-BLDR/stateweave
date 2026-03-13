"""
StateWeave Observability — OpenTelemetry hooks for monitoring.

Provides structured logging, metrics, and tracing for StateWeave operations.
Works with any OpenTelemetry-compatible backend (Datadog, Grafana, Jaeger, etc).

Usage:
    from stateweave.core.observability import instrument, get_metrics

    # Enable instrumentation (call once at startup)
    instrument(service_name="my-app")

    # All StateWeave operations are now traced and metered
"""

import json
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field

logger = logging.getLogger("stateweave.observability")

# ── Metrics store (in-memory, exportable) ──


@dataclass
class MetricsStore:
    """In-memory metrics store for StateWeave operations."""

    exports: int = 0
    imports: int = 0
    diffs: int = 0
    encryptions: int = 0
    decryptions: int = 0
    migrations: int = 0
    signing_operations: int = 0
    delta_creates: int = 0
    delta_applies: int = 0
    merges: int = 0
    errors: int = 0
    total_bytes_serialized: int = 0
    total_bytes_encrypted: int = 0
    operation_durations_ms: list = field(default_factory=list)
    framework_usage: dict = field(default_factory=dict)

    def record_operation(
        self, operation: str, framework: str = "", duration_ms: float = 0, bytes_count: int = 0
    ):
        """Record a StateWeave operation."""
        counter_map = {
            "export": "exports",
            "import": "imports",
            "diff": "diffs",
            "encrypt": "encryptions",
            "decrypt": "decryptions",
            "migrate": "migrations",
            "sign": "signing_operations",
            "delta_create": "delta_creates",
            "delta_apply": "delta_applies",
            "merge": "merges",
        }
        attr = counter_map.get(operation)
        if attr:
            setattr(self, attr, getattr(self, attr) + 1)

        if duration_ms > 0:
            self.operation_durations_ms.append(duration_ms)

        if framework:
            self.framework_usage[framework] = self.framework_usage.get(framework, 0) + 1

        if bytes_count > 0:
            if operation in ("export", "import", "diff"):
                self.total_bytes_serialized += bytes_count
            elif operation in ("encrypt", "decrypt"):
                self.total_bytes_encrypted += bytes_count

    def to_dict(self) -> dict:
        """Export metrics as a dictionary."""
        avg_duration = (
            sum(self.operation_durations_ms) / len(self.operation_durations_ms)
            if self.operation_durations_ms
            else 0
        )
        return {
            "exports": self.exports,
            "imports": self.imports,
            "diffs": self.diffs,
            "encryptions": self.encryptions,
            "decryptions": self.decryptions,
            "migrations": self.migrations,
            "signing_operations": self.signing_operations,
            "delta_creates": self.delta_creates,
            "delta_applies": self.delta_applies,
            "merges": self.merges,
            "errors": self.errors,
            "total_bytes_serialized": self.total_bytes_serialized,
            "total_bytes_encrypted": self.total_bytes_encrypted,
            "avg_operation_duration_ms": round(avg_duration, 2),
            "total_operations": len(self.operation_durations_ms),
            "framework_usage": self.framework_usage,
        }

    def to_json(self) -> str:
        """Export metrics as JSON string."""
        return json.dumps(self.to_dict(), indent=2)


# Global metrics store
_metrics = MetricsStore()
_instrumented = False


def get_metrics() -> MetricsStore:
    """Get the global metrics store."""
    return _metrics


def reset_metrics() -> None:
    """Reset all metrics (useful for testing)."""
    global _metrics
    _metrics = MetricsStore()


@contextmanager
def trace_operation(operation: str, framework: str = "", **attributes):
    """
    Context manager that traces a StateWeave operation.

    Records duration, framework usage, and emits structured log events.

    Usage:
        with trace_operation("export", framework="langgraph") as span:
            payload = adapter.export_state(agent_id)
            span["bytes"] = len(serializer.dumps(payload))
    """
    span = {"operation": operation, "framework": framework, **attributes}
    start = time.perf_counter()

    logger.info(
        "stateweave.operation.start",
        extra={"operation": operation, "framework": framework, **attributes},
    )

    try:
        yield span
        duration_ms = (time.perf_counter() - start) * 1000
        span["duration_ms"] = duration_ms
        span["status"] = "ok"

        _metrics.record_operation(
            operation,
            framework=framework,
            duration_ms=duration_ms,
            bytes_count=span.get("bytes", 0),
        )

        logger.info(
            "stateweave.operation.end",
            extra={
                "operation": operation,
                "framework": framework,
                "duration_ms": round(duration_ms, 2),
                "status": "ok",
                **{k: v for k, v in span.items() if k not in ("operation", "framework")},
            },
        )
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        span["duration_ms"] = duration_ms
        span["status"] = "error"
        span["error"] = str(e)
        _metrics.errors += 1

        logger.error(
            "stateweave.operation.error",
            extra={
                "operation": operation,
                "framework": framework,
                "duration_ms": round(duration_ms, 2),
                "error": str(e),
            },
        )
        raise


def instrument(service_name: str = "stateweave", log_format: str = "json") -> None:
    """
    Enable StateWeave observability instrumentation.

    Args:
        service_name: Name for the service in traces/metrics.
        log_format: "json" for structured logging, "text" for human-readable.
    """
    global _instrumented
    if _instrumented:
        return

    if log_format == "json":
        handler = logging.StreamHandler()
        handler.setFormatter(_JsonFormatter(service_name))
        sw_logger = logging.getLogger("stateweave.core")
        sw_logger.addHandler(handler)
        sw_logger.setLevel(logging.INFO)
    else:
        logging.basicConfig(
            level=logging.INFO,
            format=f"%(asctime)s [{service_name}] %(name)s %(levelname)s: %(message)s",
        )

    _instrumented = True
    logger.info(f"StateWeave observability enabled for service={service_name}")


class _JsonFormatter(logging.Formatter):
    """JSON log formatter for structured logging backends."""

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include extra fields from trace_operation
        for key in ("operation", "framework", "duration_ms", "status", "error", "bytes"):
            val = getattr(record, key, None)
            if val is not None:
                log_entry[key] = val
        return json.dumps(log_entry)
