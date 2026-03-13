"""
State Merge Engine — Conflict resolution for parallel agent handoffs.
======================================================================
When multiple agents modify state concurrently, this module merges their
payloads using configurable conflict resolution strategies.

This is the foundation for CRDT-like behavior in multi-agent swarms.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Set

from stateweave.schema.v1 import (
    AuditAction,
    AuditEntry,
    CognitiveState,
    GoalNode,
    Message,
    StateWeavePayload,
)

logger = logging.getLogger("stateweave.core.merge")


class ConflictResolutionPolicy(str, Enum):
    """Strategy for resolving conflicting state between two payloads.

    LAST_WRITER_WINS: The payload with the later exported_at timestamp
                      takes precedence for conflicting fields.
    UNION: Merge both payloads, keeping all unique entries. For dicts,
           keys from both sides are kept; for lists, items are unioned.
    MANUAL: Raise a MergeConflictError when conflicts are detected,
            requiring explicit human resolution.
    """

    LAST_WRITER_WINS = "last_writer_wins"
    UNION = "union"
    MANUAL = "manual"


class MergeConflictError(Exception):
    """Raised when MANUAL policy detects conflicts that require human resolution."""

    def __init__(self, conflicts: List[Dict[str, Any]]):
        self.conflicts = conflicts
        super().__init__(
            f"Merge conflict: {len(conflicts)} field(s) have divergent values. "
            "Resolve manually or switch to LAST_WRITER_WINS / UNION policy."
        )


class MergeResult:
    """Result of a merge operation."""

    def __init__(
        self,
        payload: StateWeavePayload,
        conflicts_resolved: int = 0,
        policy_used: ConflictResolutionPolicy = ConflictResolutionPolicy.LAST_WRITER_WINS,
    ):
        self.payload = payload
        self.conflicts_resolved = conflicts_resolved
        self.policy_used = policy_used


def merge_payloads(
    payload_a: StateWeavePayload,
    payload_b: StateWeavePayload,
    policy: ConflictResolutionPolicy = ConflictResolutionPolicy.LAST_WRITER_WINS,
) -> MergeResult:
    """Merge two StateWeavePayloads with conflict resolution.

    Args:
        payload_a: First payload (e.g., from Agent A).
        payload_b: Second payload (e.g., from Agent B).
        policy: How to resolve conflicting values.

    Returns:
        MergeResult containing the merged payload and conflict stats.

    Raises:
        MergeConflictError: If policy is MANUAL and conflicts are detected.
    """
    # Determine which payload is "newer" for LWW
    a_is_newer = payload_a.exported_at >= payload_b.exported_at
    newer = payload_a if a_is_newer else payload_b

    conflicts_resolved = 0

    # Merge cognitive state
    merged_cognitive, cs_conflicts = _merge_cognitive_state(
        payload_a.cognitive_state,
        payload_b.cognitive_state,
        policy,
        a_is_newer,
    )
    conflicts_resolved += cs_conflicts

    # If MANUAL and there are conflicts, bail
    if policy == ConflictResolutionPolicy.MANUAL and cs_conflicts > 0:
        # _merge_cognitive_state would have raised already
        pass

    # Merge audit trails (always union — audit logs are append-only)
    merged_audit = _merge_audit_trails(payload_a.audit_trail, payload_b.audit_trail)

    # Merge non-portable warnings (union, deduplicated by field)
    merged_warnings = _merge_warnings(
        payload_a.non_portable_warnings, payload_b.non_portable_warnings
    )

    # Add merge audit entry
    merged_audit.append(
        AuditEntry(
            timestamp=datetime.utcnow(),
            action=AuditAction.EXPORT,  # Using EXPORT as closest match
            framework="stateweave",
            success=True,
            details={
                "operation": "merge",
                "policy": policy.value,
                "source_a": payload_a.source_framework,
                "source_b": payload_b.source_framework,
                "conflicts_resolved": conflicts_resolved,
            },
        )
    )

    # Build merged payload using the newer payload as base for metadata
    merged = StateWeavePayload(
        source_framework=f"{payload_a.source_framework}+{payload_b.source_framework}",
        source_version=newer.source_version,
        exported_at=datetime.utcnow(),
        cognitive_state=merged_cognitive,
        metadata=newer.metadata,
        audit_trail=merged_audit,
        non_portable_warnings=merged_warnings,
    )

    logger.info(
        f"Merged payloads ({payload_a.source_framework} + {payload_b.source_framework}) "
        f"with {policy.value} policy, {conflicts_resolved} conflicts resolved"
    )

    return MergeResult(
        payload=merged,
        conflicts_resolved=conflicts_resolved,
        policy_used=policy,
    )


def _merge_cognitive_state(
    cs_a: CognitiveState,
    cs_b: CognitiveState,
    policy: ConflictResolutionPolicy,
    a_is_newer: bool,
) -> tuple:
    """Merge two CognitiveState instances.

    Returns:
        Tuple of (merged CognitiveState, number of conflicts resolved).
    """
    conflicts = 0

    # 1. Conversation history — union, deduplicated by content+role
    merged_messages = _merge_messages(cs_a.conversation_history, cs_b.conversation_history)

    # 2. Working memory — dict merge with policy
    merged_wm, wm_conflicts = _merge_dicts(
        cs_a.working_memory, cs_b.working_memory, policy, a_is_newer
    )
    conflicts += wm_conflicts

    # 3. Goal tree — union of goal nodes
    merged_goals = _merge_goal_trees(cs_a.goal_tree, cs_b.goal_tree)

    # 4. Tool results cache — LWW (latest takes precedence for same keys)
    merged_tools, tool_conflicts = _merge_dicts(
        cs_a.tool_results_cache, cs_b.tool_results_cache, policy, a_is_newer
    )
    conflicts += tool_conflicts

    # 5. Trust parameters — LWW
    merged_trust, trust_conflicts = _merge_dicts(
        cs_a.trust_parameters, cs_b.trust_parameters, policy, a_is_newer
    )
    conflicts += trust_conflicts

    # 6. Long-term memory — union
    merged_ltm, ltm_conflicts = _merge_dicts(
        cs_a.long_term_memory, cs_b.long_term_memory, policy, a_is_newer
    )
    conflicts += ltm_conflicts

    # 7. Episodic memory — union (append-only)
    merged_episodic = _merge_lists(cs_a.episodic_memory, cs_b.episodic_memory)

    return CognitiveState(
        conversation_history=merged_messages,
        working_memory=merged_wm,
        goal_tree=merged_goals,
        tool_results_cache=merged_tools,
        trust_parameters=merged_trust,
        long_term_memory=merged_ltm,
        episodic_memory=merged_episodic,
    ), conflicts


def _merge_messages(msgs_a: List[Message], msgs_b: List[Message]) -> List[Message]:
    """Merge two message lists, deduplicating by content + role."""
    seen: Set[str] = set()
    merged: List[Message] = []

    for msg in msgs_a + msgs_b:
        key = f"{msg.role.value}:{msg.content}"
        if key not in seen:
            seen.add(key)
            merged.append(msg)

    # Sort by any timestamp metadata if available, otherwise preserve order
    return merged


def _merge_dicts(
    dict_a: Dict[str, Any],
    dict_b: Dict[str, Any],
    policy: ConflictResolutionPolicy,
    a_is_newer: bool,
) -> tuple:
    """Merge two dicts with conflict resolution.

    Returns:
        Tuple of (merged dict, number of conflicts).
    """
    merged = {}
    conflicts = 0
    all_keys = set(dict_a.keys()) | set(dict_b.keys())

    for key in all_keys:
        in_a = key in dict_a
        in_b = key in dict_b

        if in_a and not in_b:
            merged[key] = dict_a[key]
        elif not in_a and in_b:
            merged[key] = dict_b[key]
        elif dict_a[key] == dict_b[key]:
            merged[key] = dict_a[key]
        else:
            # Conflict!
            conflicts += 1
            if policy == ConflictResolutionPolicy.MANUAL:
                raise MergeConflictError(
                    [{"field": key, "value_a": dict_a[key], "value_b": dict_b[key]}]
                )
            elif policy == ConflictResolutionPolicy.LAST_WRITER_WINS:
                merged[key] = dict_a[key] if a_is_newer else dict_b[key]
            elif policy == ConflictResolutionPolicy.UNION:
                # For union: if both are dicts, recursively merge
                if isinstance(dict_a[key], dict) and isinstance(dict_b[key], dict):
                    sub_merged, sub_conflicts = _merge_dicts(
                        dict_a[key], dict_b[key], policy, a_is_newer
                    )
                    merged[key] = sub_merged
                    conflicts += sub_conflicts - 1  # Don't double-count
                elif isinstance(dict_a[key], list) and isinstance(dict_b[key], list):
                    merged[key] = _merge_lists(dict_a[key], dict_b[key])
                else:
                    # Scalar conflict in union mode — use newer
                    merged[key] = dict_a[key] if a_is_newer else dict_b[key]

    return merged, conflicts


def _merge_goal_trees(
    tree_a: Dict[str, GoalNode],
    tree_b: Dict[str, GoalNode],
) -> Dict[str, GoalNode]:
    """Merge goal trees — union of all goals."""
    merged = {}
    for goal_id, goal in tree_a.items():
        merged[goal_id] = goal
    for goal_id, goal in tree_b.items():
        if goal_id not in merged:
            merged[goal_id] = goal
        # If same ID exists: keep the one with more progress
        elif goal.status in ("completed", "in_progress") and merged[goal_id].status == "pending":
            merged[goal_id] = goal
    return merged


def _merge_lists(list_a: List[Any], list_b: List[Any]) -> List[Any]:
    """Merge two lists, deduplicating by repr()."""
    seen: Set[str] = set()
    merged: List[Any] = []
    for item in list_a + list_b:
        key = repr(item)
        if key not in seen:
            seen.add(key)
            merged.append(item)
    return merged


def _merge_audit_trails(
    trail_a: List[AuditEntry],
    trail_b: List[AuditEntry],
) -> List[AuditEntry]:
    """Merge audit trails — union all entries, sorted by timestamp."""
    all_entries = trail_a + trail_b
    # Deduplicate by timestamp + action
    seen: Set[str] = set()
    unique: List[AuditEntry] = []
    for entry in all_entries:
        key = f"{entry.timestamp.isoformat()}:{entry.action.value}:{entry.framework}"
        if key not in seen:
            seen.add(key)
            unique.append(entry)
    return sorted(unique, key=lambda e: e.timestamp)


def _merge_warnings(warnings_a, warnings_b):
    """Merge non-portable warnings — union deduplicated by field."""
    seen: Set[str] = set()
    merged = []
    for w in warnings_a + warnings_b:
        if w.field not in seen:
            seen.add(w.field)
            merged.append(w)
    return merged
