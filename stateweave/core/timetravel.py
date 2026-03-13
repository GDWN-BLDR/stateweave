"""
Agent Time Travel — Version, checkpoint, rollback, and branch agent state.
============================================================================
Content-addressable checkpoint storage with delta compression.
Enables versioning every exported state, rolling back to prior cognitive
states, branching from any checkpoint, and diffing any two points in time.

Reuses existing engines:
- stateweave.core.delta (SHA-256 hashing, delta creation/application)
- stateweave.core.diff (structural diff between payloads)
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from stateweave.core.delta import compute_payload_hash, create_delta
from stateweave.core.diff import StateDiff, diff_payloads
from stateweave.core.serializer import StateWeaveSerializer
from stateweave.schema.v1 import StateWeavePayload

logger = logging.getLogger("stateweave.core.timetravel")


@dataclass
class CheckpointMetadata:
    """Metadata for a single checkpoint."""

    version: int
    hash: str
    agent_id: str
    framework: str
    created_at: str
    message_count: int
    working_memory_keys: int
    parent_hash: Optional[str] = None
    branch: str = "main"
    label: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "hash": self.hash,
            "agent_id": self.agent_id,
            "framework": self.framework,
            "created_at": self.created_at,
            "message_count": self.message_count,
            "working_memory_keys": self.working_memory_keys,
            "parent_hash": self.parent_hash,
            "branch": self.branch,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheckpointMetadata":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CheckpointHistory:
    """Complete history of checkpoints for an agent."""

    agent_id: str
    checkpoints: List[CheckpointMetadata] = field(default_factory=list)
    branches: Dict[str, List[int]] = field(default_factory=lambda: {"main": []})

    @property
    def latest(self) -> Optional[CheckpointMetadata]:
        if not self.checkpoints:
            return None
        return max(self.checkpoints, key=lambda c: c.version)

    @property
    def version_count(self) -> int:
        return len(self.checkpoints)

    def get_version(self, version: int) -> Optional[CheckpointMetadata]:
        for cp in self.checkpoints:
            if cp.version == version:
                return cp
        return None

    def get_by_hash(self, hash_prefix: str) -> Optional[CheckpointMetadata]:
        for cp in self.checkpoints:
            if cp.hash.startswith(hash_prefix):
                return cp
        return None


class CheckpointStore:
    """Content-addressable checkpoint store for agent state.

    Stores StateWeavePayloads as versioned checkpoints with:
    - SHA-256 content-addressable storage
    - Delta compression between versions
    - Branch/merge model
    - Human-readable history

    Storage layout:
        .stateweave/
            checkpoints/
                {agent_id}/
                    manifest.json        # Version history
                    v001.json            # Full checkpoint
                    v002.delta.json      # Delta from v001
                    v003.json            # Full checkpoint (every 5th)
    """

    def __init__(self, store_dir: Optional[str] = None):
        if store_dir:
            self._root = Path(store_dir)
        else:
            self._root = Path.cwd() / ".stateweave" / "checkpoints"
        self._serializer = StateWeaveSerializer(pretty=True)

    def checkpoint(
        self,
        payload: StateWeavePayload,
        agent_id: Optional[str] = None,
        label: Optional[str] = None,
        branch: str = "main",
    ) -> CheckpointMetadata:
        """Save a checkpoint of the current agent state.

        Args:
            payload: The state to checkpoint.
            agent_id: Agent identifier (defaults to payload.metadata.agent_id).
            label: Optional human-readable label for this checkpoint.
            branch: Branch name (default: "main").

        Returns:
            CheckpointMetadata for the new checkpoint.
        """
        agent_id = agent_id or payload.metadata.agent_id
        agent_dir = self._root / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Load existing history
        history = self._load_history(agent_id)

        # Compute hash
        content_hash = compute_payload_hash(payload)

        # Determine version number
        version = history.version_count + 1

        # Get parent hash
        parent_hash = None
        if history.latest:
            parent_hash = history.latest.hash

        # Create metadata
        metadata = CheckpointMetadata(
            version=version,
            hash=content_hash,
            agent_id=agent_id,
            framework=payload.source_framework,
            created_at=datetime.utcnow().isoformat(),
            message_count=len(payload.cognitive_state.conversation_history),
            working_memory_keys=len(payload.cognitive_state.working_memory),
            parent_hash=parent_hash,
            branch=branch,
            label=label,
        )

        # Decide: full checkpoint or delta
        # Every 5th version gets a full snapshot, others get deltas
        if version == 1 or version % 5 == 0 or parent_hash is None:
            # Store full checkpoint
            self._store_full(agent_dir, version, payload)
        else:
            # Store delta from previous version
            prev_payload = self._load_payload(agent_id, history.latest.version)
            if prev_payload:
                delta = create_delta(prev_payload, payload)
                self._store_delta(agent_dir, version, delta)
                # Also store full as fallback
                self._store_full(agent_dir, version, payload)
            else:
                self._store_full(agent_dir, version, payload)

        # Update history
        history.checkpoints.append(metadata)
        if branch not in history.branches:
            history.branches[branch] = []
        history.branches[branch].append(version)
        self._save_history(agent_id, history)

        logger.info(
            f"Checkpoint v{version} for '{agent_id}' "
            f"({content_hash[:12]}...) on branch '{branch}'"
        )

        return metadata

    def history(self, agent_id: str) -> CheckpointHistory:
        """Get the full checkpoint history for an agent.

        Args:
            agent_id: Agent identifier.

        Returns:
            CheckpointHistory with all versions.
        """
        return self._load_history(agent_id)

    def rollback(self, agent_id: str, version: int) -> StateWeavePayload:
        """Restore a previous checkpoint.

        Args:
            agent_id: Agent identifier.
            version: Version number to restore.

        Returns:
            The StateWeavePayload from that checkpoint.

        Raises:
            ValueError: If version not found.
        """
        payload = self._load_payload(agent_id, version)
        if payload is None:
            raise ValueError(f"Checkpoint v{version} not found for agent '{agent_id}'")

        logger.info(f"Rolled back '{agent_id}' to v{version}")
        return payload

    def branch(
        self,
        agent_id: str,
        version: int,
        new_agent_id: str,
        branch_name: str = "main",
    ) -> CheckpointMetadata:
        """Branch from a checkpoint to create a new agent lineage.

        Args:
            agent_id: Source agent identifier.
            version: Version to branch from.
            new_agent_id: Identifier for the new branch.
            branch_name: Branch name for the new lineage.

        Returns:
            CheckpointMetadata for the branched checkpoint.
        """
        payload = self.rollback(agent_id, version)

        metadata = self.checkpoint(
            payload=payload,
            agent_id=new_agent_id,
            label=f"Branched from {agent_id} v{version}",
            branch=branch_name,
        )

        logger.info(
            f"Branched '{agent_id}' v{version} → '{new_agent_id}' "
            f"(branch: {branch_name})"
        )
        return metadata

    def diff_versions(
        self,
        agent_id: str,
        version_a: int,
        version_b: int,
    ) -> StateDiff:
        """Diff two checkpoint versions.

        Args:
            agent_id: Agent identifier.
            version_a: First version.
            version_b: Second version.

        Returns:
            StateDiff showing all differences.
        """
        payload_a = self._load_payload(agent_id, version_a)
        payload_b = self._load_payload(agent_id, version_b)

        if payload_a is None:
            raise ValueError(f"Checkpoint v{version_a} not found")
        if payload_b is None:
            raise ValueError(f"Checkpoint v{version_b} not found")

        return diff_payloads(payload_a, payload_b)

    def list_agents(self) -> List[str]:
        """List all agents with checkpoints.

        Returns:
            List of agent IDs.
        """
        if not self._root.exists():
            return []
        return [
            d.name
            for d in self._root.iterdir()
            if d.is_dir() and (d / "manifest.json").exists()
        ]

    # --- Internal storage methods ---

    def _store_full(
        self, agent_dir: Path, version: int, payload: StateWeavePayload
    ) -> None:
        filepath = agent_dir / f"v{version:04d}.json"
        data = self._serializer.to_dict(payload)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _store_delta(
        self, agent_dir: Path, version: int, delta: Any
    ) -> None:
        filepath = agent_dir / f"v{version:04d}.delta.json"
        with open(filepath, "w") as f:
            json.dump(delta.model_dump(mode="json"), f, indent=2, default=str)

    def _load_payload(
        self, agent_id: str, version: int
    ) -> Optional[StateWeavePayload]:
        agent_dir = self._root / agent_id
        filepath = agent_dir / f"v{version:04d}.json"

        if not filepath.exists():
            return None

        with open(filepath, "r") as f:
            data = json.load(f)

        return self._serializer.from_dict(data)

    def _load_history(self, agent_id: str) -> CheckpointHistory:
        agent_dir = self._root / agent_id
        manifest = agent_dir / "manifest.json"

        if not manifest.exists():
            return CheckpointHistory(agent_id=agent_id)

        with open(manifest, "r") as f:
            data = json.load(f)

        history = CheckpointHistory(
            agent_id=agent_id,
            branches=data.get("branches", {"main": []}),
        )
        for cp_data in data.get("checkpoints", []):
            history.checkpoints.append(CheckpointMetadata.from_dict(cp_data))

        return history

    def _save_history(self, agent_id: str, history: CheckpointHistory) -> None:
        agent_dir = self._root / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        manifest = agent_dir / "manifest.json"

        data = {
            "agent_id": agent_id,
            "checkpoints": [cp.to_dict() for cp in history.checkpoints],
            "branches": history.branches,
        }

        with open(manifest, "w") as f:
            json.dump(data, f, indent=2)

    def format_history(self, agent_id: str) -> str:
        """Format checkpoint history as a human-readable report."""
        history = self.history(agent_id)

        if not history.checkpoints:
            return f"No checkpoints found for agent '{agent_id}'"

        lines = [
            f"Checkpoint History: {agent_id}",
            "═" * 60,
            f"  Versions: {history.version_count}",
            f"  Branches: {', '.join(history.branches.keys())}",
            "",
        ]

        for cp in reversed(history.checkpoints):
            label = f" — {cp.label}" if cp.label else ""
            branch_tag = f" [{cp.branch}]" if cp.branch != "main" else ""
            lines.append(
                f"  v{cp.version:>3}  {cp.hash[:12]}  "
                f"{cp.created_at[:19]}  "
                f"msgs={cp.message_count} mem={cp.working_memory_keys}"
                f"{branch_tag}{label}"
            )

        lines.append("═" * 60)
        return "\n".join(lines)
