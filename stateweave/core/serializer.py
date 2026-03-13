"""
StateWeave Serializer — The central serialization chokepoint.
==============================================================
[LAW 3] All cognitive state serialization MUST transit through this module.
No side-channel serialization via raw json, pickle, or msgpack.
"""

import base64
import json
import logging
from typing import Any, Dict, Tuple

from stateweave.schema.v1 import StateWeavePayload

logger = logging.getLogger("stateweave.core.serializer")


class SerializationError(Exception):
    """Raised when serialization or deserialization fails."""

    pass


class StateWeaveSerializer:
    """The single chokepoint for all state serialization.

    All adapters MUST use this serializer for converting state
    to/from the Universal Schema wire format. This ensures:
    - Consistent encoding across all adapters
    - Single point for encryption integration
    - Audit trail awareness
    - Type-safe round-trip serialization

    Usage:
        serializer = StateWeaveSerializer()
        raw_bytes = serializer.dumps(payload)
        restored = serializer.loads(raw_bytes)

    LangGraph-compatible usage:
        type_str, data = serializer.dumps_typed(payload)
        restored = serializer.loads_typed((type_str, data))
    """

    CONTENT_TYPE = "application/stateweave+json"
    TYPE_PREFIX = "stateweave.v1"

    def __init__(self, pretty: bool = False):
        """Initialize the serializer.

        Args:
            pretty: If True, produce pretty-printed JSON output.
        """
        self._pretty = pretty

    def dumps(self, payload: StateWeavePayload) -> bytes:
        """Serialize a StateWeavePayload to bytes.

        Args:
            payload: The payload to serialize.

        Returns:
            UTF-8 encoded JSON bytes.

        Raises:
            SerializationError: If serialization fails.
        """
        try:
            json_str = payload.model_dump_json(
                indent=2 if self._pretty else None,
            )
            return json_str.encode("utf-8")
        except Exception as e:
            raise SerializationError(f"Failed to serialize payload: {e}") from e

    def loads(self, data: bytes) -> StateWeavePayload:
        """Deserialize bytes to a StateWeavePayload.

        Args:
            data: UTF-8 encoded JSON bytes.

        Returns:
            A validated StateWeavePayload instance.

        Raises:
            SerializationError: If deserialization fails.
        """
        try:
            raw = json.loads(data.decode("utf-8"))
            return StateWeavePayload(**raw)
        except json.JSONDecodeError as e:
            raise SerializationError(f"Invalid JSON: {e}") from e
        except Exception as e:
            raise SerializationError(f"Failed to deserialize payload: {e}") from e

    def dumps_typed(self, payload: StateWeavePayload) -> Tuple[str, bytes]:
        """Serialize with type tag (LangGraph SerializerProtocol compatible).

        Returns:
            Tuple of (type_string, serialized_bytes).
        """
        type_str = f"{self.TYPE_PREFIX}.{payload.source_framework}"
        data = self.dumps(payload)
        return type_str, data

    def loads_typed(self, data: Tuple[str, bytes]) -> StateWeavePayload:
        """Deserialize from typed tuple (LangGraph SerializerProtocol compatible).

        Args:
            data: Tuple of (type_string, serialized_bytes).

        Returns:
            A validated StateWeavePayload instance.
        """
        type_str, raw_bytes = data
        if not type_str.startswith(self.TYPE_PREFIX):
            raise SerializationError(
                f"Unknown type string: {type_str}. Expected prefix: {self.TYPE_PREFIX}"
            )
        return self.loads(raw_bytes)

    def to_dict(self, payload: StateWeavePayload) -> Dict[str, Any]:
        """Convert a payload to a plain dictionary.

        Uses custom serializer for datetime and enum types.
        """
        return json.loads(self.dumps(payload).decode("utf-8"))

    def from_dict(self, data: Dict[str, Any]) -> StateWeavePayload:
        """Create a payload from a plain dictionary."""
        try:
            return StateWeavePayload(**data)
        except Exception as e:
            raise SerializationError(f"Failed to create payload from dict: {e}") from e

    @staticmethod
    def encode_binary(data: bytes) -> str:
        """Encode binary data as base64 string for JSON transport."""
        return base64.b64encode(data).decode("ascii")

    @staticmethod
    def decode_binary(data: str) -> bytes:
        """Decode base64 string back to binary data."""
        return base64.b64decode(data.encode("ascii"))
