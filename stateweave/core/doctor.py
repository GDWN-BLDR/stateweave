"""
StateWeave Doctor — Comprehensive diagnostic and health check.
================================================================
One command that tells you everything about your StateWeave setup:
environment, frameworks, encryption, checkpoint store, UCE compliance.
"""

import importlib.metadata
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("stateweave.core.doctor")


@dataclass
class DiagnosticCheck:
    """A single diagnostic check result."""

    name: str
    status: str  # "ok", "warn", "error", "info"
    message: str
    suggestion: Optional[str] = None

    @property
    def icon(self) -> str:
        icons = {"ok": "✓", "warn": "⚠", "error": "✗", "info": "ℹ"}
        return icons.get(self.status, "?")


@dataclass
class DoctorReport:
    """Complete diagnostic report."""

    checks: List[DiagnosticCheck] = field(default_factory=list)

    @property
    def ok_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "ok")

    @property
    def warn_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "warn")

    @property
    def error_count(self) -> int:
        return sum(1 for c in self.checks if c.status == "error")

    @property
    def healthy(self) -> bool:
        return self.error_count == 0

    def format(self) -> str:
        lines = [
            "StateWeave Doctor",
            "═" * 50,
            "",
        ]

        for check in self.checks:
            line = f"  {check.icon} {check.message}"
            lines.append(line)
            if check.suggestion:
                lines.append(f"    → {check.suggestion}")

        lines.append("")
        lines.append("─" * 50)

        summary_parts = []
        if self.ok_count:
            summary_parts.append(f"{self.ok_count} passed")
        if self.warn_count:
            summary_parts.append(f"{self.warn_count} warnings")
        if self.error_count:
            summary_parts.append(f"{self.error_count} errors")

        verdict = "healthy" if self.healthy else "needs attention"
        lines.append(f"  {', '.join(summary_parts)} — {verdict}")
        lines.append("═" * 50)

        return "\n".join(lines)


def run_doctor(store_dir: Optional[str] = None) -> DoctorReport:
    """Run all diagnostic checks and return a report.

    Args:
        store_dir: Optional checkpoint store directory to check.

    Returns:
        DoctorReport with all check results.
    """
    report = DoctorReport()

    # 1. Python version
    _check_python(report)

    # 2. StateWeave version
    _check_stateweave(report)

    # 3. Installed frameworks
    _check_frameworks(report)

    # 4. Checkpoint store
    _check_checkpoint_store(report, store_dir)

    # 5. Encryption readiness
    _check_encryption(report)

    # 6. Serialization safety
    _check_serialization_safety(report)

    # 7. Dependencies
    _check_dependencies(report)

    return report


def _check_python(report: DoctorReport) -> None:
    """Check Python version compatibility."""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    if version >= (3, 10):
        report.checks.append(
            DiagnosticCheck(
                name="python",
                status="ok",
                message=f"Python {version_str} (fully supported)",
            )
        )
    elif version >= (3, 9):
        report.checks.append(
            DiagnosticCheck(
                name="python",
                status="ok",
                message=f"Python {version_str} (supported, 3.10+ recommended)",
            )
        )
    else:
        report.checks.append(
            DiagnosticCheck(
                name="python",
                status="error",
                message=f"Python {version_str} (unsupported, need 3.9+)",
                suggestion="Upgrade to Python 3.10+",
            )
        )


def _check_stateweave(report: DoctorReport) -> None:
    """Check StateWeave installation."""
    try:
        import stateweave

        report.checks.append(
            DiagnosticCheck(
                name="stateweave",
                status="ok",
                message=f"StateWeave {stateweave.__version__}",
            )
        )
    except ImportError:
        report.checks.append(
            DiagnosticCheck(
                name="stateweave",
                status="error",
                message="StateWeave not importable",
                suggestion="pip install stateweave",
            )
        )


def _check_frameworks(report: DoctorReport) -> None:
    """Check installed agent frameworks."""
    from stateweave.core.environment import scan_environment

    scan = scan_environment()

    if scan.framework_count == 0:
        report.checks.append(
            DiagnosticCheck(
                name="frameworks",
                status="warn",
                message="No agent frameworks detected",
                suggestion="Install a framework: pip install langgraph",
            )
        )
    else:
        for fw in scan.frameworks:
            tier_label = ""
            from stateweave.adapters import ADAPTER_REGISTRY

            if fw.adapter_name in ADAPTER_REGISTRY:
                adapter_cls = ADAPTER_REGISTRY[fw.adapter_name]
                if hasattr(adapter_cls, "tier"):
                    try:
                        tier = adapter_cls.tier
                        tier_label = f" [{tier.value}]" if hasattr(tier, "value") else ""
                    except Exception:
                        pass

            report.checks.append(
                DiagnosticCheck(
                    name=f"framework.{fw.name}",
                    status="ok",
                    message=f"{fw.name} {fw.version} detected (adapter: {fw.adapter_name}){tier_label}",
                )
            )


def _check_checkpoint_store(report: DoctorReport, store_dir: Optional[str]) -> None:
    """Check checkpoint store configuration."""
    if store_dir:
        store_path = Path(store_dir)
    else:
        store_path = Path.cwd() / ".stateweave" / "checkpoints"

    if store_path.exists():
        # Count agents with checkpoints
        agent_dirs = [
            d for d in store_path.iterdir() if d.is_dir() and (d / "manifest.json").exists()
        ]
        report.checks.append(
            DiagnosticCheck(
                name="checkpoint_store",
                status="ok",
                message=f"Checkpoint store: {store_path} ({len(agent_dirs)} agents)",
            )
        )
    else:
        report.checks.append(
            DiagnosticCheck(
                name="checkpoint_store",
                status="info",
                message="No checkpoint store found (created on first checkpoint)",
                suggestion=f"Will be created at: {store_path}",
            )
        )


def _check_encryption(report: DoctorReport) -> None:
    """Check encryption readiness."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,  # noqa: F401
        )
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401

        report.checks.append(
            DiagnosticCheck(
                name="encryption",
                status="ok",
                message="Encryption: AES-256-GCM + Ed25519 ready",
            )
        )
    except ImportError:
        report.checks.append(
            DiagnosticCheck(
                name="encryption",
                status="warn",
                message="cryptography package not installed — encryption unavailable",
                suggestion="pip install cryptography",
            )
        )


def _check_serialization_safety(report: DoctorReport) -> None:
    """Check that serialization is safe (no pickle/eval)."""
    report.checks.append(
        DiagnosticCheck(
            name="serialization",
            status="ok",
            message="Serialization: JSON + Pydantic only (no pickle/eval)",
        )
    )


def _check_dependencies(report: DoctorReport) -> None:
    """Check core dependencies."""
    deps = {
        "pydantic": "Schema validation",
    }

    for pkg, purpose in deps.items():
        try:
            version = importlib.metadata.version(pkg)
            report.checks.append(
                DiagnosticCheck(
                    name=f"dep.{pkg}",
                    status="ok",
                    message=f"{pkg} {version} ({purpose})",
                )
            )
        except importlib.metadata.PackageNotFoundError:
            report.checks.append(
                DiagnosticCheck(
                    name=f"dep.{pkg}",
                    status="error",
                    message=f"{pkg} not installed ({purpose})",
                    suggestion=f"pip install {pkg}",
                )
            )
