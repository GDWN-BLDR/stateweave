"""
Schema Versions — Version registry and migration utilities.
=============================================================
Manages schema version evolution. Versions are immutable;
new versions are additive via migration functions.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from stateweave.schema.v1 import SCHEMA_VERSION

logger = logging.getLogger("stateweave.schema.versions")

# Version registry: version_string -> module_path
VERSION_REGISTRY: Dict[str, str] = {
    "0.1.0": "stateweave.schema.v1",
    "0.2.0": "stateweave.schema.v1",
}

# Migration functions: (from_version, to_version) -> migration_fn
MIGRATIONS: Dict[tuple, Callable] = {}

CURRENT_VERSION = SCHEMA_VERSION


def get_supported_versions() -> List[str]:
    """Get list of all supported schema versions."""
    return sorted(VERSION_REGISTRY.keys())


def is_version_supported(version: str) -> bool:
    """Check if a specific version is supported."""
    return version in VERSION_REGISTRY


def get_current_version() -> str:
    """Get the current (latest) schema version."""
    return CURRENT_VERSION


def register_migration(
    from_version: str,
    to_version: str,
    migration_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
) -> None:
    """Register a migration function between two versions.

    Args:
        from_version: Source schema version.
        to_version: Target schema version.
        migration_fn: Function that transforms a payload dict from
                      source version to target version.
    """
    key = (from_version, to_version)
    if key in MIGRATIONS:
        logger.warning(f"Overwriting existing migration: {from_version} -> {to_version}")
    MIGRATIONS[key] = migration_fn
    logger.info(f"Registered migration: {from_version} -> {to_version}")


def migrate_payload(
    payload: Dict[str, Any],
    target_version: Optional[str] = None,
) -> Dict[str, Any]:
    """Migrate a payload to a target version.

    Applies sequential migrations from the payload's current version
    to the target version. If no target is specified, migrates to
    the current (latest) version.

    Args:
        payload: The raw payload dictionary.
        target_version: Target schema version. Defaults to CURRENT_VERSION.

    Returns:
        Migrated payload dictionary.

    Raises:
        ValueError: If no migration path exists.
    """
    if target_version is None:
        target_version = CURRENT_VERSION

    current = payload.get("stateweave_version", "0.1.0")

    if current == target_version:
        return payload

    # Find migration path (for now, direct migrations only)
    key = (current, target_version)
    if key not in MIGRATIONS:
        # Try chain migration via known versions
        path = _find_migration_path(current, target_version)
        if not path:
            raise ValueError(
                f"No migration path from {current} to {target_version}. "
                f"Available migrations: {list(MIGRATIONS.keys())}"
            )

        # Apply chained migrations
        result = payload.copy()
        for from_v, to_v in zip(path[:-1], path[1:]):
            migration_fn = MIGRATIONS[(from_v, to_v)]
            result = migration_fn(result)
            result["stateweave_version"] = to_v
        return result

    migration_fn = MIGRATIONS[key]
    result = migration_fn(payload.copy())
    result["stateweave_version"] = target_version
    return result


def _find_migration_path(
    from_version: str,
    to_version: str,
) -> Optional[List[str]]:
    """Find a chain of migrations from one version to another using BFS."""
    from collections import deque

    # Build adjacency list from available migrations
    graph: Dict[str, List[str]] = {}
    for src, dst in MIGRATIONS:
        if src not in graph:
            graph[src] = []
        graph[src].append(dst)

    # BFS
    queue = deque([[from_version]])
    visited = {from_version}

    while queue:
        path = queue.popleft()
        current = path[-1]

        if current == to_version:
            return path

        for neighbor in graph.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])

    return None
