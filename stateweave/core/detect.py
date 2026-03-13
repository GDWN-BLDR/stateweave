"""
Framework Auto-Detection — Identify the source framework from state data.
===========================================================================
Analyzes a state blob (dict, JSON string, or file) and returns the most
likely framework that produced it, with a confidence score.

This is Flywheel Feature #5 — makes adoption even easier by eliminating
the need to know what framework you're migrating FROM.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

logger = logging.getLogger("stateweave.core.detect")


# Framework signature patterns — unique keys or structures that identify
# which framework produced a given state blob
FRAMEWORK_SIGNATURES: Dict[str, Dict[str, Any]] = {
    "langgraph": {
        "strong_keys": [
            "checkpoint_id",
            "channel_values",
            "__channel_versions__",
            "checkpoint_ns",
        ],
        "moderate_keys": ["messages", "configurable"],
        "structure_hints": ["thread_id"],
        "message_type_values": ["HumanMessage", "AIMessage", "ToolMessage"],
    },
    "dspy": {
        "strong_keys": ["signature", "demos", "_compiled", "lm"],
        "moderate_keys": ["traces", "train", "metadata"],
        "structure_hints": [],
        "message_type_values": [],
    },
    "llamaindex": {
        "strong_keys": [
            "memory_blocks",
            "_vector_store_ref",
            "_storage_context",
        ],
        "moderate_keys": ["chat_history", "context"],
        "structure_hints": ["chat_store"],
        "message_type_values": [],
    },
    "openai_agents": {
        "strong_keys": ["session_messages", "handoffs", "_session_backend"],
        "moderate_keys": ["instructions", "model", "tools"],
        "structure_hints": ["developer"],
        "message_type_values": [],
    },
    "haystack": {
        "strong_keys": [
            "_pipeline_ref",
            "_document_store_ref",
            "long_term_memories",
        ],
        "moderate_keys": ["messages", "tools"],
        "structure_hints": [],
        "message_type_values": [],
    },
    "letta": {
        "strong_keys": [
            "core_memory",
            "archival_memory",
            "recall_memory",
            "_persistence_manager_ref",
        ],
        "moderate_keys": ["system", "tools"],
        "structure_hints": ["inner_thoughts"],
        "message_type_values": [],
    },
    "semantic_kernel": {
        "strong_keys": [
            "thread_state",
            "_kernel_ref",
            "_service_id",
            "plugins",
        ],
        "moderate_keys": ["chat_history", "instructions"],
        "structure_hints": [],
        "message_type_values": [],
    },
    "crewai": {
        "strong_keys": ["crew_output", "agents", "tasks", "kickoff_output"],
        "moderate_keys": ["tools", "verbose"],
        "structure_hints": [],
        "message_type_values": [],
    },
    "autogen": {
        "strong_keys": [
            "chat_history",
            "oai_messages",
            "groupchat",
            "_oai_system_message",
        ],
        "moderate_keys": ["messages", "human_input_mode"],
        "structure_hints": ["ConversableAgent"],
        "message_type_values": [],
    },
    "mcp": {
        "strong_keys": [
            "server_capabilities",
            "tools",
            "resources",
            "prompts",
        ],
        "moderate_keys": ["server_name", "protocol_version"],
        "structure_hints": ["mcp"],
        "message_type_values": [],
    },
}


def detect_framework(
    state: Union[str, Dict, Path],
    top_n: int = 3,
) -> List[Tuple[str, float]]:
    """Detect the most likely source framework for a state blob.

    Args:
        state: State data as a dict, JSON string, or path to a JSON file.
        top_n: Number of top predictions to return.

    Returns:
        List of (framework_name, confidence_score) tuples, sorted by
        confidence descending. Confidence is 0.0 to 1.0.

    Example:
        >>> results = detect_framework({"signature": {...}, "demos": [...]})
        >>> results[0]
        ("dspy", 0.95)
    """
    # Parse input
    if isinstance(state, (str, Path)):
        path = Path(state)
        if path.exists() and path.is_file():
            with open(path) as f:
                data = json.load(f)
        else:
            # Try parsing as JSON string
            try:
                data = json.loads(str(state))
            except json.JSONDecodeError:
                logger.warning("Could not parse state as JSON")
                return [("unknown", 0.0)]
    elif isinstance(state, dict):
        data = state
    else:
        logger.warning(f"Unsupported state type: {type(state)}")
        return [("unknown", 0.0)]

    # Score each framework
    scores: Dict[str, float] = {}
    all_keys = _flatten_keys(data)

    for framework, signatures in FRAMEWORK_SIGNATURES.items():
        score = 0.0

        # Strong keys: 0.25 each (max 1.0 from strong keys)
        strong_matches = sum(1 for k in signatures["strong_keys"] if k in all_keys)
        score += min(strong_matches * 0.25, 1.0)

        # Moderate keys: 0.1 each (max 0.3)
        moderate_matches = sum(1 for k in signatures["moderate_keys"] if k in all_keys)
        score += min(moderate_matches * 0.1, 0.3)

        # Structure hints: 0.1 each (max 0.2) — values containing hints
        all_values_str = json.dumps(data)
        hint_matches = sum(1 for h in signatures["structure_hints"] if h in all_values_str)
        score += min(hint_matches * 0.1, 0.2)

        # Message type values: 0.15 each (max 0.3)
        type_matches = sum(1 for t in signatures["message_type_values"] if t in all_values_str)
        score += min(type_matches * 0.15, 0.3)

        # Normalize to [0, 1]
        scores[framework] = min(score, 1.0)

    # Sort by confidence
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Filter out zero-confidence predictions
    ranked = [(name, round(conf, 2)) for name, conf in ranked if conf > 0.0]

    return ranked[:top_n] if ranked else [("unknown", 0.0)]


def _flatten_keys(data: Dict[str, Any], prefix: str = "") -> set:
    """Recursively collect all keys from a nested dict."""
    keys = set()
    if isinstance(data, dict):
        for k, v in data.items():
            keys.add(k)
            if isinstance(v, dict):
                keys.update(_flatten_keys(v, f"{prefix}{k}."))
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        keys.update(_flatten_keys(item, f"{prefix}{k}[]."))
    return keys
