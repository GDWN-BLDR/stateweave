"""
Delta State Transport — Send only state differences between payloads.
======================================================================
Instead of transferring full StateWeavePayloads, compute and apply
structural diffs for bandwidth-efficient state synchronization.

Uses the existing diff engine (stateweave.core.diff) as the foundation.
"""

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from stateweave.core.diff import diff_payloads
from stateweave.schema.v1 import SCHEMA_VERSION, StateWeavePayload

logger = logging.getLogger("stateweave.core.delta")


class DeltaEntry(BaseModel):
    """A single state change to apply."""

    path: str
    operation: str  # "set", "delete", "append"
    value: Optional[Any] = None


class DeltaPayload(BaseModel):
    """A differential state update.

    Instead of sending the full StateWeavePayload, a DeltaPayload
    contains only the changes needed to update a known base state.

    The receiver must have the base state (verified by base_hash)
    and applies the delta entries to reconstruct the updated state.
    """

    stateweave_version: str = Field(default=SCHEMA_VERSION)
    base_hash: str = Field(description="SHA-256 hash of the base payload JSON")
    source_framework: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    entries: List[DeltaEntry] = Field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return len(self.entries) == 0

    @property
    def size(self) -> int:
        return len(self.entries)


def compute_payload_hash(payload: StateWeavePayload) -> str:
    """Compute a stable SHA-256 hash of a payload for delta base verification.

    Args:
        payload: The payload to hash.

    Returns:
        Hex-encoded SHA-256 hash string.
    """
    # Use model_dump_json for deterministic JSON output
    payload_json = payload.model_dump_json(exclude={"signature"})
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def create_delta(
    old_payload: StateWeavePayload,
    new_payload: StateWeavePayload,
) -> DeltaPayload:
    """Create a delta between two StateWeavePayloads.

    Args:
        old_payload: The base (previous) state.
        new_payload: The updated state.

    Returns:
        DeltaPayload containing only the changes.
    """
    base_hash = compute_payload_hash(old_payload)

    # Use the existing diff engine to find changes
    state_diff = diff_payloads(old_payload, new_payload)

    entries: List[DeltaEntry] = []
    for diff_entry in state_diff.entries:
        if diff_entry.diff_type == "added":
            entries.append(
                DeltaEntry(
                    path=diff_entry.path,
                    operation="set",
                    value=diff_entry.new_value,
                )
            )
        elif diff_entry.diff_type == "removed":
            entries.append(
                DeltaEntry(
                    path=diff_entry.path,
                    operation="delete",
                )
            )
        elif diff_entry.diff_type == "modified":
            entries.append(
                DeltaEntry(
                    path=diff_entry.path,
                    operation="set",
                    value=diff_entry.new_value,
                )
            )

    logger.info(
        f"Created delta: {len(entries)} entries "
        f"({state_diff.added_count} added, {state_diff.removed_count} removed, "
        f"{state_diff.modified_count} modified)"
    )

    return DeltaPayload(
        base_hash=base_hash,
        source_framework=new_payload.source_framework,
        entries=entries,
    )


class DeltaHashMismatchError(Exception):
    """Raised when the base payload hash doesn't match the delta's expected base."""


def apply_delta(
    base_payload: StateWeavePayload,
    delta: DeltaPayload,
) -> StateWeavePayload:
    """Apply a DeltaPayload to a base StateWeavePayload.

    Args:
        base_payload: The known base state.
        delta: The delta to apply.

    Returns:
        A new StateWeavePayload with the delta applied.

    Raises:
        DeltaHashMismatchError: If the base payload hash doesn't match.
    """
    # Verify the base matches
    actual_hash = compute_payload_hash(base_payload)
    if actual_hash != delta.base_hash:
        raise DeltaHashMismatchError(
            f"Base payload hash mismatch: expected {delta.base_hash[:16]}..., "
            f"got {actual_hash[:16]}... — the base state has diverged"
        )

    # Convert payload to dict for mutation
    data = base_payload.model_dump(mode="json")

    for entry in delta.entries:
        _apply_entry(data, entry)

    # Reconstruct the payload
    result = StateWeavePayload(**data)
    logger.info(f"Applied delta with {delta.size} entries to base payload")
    return result


def _apply_entry(data: Dict[str, Any], entry: DeltaEntry) -> None:
    """Apply a single delta entry to a nested dict."""
    parts = _parse_path(entry.path)

    if entry.operation == "delete":
        _delete_at_path(data, parts)
    elif entry.operation in ("set", "append"):
        _set_at_path(data, parts, entry.value)


def _parse_path(path: str) -> List:
    """Parse dot-separated path with array indices.

    Examples:
        "cognitive_state.working_memory.key" → ["cognitive_state", "working_memory", "key"]
        "audit_trail[0].action" → ["audit_trail", 0, "action"]
    """
    result = []
    for part in path.split("."):
        if "[" in part:
            key, idx = part.split("[", 1)
            if key:
                result.append(key)
            result.append(int(idx.rstrip("]")))
        else:
            result.append(part)
    return result


def _set_at_path(data: Any, parts: List, value: Any) -> None:
    """Set a value at a nested path, creating intermediate dicts as needed."""
    for i, part in enumerate(parts[:-1]):
        if isinstance(part, int):
            while len(data) <= part:
                data.append({})
            data = data[part]
        else:
            if part not in data:
                next_part = parts[i + 1]
                data[part] = [] if isinstance(next_part, int) else {}
            data = data[part]

    last = parts[-1]
    if isinstance(last, int):
        while len(data) <= last:
            data.append(None)
        data[last] = value
    else:
        data[last] = value


def _delete_at_path(data: Any, parts: List) -> None:
    """Delete a value at a nested path."""
    for part in parts[:-1]:
        if isinstance(part, int):
            if part < len(data):
                data = data[part]
            else:
                return
        else:
            if part in data:
                data = data[part]
            else:
                return

    last = parts[-1]
    if isinstance(last, int):
        if last < len(data):
            data.pop(last)
    elif isinstance(data, dict) and last in data:
        del data[last]
