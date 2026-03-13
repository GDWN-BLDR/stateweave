"""
Adapter Contract Scanner (Law 4)
=================================
Ensures all adapter files extend StateWeaveAdapter ABC
and implement required methods/properties.
"""

import ast
import os

from stateweave.compliance.scanner_base import BaseScanner, ScanResult, Violation


class AdapterContractScanner(BaseScanner):
    @property
    def name(self) -> str:
        return "adapter_contract"

    def scan(self, config: dict, project_root: str) -> ScanResult:
        mode = self._get_mode(config)
        violations = []
        stats = {"adapters_checked": 0, "compliant": 0}

        adapters_dir = os.path.join(project_root, config.get("adapters_dir", "stateweave/adapters"))
        required_methods = config.get("required_methods", [])
        required_properties = config.get("required_properties", [])
        base_class = config.get("base_class", "StateWeaveAdapter")

        if not os.path.exists(adapters_dir):
            return ScanResult(
                scanner_name=self.name,
                passed=True,
                mode=mode,
                violations=[],
                stats={"adapters_checked": 0, "compliant": 0},
            )

        for fname in sorted(os.listdir(adapters_dir)):
            if not fname.endswith(".py") or fname.startswith("_") or fname == "base.py":
                continue

            fpath = os.path.join(adapters_dir, fname)
            rel_path = os.path.relpath(fpath, project_root)
            stats["adapters_checked"] += 1

            with open(fpath, "r") as f:
                source = f.read()

            try:
                tree = ast.parse(source)
            except SyntaxError as e:
                violations.append(
                    Violation(
                        rule=self.name,
                        file=rel_path,
                        line=e.lineno,
                        message=f"Syntax error: {e.msg}",
                        severity=mode,
                    )
                )
                continue

            # Find classes that extend the base class
            adapter_classes = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        base_name = ""
                        if isinstance(base, ast.Name):
                            base_name = base.id
                        elif isinstance(base, ast.Attribute):
                            base_name = base.attr
                        if base_name == base_class:
                            adapter_classes.append(node)

            if not adapter_classes:
                violations.append(
                    Violation(
                        rule=self.name,
                        file=rel_path,
                        line=None,
                        message=f"No class extending {base_class} found in adapter file",
                        severity=mode,
                    )
                )
                continue

            for cls_node in adapter_classes:
                method_names = set()
                for item in cls_node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_names.add(item.name)

                # Check required methods
                for method in required_methods:
                    if method not in method_names:
                        violations.append(
                            Violation(
                                rule=self.name,
                                file=rel_path,
                                line=cls_node.lineno,
                                message=f"Class '{cls_node.name}' missing required method: {method}",
                                severity=mode,
                            )
                        )

                # Check required properties
                for prop in required_properties:
                    if prop not in method_names:
                        violations.append(
                            Violation(
                                rule=self.name,
                                file=rel_path,
                                line=cls_node.lineno,
                                message=f"Class '{cls_node.name}' missing required property: {prop}",
                                severity=mode,
                            )
                        )

            if not any(v.file == rel_path for v in violations):
                stats["compliant"] += 1

        return ScanResult(
            scanner_name=self.name,
            passed=len(violations) == 0,
            mode=mode,
            violations=violations,
            stats=stats,
        )
