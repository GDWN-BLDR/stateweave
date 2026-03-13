"""
STATEWEAVE Scanner Base — Interface for all compliance scanners.
================================================================
Every scanner plugin extends BaseScanner and implements scan().
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class Mode(Enum):
    BLOCK = "BLOCK"
    WARN = "WARN"


@dataclass
class Violation:
    """A single compliance violation with evidence."""

    rule: str  # e.g. "schema_integrity"
    file: str  # relative path
    line: Optional[int]  # line number if applicable
    message: str  # human-readable description
    severity: Mode = Mode.BLOCK

    def to_dict(self):
        return {
            "rule": self.rule,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "severity": self.severity.value,
        }


@dataclass
class ScanResult:
    """Result from a scanner run."""

    scanner_name: str
    passed: bool
    mode: Mode
    violations: List[Violation] = field(default_factory=list)
    stats: dict = field(default_factory=dict)  # scanner-specific metrics

    def to_dict(self):
        return {
            "scanner": self.scanner_name,
            "passed": self.passed,
            "mode": self.mode.value,
            "violation_count": len(self.violations),
            "violations": [v.to_dict() for v in self.violations],
            "stats": self.stats,
        }


class BaseScanner(ABC):
    """
    Abstract base class for all UCE scanners.

    Subclasses must implement:
        - name: str property
        - scan(config: dict, project_root: str) -> ScanResult
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Scanner identifier matching rules.yaml key."""
        ...

    @abstractmethod
    def scan(self, config: dict, project_root: str) -> ScanResult:
        """
        Execute the scanner.

        Args:
            config: Scanner-specific config from rules.yaml
            project_root: Absolute path to StateWeave project root

        Returns:
            ScanResult with violations and stats
        """
        ...

    def _get_mode(self, config: dict) -> Mode:
        """Get enforcement mode from config."""
        mode_str = config.get("mode", "BLOCK").upper()
        return Mode.BLOCK if mode_str == "BLOCK" else Mode.WARN

    def _should_skip(self, path: str, config: dict) -> bool:
        """Check if a path should be skipped based on ignore rules.

        Uses prefix-only matching to prevent false positives.
        """
        import os

        global_ignores = config.get("_global_ignore_paths", [])
        normalized = path.replace(os.sep, "/")
        for ignore in global_ignores:
            normalized_ignore = ignore.rstrip("/").replace(os.sep, "/")
            if normalized.startswith(normalized_ignore + "/") or normalized == normalized_ignore:
                return True
        return False
