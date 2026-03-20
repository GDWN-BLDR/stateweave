"""
StateWeave Replay — Step-by-step agent state debugger.
=======================================================
Replays an agent's checkpoint history, showing what changed
at each step. Like a debugger for agent cognition.

Usage:
    from stateweave.core.replay import ReplayEngine

    engine = ReplayEngine(store)
    for step in engine.replay("my-agent"):
        print(step.summary)
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from stateweave.core.timetravel import CheckpointStore
from stateweave.schema.v1 import StateWeavePayload

logger = logging.getLogger("stateweave.core.replay")


@dataclass
class ReplayStep:
    """A single step in an agent replay."""

    version: int
    label: Optional[str]
    framework: str
    created_at: str
    message_count: int
    working_memory_keys: int
    confidence: Optional[float] = None

    # Changes from previous step
    messages_added: int = 0
    messages_removed: int = 0
    memory_added: List[str] = field(default_factory=list)
    memory_removed: List[str] = field(default_factory=list)
    memory_changed: Dict[str, tuple] = field(default_factory=dict)  # key: (old, new)
    diff_added: int = 0
    diff_removed: int = 0
    diff_modified: int = 0

    # Alerts
    alerts: List[str] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return (
            self.messages_added != 0
            or self.messages_removed != 0
            or len(self.memory_added) > 0
            or len(self.memory_removed) > 0
            or len(self.memory_changed) > 0
        )

    @property
    def total_changes(self) -> int:
        return self.diff_added + self.diff_removed + self.diff_modified


@dataclass
class ReplayResult:
    """Complete replay of an agent's checkpoint history."""

    agent_id: str
    steps: List[ReplayStep] = field(default_factory=list)
    total_versions: int = 0

    @property
    def confidence_trend(self) -> List[Optional[float]]:
        """Return the confidence values across all steps."""
        return [s.confidence for s in self.steps]

    @property
    def biggest_change_step(self) -> Optional[ReplayStep]:
        """Return the step with the most changes."""
        if not self.steps:
            return None
        return max(self.steps, key=lambda s: s.total_changes)


class ReplayEngine:
    """Replays agent checkpoint history step-by-step.

    Iterates through checkpoints showing changes at each version:
    - Messages added/removed
    - Working memory changes (added, removed, modified keys)
    - Confidence drift
    - Alerts for anomalies (big drops, high change counts)
    """

    def __init__(self, store: CheckpointStore):
        self._store = store

    def replay(
        self,
        agent_id: str,
        from_version: Optional[int] = None,
        to_version: Optional[int] = None,
    ) -> ReplayResult:
        """Replay an agent's history and return structured steps.

        Args:
            agent_id: The agent to replay.
            from_version: Start from this version (default: v1).
            to_version: End at this version (default: latest).

        Returns:
            ReplayResult with all steps.
        """
        history = self._store.history(agent_id)
        if not history.checkpoints:
            return ReplayResult(agent_id=agent_id)

        sorted_cps = sorted(history.checkpoints, key=lambda c: c.version)

        # Apply version range
        if from_version:
            sorted_cps = [c for c in sorted_cps if c.version >= from_version]
        if to_version:
            sorted_cps = [c for c in sorted_cps if c.version <= to_version]

        if not sorted_cps:
            return ReplayResult(agent_id=agent_id)

        result = ReplayResult(
            agent_id=agent_id,
            total_versions=len(sorted_cps),
        )

        prev_payload: Optional[StateWeavePayload] = None

        for cp in sorted_cps:
            try:
                payload = self._store._load_payload(agent_id, cp.version)
            except Exception:
                continue

            if payload is None:
                continue

            step = self._build_step(cp, payload, prev_payload)
            result.steps.append(step)
            prev_payload = payload

        return result

    def _build_step(
        self,
        cp,
        payload: StateWeavePayload,
        prev_payload: Optional[StateWeavePayload],
    ) -> ReplayStep:
        """Build a ReplayStep from a checkpoint and its predecessor."""
        # Extract confidence from working memory
        confidence = None
        wm = payload.cognitive_state.working_memory
        for key in ("confidence", "confidence_score", "agent_confidence"):
            if key in wm:
                try:
                    confidence = float(wm[key])
                except (ValueError, TypeError):
                    pass
                break

        step = ReplayStep(
            version=cp.version,
            label=cp.label,
            framework=cp.framework,
            created_at=cp.created_at,
            message_count=cp.message_count,
            working_memory_keys=cp.working_memory_keys,
            confidence=confidence,
        )

        if prev_payload is None:
            # First step — no diff
            step.messages_added = cp.message_count
            step.memory_added = list(wm.keys())
            step.diff_added = cp.message_count + len(wm)
            return step

        # Compare with previous
        prev_msgs = len(prev_payload.cognitive_state.conversation_history)
        curr_msgs = cp.message_count
        step.messages_added = max(0, curr_msgs - prev_msgs)
        step.messages_removed = max(0, prev_msgs - curr_msgs)

        # Working memory diff
        prev_wm = prev_payload.cognitive_state.working_memory
        curr_wm = payload.cognitive_state.working_memory

        prev_keys = set(prev_wm.keys())
        curr_keys = set(curr_wm.keys())

        step.memory_added = sorted(curr_keys - prev_keys)
        step.memory_removed = sorted(prev_keys - curr_keys)

        for key in prev_keys & curr_keys:
            if prev_wm[key] != curr_wm[key]:
                step.memory_changed[key] = (prev_wm[key], curr_wm[key])

        # Use existing diff engine for counts
        try:
            diff = self._store.diff_versions(cp.agent_id, cp.version - 1, cp.version)
            step.diff_added = diff.added_count
            step.diff_removed = diff.removed_count
            step.diff_modified = diff.modified_count
        except Exception:
            step.diff_added = len(step.memory_added) + step.messages_added
            step.diff_removed = len(step.memory_removed) + step.messages_removed
            step.diff_modified = len(step.memory_changed)

        # Generate alerts
        if prev_payload:
            prev_conf = None
            for key in ("confidence", "confidence_score", "agent_confidence"):
                if key in prev_wm:
                    try:
                        prev_conf = float(prev_wm[key])
                    except (ValueError, TypeError):
                        pass
                    break

            if prev_conf is not None and confidence is not None:
                drop = prev_conf - confidence
                if drop > 0.3:
                    pct = int(drop / prev_conf * 100) if prev_conf > 0 else 0
                    step.alerts.append(
                        f"Confidence dropped {pct}% ({prev_conf:.2f} → {confidence:.2f})"
                    )
                elif drop < -0.3:
                    step.alerts.append(f"Confidence recovered ({prev_conf:.2f} → {confidence:.2f})")

        if step.total_changes > 10:
            step.alerts.append(f"Large state change: {step.total_changes} modifications")

        if "hallucination_risk" in curr_wm or "hallucination" in str(curr_wm).lower():
            step.alerts.append("Hallucination risk detected in working memory")

        return step
