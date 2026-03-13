"""
STATEWEAVE Scanner Registry — Auto-discovers and loads scanner plugins.
=======================================================================
Reads rules.yaml, discovers scanners in compliance/scanners/,
and provides the scanner list to the UCE runner.
"""

import importlib
import inspect
import logging
import os
from typing import List, Tuple

import yaml

logger = logging.getLogger("stateweave.compliance.registry")

from stateweave.compliance.scanner_base import BaseScanner


def load_rules(project_root: str) -> dict:
    """Load rules.yaml from the compliance package."""
    rules_path = os.path.join(project_root, "stateweave", "compliance", "rules.yaml")
    if not os.path.exists(rules_path):
        raise FileNotFoundError(f"Compliance rules not found: {rules_path}")

    with open(rules_path) as f:
        return yaml.safe_load(f) or {}


def discover_scanners(project_root: str) -> List[BaseScanner]:
    """
    Auto-discover all scanner plugins in compliance/scanners/.

    Each .py file in the scanners directory must contain a class
    that extends BaseScanner.
    """
    scanners_dir = os.path.join(project_root, "stateweave", "compliance", "scanners")
    discovered = []

    if not os.path.exists(scanners_dir):
        return discovered

    for fname in sorted(os.listdir(scanners_dir)):
        if not fname.endswith(".py") or fname.startswith("_"):
            continue

        module_name = f"stateweave.compliance.scanners.{fname[:-3]}"
        try:
            module = importlib.import_module(module_name)
        except ImportError as e:
            logger.error(f"Failed to import scanner {module_name}: {e}")
            continue

        # Find scanner classes in the module
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, BaseScanner) and obj is not BaseScanner:
                try:
                    instance = obj()
                    discovered.append(instance)
                except Exception as e:
                    logger.error(f"Failed to instantiate scanner {name}: {e}")

    return discovered


def get_enabled_scanners(
    scanners: List[BaseScanner], rules: dict
) -> List[Tuple[BaseScanner, dict]]:
    """
    Filter scanners to only those enabled in rules.yaml.

    Returns list of (scanner, scanner_config) tuples.
    """
    global_config = rules.get("global", {})
    ignore_paths = global_config.get("ignore_paths", [])

    enabled = []
    for scanner in scanners:
        scanner_config = rules.get(scanner.name, {})
        if not scanner_config.get("enabled", False):
            continue

        # Inject global ignore paths into scanner config
        scanner_config["_global_ignore_paths"] = ignore_paths
        enabled.append((scanner, scanner_config))

    return enabled
