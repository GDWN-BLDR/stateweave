"""
Import Discipline Scanner (Law 7)
===================================
Enforces layered import hierarchy. No cross-layer imports
that violate the dependency graph.
"""

import ast
import os

from stateweave.compliance.scanner_base import BaseScanner, Mode, ScanResult, Violation


class ImportDisciplineScanner(BaseScanner):
    @property
    def name(self) -> str:
        return "import_discipline"

    def scan(self, config: dict, project_root: str) -> ScanResult:
        mode = self._get_mode(config)
        violations = []
        stats = {"files_scanned": 0, "imports_checked": 0}

        layers = config.get("layers", {})

        for layer_name, layer_config in layers.items():
            layer_path = os.path.join(project_root, layer_config.get("path", ""))
            allowed_imports = layer_config.get("may_import", [])

            if not os.path.exists(layer_path):
                continue

            for root, _dirs, files in os.walk(layer_path):
                for fname in sorted(files):
                    if not fname.endswith(".py") or fname.startswith("_"):
                        continue

                    fpath = os.path.join(root, fname)
                    rel_path = os.path.relpath(fpath, project_root)

                    if self._should_skip(rel_path, config):
                        continue

                    stats["files_scanned"] += 1

                    with open(fpath, "r") as f:
                        source = f.read()

                    try:
                        tree = ast.parse(source)
                    except SyntaxError:
                        continue

                    for node in ast.walk(tree):
                        imported_module = None

                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                imported_module = alias.name
                                self._check_import(
                                    imported_module,
                                    layer_name,
                                    allowed_imports,
                                    rel_path,
                                    node.lineno,
                                    violations,
                                    mode,
                                    stats,
                                )
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                imported_module = node.module
                                self._check_import(
                                    imported_module,
                                    layer_name,
                                    allowed_imports,
                                    rel_path,
                                    node.lineno,
                                    violations,
                                    mode,
                                    stats,
                                )

        return ScanResult(
            scanner_name=self.name,
            passed=len(violations) == 0,
            mode=mode,
            violations=violations,
            stats=stats,
        )

    def _check_import(
        self,
        imported_module: str,
        layer_name: str,
        allowed_imports: list,
        file_path: str,
        line: int,
        violations: list,
        mode: Mode,
        stats: dict,
    ):
        """Check if an import violates the layer hierarchy."""
        if not imported_module.startswith("stateweave."):
            return  # External imports are fine

        stats["imports_checked"] += 1

        # Get the target layer from the import
        import_parts = imported_module.split(".")
        if len(import_parts) < 2:
            return

        # The imported stateweave sub-package
        f"stateweave.{import_parts[1]}"

        # Same-layer imports are always allowed
        layer_package = f"stateweave.{layer_name}"
        if imported_module.startswith(layer_package):
            return

        # Check if target is in allowed imports
        is_allowed = any(imported_module.startswith(allowed) for allowed in allowed_imports)

        if not is_allowed:
            violations.append(
                Violation(
                    rule=self.name,
                    file=file_path,
                    line=line,
                    message=(
                        f"Layer '{layer_name}' imports '{imported_module}' "
                        f"which is not in allowed imports: {allowed_imports}"
                    ),
                    severity=mode,
                )
            )
