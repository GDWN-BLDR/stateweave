"""
StateWeave Schema Registry — Publish and discover state schemas.
=================================================================
Local-first registry that enables developers to publish, discover,
and reuse StateWeave payload schemas and adapter extensions.

Storage: ~/.stateweave/registry/ (local)
Future: registry.stateweave.dev (hosted)

Usage:
    from stateweave.registry import RegistryClient

    client = RegistryClient()
    client.publish("customer-support-agent", payload, tags=["support", "crewai"])
    results = client.search("support")
    schema = client.get("customer-support-agent")
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from stateweave.core.serializer import StateWeaveSerializer
from stateweave.schema.v1 import StateWeavePayload

logger = logging.getLogger("stateweave.registry")

DEFAULT_REGISTRY_DIR = Path.home() / ".stateweave" / "registry"


@dataclass
class RegistryEntry:
    """A published schema in the registry."""

    name: str
    description: str
    framework: str
    version: str
    tags: List[str]
    author: str
    published_at: str
    message_count: int
    memory_keys: int
    schema_hash: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "framework": self.framework,
            "version": self.version,
            "tags": self.tags,
            "author": self.author,
            "published_at": self.published_at,
            "message_count": self.message_count,
            "memory_keys": self.memory_keys,
            "schema_hash": self.schema_hash,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegistryEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class RegistryClient:
    """Local-first schema registry client.

    Stores schemas in a local directory, with optional sync
    to a remote registry in the future.
    """

    def __init__(self, registry_dir: Optional[str] = None):
        self._dir = Path(registry_dir) if registry_dir else DEFAULT_REGISTRY_DIR
        self._index_path = self._dir / "index.json"
        self._schemas_dir = self._dir / "schemas"
        self._serializer = StateWeaveSerializer(pretty=True)

    def publish(
        self,
        name: str,
        payload: StateWeavePayload,
        description: str = "",
        tags: Optional[List[str]] = None,
        author: str = "",
    ) -> RegistryEntry:
        """Publish a schema to the registry.

        Args:
            name: Schema name (kebab-case recommended).
            payload: Example payload defining the schema.
            description: Human-readable description.
            tags: Searchable tags.
            author: Author name.

        Returns:
            RegistryEntry for the published schema.
        """
        self._schemas_dir.mkdir(parents=True, exist_ok=True)

        from stateweave.core.delta import compute_payload_hash
        schema_hash = compute_payload_hash(payload)

        entry = RegistryEntry(
            name=name,
            description=description or f"Schema for {payload.source_framework} agent '{payload.metadata.agent_id}'",
            framework=payload.source_framework,
            version=payload.stateweave_version,
            tags=tags or [],
            author=author,
            published_at=datetime.utcnow().isoformat(),
            message_count=len(payload.cognitive_state.conversation_history),
            memory_keys=len(payload.cognitive_state.working_memory),
            schema_hash=schema_hash,
        )

        # Save the payload
        schema_file = self._schemas_dir / f"{name}.json"
        with open(schema_file, "w") as f:
            json.dump(self._serializer.to_dict(payload), f, indent=2, default=str)

        # Update index
        index = self._load_index()
        index[name] = entry.to_dict()
        self._save_index(index)

        logger.info(f"Published schema '{name}' to registry")
        return entry

    def get(self, name: str) -> Optional[StateWeavePayload]:
        """Get a published schema payload.

        Args:
            name: Schema name.

        Returns:
            StateWeavePayload or None.
        """
        schema_file = self._schemas_dir / f"{name}.json"
        if not schema_file.exists():
            return None

        with open(schema_file) as f:
            data = json.load(f)

        return self._serializer.from_dict(data)

    def get_entry(self, name: str) -> Optional[RegistryEntry]:
        """Get metadata for a published schema.

        Args:
            name: Schema name.

        Returns:
            RegistryEntry or None.
        """
        index = self._load_index()
        data = index.get(name)
        return RegistryEntry.from_dict(data) if data else None

    def search(self, query: str, tags: Optional[List[str]] = None) -> List[RegistryEntry]:
        """Search the registry.

        Args:
            query: Text to search for in names, descriptions, and tags.
            tags: Filter by tags (all must match).

        Returns:
            List of matching entries.
        """
        index = self._load_index()
        results = []

        query_lower = query.lower()

        for name, data in index.items():
            entry = RegistryEntry.from_dict(data)

            # Text match
            text_match = (
                query_lower in entry.name.lower()
                or query_lower in entry.description.lower()
                or any(query_lower in t.lower() for t in entry.tags)
            )

            # Tag filter
            tag_match = True
            if tags:
                tag_match = all(t in entry.tags for t in tags)

            if text_match and tag_match:
                results.append(entry)

        return results

    def list_all(self) -> List[RegistryEntry]:
        """List all schemas in the registry."""
        index = self._load_index()
        return [RegistryEntry.from_dict(data) for data in index.values()]

    def delete(self, name: str) -> bool:
        """Delete a schema from the registry.

        Args:
            name: Schema name.

        Returns:
            True if deleted, False if not found.
        """
        index = self._load_index()
        if name not in index:
            return False

        del index[name]
        self._save_index(index)

        schema_file = self._schemas_dir / f"{name}.json"
        if schema_file.exists():
            schema_file.unlink()

        logger.info(f"Deleted schema '{name}' from registry")
        return True

    def format_listing(self) -> str:
        """Format registry contents as a human-readable report."""
        entries = self.list_all()

        if not entries:
            return "Registry is empty. Publish with: stateweave registry publish <name>"

        lines = [
            "StateWeave Schema Registry",
            "═" * 50,
            f"  {len(entries)} schemas",
            "",
        ]

        for entry in sorted(entries, key=lambda e: e.name):
            tags_str = ", ".join(entry.tags) if entry.tags else ""
            lines.append(
                f"  {entry.name:<30} {entry.framework:<12} "
                f"msgs={entry.message_count} keys={entry.memory_keys}"
            )
            if tags_str:
                lines.append(f"    tags: {tags_str}")

        lines.append("═" * 50)
        return "\n".join(lines)

    # --- Internal ---

    def _load_index(self) -> Dict[str, Any]:
        if not self._index_path.exists():
            return {}
        with open(self._index_path) as f:
            return json.load(f)

    def _save_index(self, index: Dict[str, Any]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with open(self._index_path, "w") as f:
            json.dump(index, f, indent=2)
