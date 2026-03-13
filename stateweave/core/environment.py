"""
Environment Scanner — Detect installed agent frameworks in the Python environment.
===================================================================================
Probes the Python environment for installed agent frameworks and returns
configured adapters ready to use, enabling zero-config export.
"""

import importlib.metadata
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from stateweave.adapters import ADAPTER_REGISTRY

logger = logging.getLogger("stateweave.core.environment")

# Package names on PyPI → framework identifiers in our adapter registry
FRAMEWORK_PACKAGES: Dict[str, str] = {
    "langgraph": "langgraph",
    "langgraph-checkpoint": "langgraph",
    "crewai": "crewai",
    "pyautogen": "autogen",
    "autogen-agentchat": "autogen",
    "dspy": "dspy",
    "dspy-ai": "dspy",
    "llama-index": "llamaindex",
    "llama-index-core": "llamaindex",
    "openai-agents": "openai_agents",
    "openai": "openai_agents",
    "haystack-ai": "haystack",
    "farm-haystack": "haystack",
    "letta": "letta",
    "semantic-kernel": "semantic_kernel",
    "mcp": "mcp",
}


@dataclass
class FrameworkInfo:
    """Information about a detected installed framework."""

    name: str
    version: str
    adapter_name: str
    package_name: str
    has_adapter: bool = True


@dataclass
class EnvironmentScan:
    """Results of scanning the Python environment for agent frameworks."""

    frameworks: List[FrameworkInfo] = field(default_factory=list)
    python_version: str = ""
    stateweave_version: str = ""

    @property
    def framework_count(self) -> int:
        return len(self.frameworks)

    @property
    def framework_names(self) -> List[str]:
        return [f.name for f in self.frameworks]

    def has_framework(self, name: str) -> bool:
        return any(f.adapter_name == name for f in self.frameworks)

    def get_framework(self, name: str) -> Optional[FrameworkInfo]:
        for f in self.frameworks:
            if f.adapter_name == name:
                return f
        return None

    def to_report(self) -> str:
        lines = [
            "Environment Scan Results:",
            "─" * 50,
            f"  Python: {self.python_version}",
            f"  StateWeave: {self.stateweave_version}",
            f"  Frameworks detected: {self.framework_count}",
            "",
        ]
        if self.frameworks:
            for fw in sorted(self.frameworks, key=lambda f: f.name):
                status = "✓" if fw.has_adapter else "✗"
                lines.append(
                    f"  {status} {fw.name:<20} v{fw.version:<12} (adapter: {fw.adapter_name})"
                )
        else:
            lines.append("  No agent frameworks detected.")
        lines.append("─" * 50)
        return "\n".join(lines)


def scan_environment() -> EnvironmentScan:
    """Scan the Python environment for installed agent frameworks.

    Checks installed packages against known framework package names
    and returns information about which frameworks are available.

    Returns:
        EnvironmentScan with detected frameworks.
    """
    import sys

    import stateweave

    scan = EnvironmentScan(
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        stateweave_version=stateweave.__version__,
    )

    # Track which adapter names we've already found (avoid duplicates)
    seen_adapters = set()

    for package_name, adapter_name in FRAMEWORK_PACKAGES.items():
        if adapter_name in seen_adapters:
            continue

        try:
            dist = importlib.metadata.distribution(package_name)
            version = dist.version

            has_adapter = adapter_name in ADAPTER_REGISTRY

            scan.frameworks.append(
                FrameworkInfo(
                    name=adapter_name,
                    version=version,
                    adapter_name=adapter_name,
                    package_name=package_name,
                    has_adapter=has_adapter,
                )
            )
            seen_adapters.add(adapter_name)
            logger.debug(f"Detected {adapter_name} v{version} (package: {package_name})")

        except importlib.metadata.PackageNotFoundError:
            continue

    logger.info(f"Environment scan: {scan.framework_count} frameworks detected")
    return scan


def auto_select_adapter(scan: Optional[EnvironmentScan] = None):
    """Auto-select the best adapter based on installed frameworks.

    Priority order: langgraph > mcp > crewai > autogen > others.

    Args:
        scan: Pre-computed environment scan. If None, scans now.

    Returns:
        Tuple of (adapter_name, adapter_class) or (None, None).
    """
    if scan is None:
        scan = scan_environment()

    # Priority order for auto-selection
    priority = [
        "langgraph",
        "mcp",
        "crewai",
        "autogen",
        "dspy",
        "llamaindex",
        "openai_agents",
        "haystack",
        "letta",
        "semantic_kernel",
    ]

    for name in priority:
        if scan.has_framework(name) and name in ADAPTER_REGISTRY:
            return name, ADAPTER_REGISTRY[name]

    return None, None
