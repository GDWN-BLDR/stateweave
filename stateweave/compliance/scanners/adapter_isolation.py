"""
Adapter Isolation Scanner
==========================
Ensures adapters work without their target framework installed.

This scanner catches the exact class of bug that broke CI:
- Adapters that call _require_framework() unconditionally in
  export_state/import_state, blocking the fallback/mock path.
- Adapters must guard _require_framework() so unit tests can
  run without installing every framework.

The rule: _require_framework() must be inside a conditional branch
(if self._graph, if self._checkpointer, etc.), never at the top
level of export_state/import_state.

Additionally checks CI workflow dependency pins for conflicts.
"""

import ast
import os
import re
import subprocess
import sys
from typing import List

from stateweave.compliance.scanner_base import BaseScanner, Mode, ScanResult, Violation


class AdapterIsolationScanner(BaseScanner):
    @property
    def name(self) -> str:
        return "adapter_isolation"

    def scan(self, config: dict, project_root: str) -> ScanResult:
        mode = self._get_mode(config)
        violations: List[Violation] = []
        stats = {"adapters_checked": 0, "pins_checked": 0}

        # --- Check 1: Adapter _require_framework usage ---
        adapters_dir = os.path.join(project_root, config.get("adapters_dir", "stateweave/adapters"))

        if os.path.exists(adapters_dir):
            for fname in sorted(os.listdir(adapters_dir)):
                if not fname.endswith(".py") or fname.startswith("_") or fname == "base.py":
                    continue

                fpath = os.path.join(adapters_dir, fname)
                rel_path = os.path.relpath(fpath, project_root)
                stats["adapters_checked"] += 1

                with open(fpath) as f:
                    source = f.read()

                try:
                    tree = ast.parse(source)
                except SyntaxError:
                    continue

                violations.extend(self._check_require_framework_guarded(tree, rel_path, mode))

        # --- Check 2: CI workflow dependency pins ---
        workflows_dir = os.path.join(project_root, ".github", "workflows")
        if os.path.exists(workflows_dir):
            for fname in sorted(os.listdir(workflows_dir)):
                if not fname.endswith((".yml", ".yaml")):
                    continue
                fpath = os.path.join(workflows_dir, fname)
                rel_path = os.path.relpath(fpath, project_root)

                with open(fpath) as f:
                    content = f.read()

                pin_violations = self._check_dependency_pins(content, rel_path, mode, project_root)
                stats["pins_checked"] += len(pin_violations) or 1
                violations.extend(pin_violations)

        return ScanResult(
            scanner_name=self.name,
            passed=len(violations) == 0,
            mode=mode,
            violations=violations,
            stats=stats,
        )

    def _check_require_framework_guarded(
        self, tree: ast.Module, rel_path: str, mode: Mode
    ) -> List[Violation]:
        """Check that _require_framework calls are inside conditional branches."""
        violations = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue

            for item in node.body:
                if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue

                if item.name not in ("export_state", "import_state"):
                    continue

                # Walk the function body at the TOP LEVEL only
                for stmt in item.body:
                    if self._is_unguarded_require_framework(stmt):
                        violations.append(
                            Violation(
                                rule=self.name,
                                file=rel_path,
                                line=stmt.lineno,
                                message=(
                                    f"_require_framework() called unconditionally in "
                                    f"{node.name}.{item.name}(). Must be inside a "
                                    f"conditional (if self._graph, etc.) so the adapter "
                                    f"works without the framework installed."
                                ),
                                severity=mode,
                            )
                        )
        return violations

    def _is_unguarded_require_framework(self, stmt: ast.stmt) -> bool:
        """Check if a statement is a bare _require_framework call (not inside an if)."""
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            return self._is_require_framework_call(stmt.value)
        return False

    def _is_require_framework_call(self, node: ast.Call) -> bool:
        """Check if a Call node is self._require_framework(...)."""
        if isinstance(node.func, ast.Attribute):
            return node.func.attr == "_require_framework"
        return False

    def _check_dependency_pins(
        self, content: str, rel_path: str, mode: Mode, project_root: str
    ) -> List[Violation]:
        """Check that pinned dependency specs in CI actually resolve."""
        violations = []

        # Find pip-install lines with pinned versions (e.g., "langgraph==0.2.62 langchain-core==0.3.0")
        pin_pattern = re.compile(r'pip-install:\s*["\'](.+?)["\']', re.MULTILINE)

        for match in pin_pattern.finditer(content):
            pip_spec = match.group(1)
            # Only check if there are 2+ pinned packages (conflict risk)
            pinned_pkgs = re.findall(r"(\S+==\S+)", pip_spec)
            if len(pinned_pkgs) < 2:
                continue

            line_num = content[: match.start()].count("\n") + 1

            # Dry-run pip install to check for conflicts
            try:
                result_full = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "--dry-run",
                        *pinned_pkgs,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result_full.returncode != 0 and "conflict" in result_full.stderr.lower():
                    violations.append(
                        Violation(
                            rule=self.name,
                            file=rel_path,
                            line=line_num,
                            message=(
                                f"Pinned dependency conflict: '{pip_spec}' — "
                                f"pip cannot resolve these versions together"
                            ),
                            severity=mode,
                        )
                    )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass  # Can't check, skip

        return violations
