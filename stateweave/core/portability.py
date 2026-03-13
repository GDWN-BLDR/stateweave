"""
Portability Analyzer — Non-portable state detection.
======================================================
Detects state elements that cannot be fully transferred
between frameworks and generates non_portable_warnings[].
"""

import logging
from typing import Any, Dict, List, Optional

from stateweave.schema.v1 import NonPortableWarning, NonPortableWarningSeverity

logger = logging.getLogger("stateweave.core.portability")

# Known non-portable Python types
NON_PORTABLE_TYPES: Dict[str, str] = {
    "sqlite3.Cursor": "Database cursors cannot be serialized across processes",
    "sqlite3.Connection": "Database connections are process-bound",
    "socket.socket": "Network sockets cannot be serialized",
    "threading.Thread": "Thread objects are OS/runtime-specific",
    "threading.Lock": "Locks are process-specific synchronization primitives",
    "asyncio.Task": "Async tasks are runtime-specific",
    "asyncio.Future": "Futures are runtime-specific",
    "_io.TextIOWrapper": "File handles cannot be serialized",
    "_io.BufferedReader": "File handles cannot be serialized",
    "generator": "Generator objects maintain internal execution state",
    "coroutine": "Coroutine objects maintain internal execution state",
    "weakref": "Weak references are process-specific",
}

# Framework-specific non-portable elements
FRAMEWORK_NON_PORTABLE: Dict[str, List[Dict[str, str]]] = {
    "langgraph": [
        {
            "field_pattern": "__channel_versions__",
            "reason": "LangGraph internal channel tracking metadata",
            "severity": "WARN",
        },
        {
            "field_pattern": "checkpoint_id",
            "reason": "UUID specific to LangGraph storage backend",
            "severity": "INFO",
        },
        {
            "field_pattern": "pending_writes",
            "reason": "In-progress operations not yet committed",
            "severity": "WARN",
        },
        {
            "field_pattern": "task.id",
            "reason": "Execution-specific task identifier",
            "severity": "INFO",
        },
    ],
    "mcp": [
        {
            "field_pattern": "_meta",
            "reason": "MCP server-specific metadata",
            "severity": "INFO",
        },
        {
            "field_pattern": "oauth_token",
            "reason": "Security-sensitive credentials must not transfer",
            "severity": "CRITICAL",
        },
        {
            "field_pattern": "sse_stream",
            "reason": "Server-sent events stream cursor is server-specific",
            "severity": "WARN",
        },
    ],
}


class PortabilityAnalyzer:
    """Analyzes state payloads for non-portable elements.

    Examines working memory, tool results, and custom state fields
    to identify elements that cannot safely transfer between frameworks.
    """

    def __init__(self, source_framework: Optional[str] = None):
        """Initialize the analyzer.

        Args:
            source_framework: The source framework name for
                              framework-specific detection rules.
        """
        self._source_framework = source_framework

    def analyze(self, state_dict: Dict[str, Any]) -> List[NonPortableWarning]:
        """Analyze a state dictionary for non-portable elements.

        Args:
            state_dict: The cognitive state dictionary to analyze.

        Returns:
            List of NonPortableWarning instances.
        """
        warnings: List[NonPortableWarning] = []

        # Check for non-portable Python types in values
        self._scan_values(state_dict, "", warnings)

        # Check for framework-specific non-portable fields
        if self._source_framework:
            self._check_framework_fields(state_dict, self._source_framework, warnings)

        # Check for potentially sensitive data
        self._check_sensitive_data(state_dict, "", warnings)

        logger.info(
            f"Portability analysis complete: {len(warnings)} warning(s) "
            f"for framework '{self._source_framework or 'unknown'}'"
        )

        return warnings

    def _scan_values(
        self,
        obj: Any,
        path: str,
        warnings: List[NonPortableWarning],
    ) -> None:
        """Recursively scan values for non-portable types."""
        type_name = type(obj).__module__ + "." + type(obj).__qualname__

        # Check against known non-portable types
        for np_type, reason in NON_PORTABLE_TYPES.items():
            if np_type in type_name:
                warnings.append(
                    NonPortableWarning(
                        field=path or "root",
                        reason=reason,
                        severity=NonPortableWarningSeverity.WARN,
                        data_loss=True,
                        original_type=type_name,
                        recommendation=f"Re-initialize {np_type.split('.')[-1]} after import",
                    )
                )
                return

        # Recurse into containers
        if isinstance(obj, dict):
            for key, value in obj.items():
                child_path = f"{path}.{key}" if path else str(key)
                self._scan_values(value, child_path, warnings)
        elif isinstance(obj, (list, tuple)):
            for i, item in enumerate(obj):
                child_path = f"{path}[{i}]"
                self._scan_values(item, child_path, warnings)

    def _check_framework_fields(
        self,
        state_dict: Dict[str, Any],
        framework: str,
        warnings: List[NonPortableWarning],
    ) -> None:
        """Check for framework-specific non-portable fields."""
        framework_rules = FRAMEWORK_NON_PORTABLE.get(framework, [])

        for rule in framework_rules:
            pattern = rule["field_pattern"]
            matches = self._find_matching_fields(state_dict, pattern)

            for match_path in matches:
                severity = NonPortableWarningSeverity(rule.get("severity", "WARN"))
                warnings.append(
                    NonPortableWarning(
                        field=match_path,
                        reason=rule["reason"],
                        severity=severity,
                        data_loss=severity != NonPortableWarningSeverity.INFO,
                        recommendation=(
                            f"This field is specific to {framework} and will be "
                            f"stripped during export"
                        ),
                    )
                )

    def _find_matching_fields(
        self,
        obj: Any,
        pattern: str,
        path: str = "",
    ) -> List[str]:
        """Find all fields matching a pattern in a nested structure."""
        matches = []

        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                if pattern in key:
                    matches.append(current_path)
                matches.extend(self._find_matching_fields(value, pattern, current_path))
        elif isinstance(obj, (list, tuple)):
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]"
                matches.extend(self._find_matching_fields(item, pattern, current_path))

        return matches

    def _check_sensitive_data(
        self,
        obj: Any,
        path: str,
        warnings: List[NonPortableWarning],
    ) -> None:
        """Check for potentially sensitive data that shouldn't transfer."""
        sensitive_patterns = [
            "api_key",
            "secret",
            "password",
            "token",
            "credential",
            "private_key",
            "access_key",
        ]

        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                key_lower = key.lower()

                for pattern in sensitive_patterns:
                    if pattern in key_lower:
                        warnings.append(
                            NonPortableWarning(
                                field=current_path,
                                reason=f"Potentially sensitive field '{key}' detected",
                                severity=NonPortableWarningSeverity.CRITICAL,
                                data_loss=True,
                                recommendation=(
                                    "Sensitive credentials should be stripped before "
                                    "state export. Use environment variables instead."
                                ),
                            )
                        )
                        break

                self._check_sensitive_data(value, current_path, warnings)
        elif isinstance(obj, (list, tuple)):
            for i, item in enumerate(obj):
                self._check_sensitive_data(item, f"{path}[{i}]", warnings)
