"""
Schema Integrity Scanner (Law 2)
=================================
Validates that Universal Schema Pydantic models exist and contain required fields.
"""

import ast
import os

from stateweave.compliance.scanner_base import BaseScanner, ScanResult, Violation


class SchemaIntegrityScanner(BaseScanner):
    @property
    def name(self) -> str:
        return "schema_integrity"

    def scan(self, config: dict, project_root: str) -> ScanResult:
        mode = self._get_mode(config)
        violations = []
        stats = {"schema_files_checked": 0, "required_fields_found": 0}

        schema_module = config.get("schema_module", "stateweave.schema.v1")
        required_fields = config.get("required_fields", [])

        # Convert module path to file path
        schema_path = os.path.join(project_root, schema_module.replace(".", os.sep) + ".py")

        if not os.path.exists(schema_path):
            violations.append(
                Violation(
                    rule=self.name,
                    file=schema_path,
                    line=None,
                    message=f"Schema module not found: {schema_module}",
                    severity=mode,
                )
            )
            return ScanResult(
                scanner_name=self.name,
                passed=False,
                mode=mode,
                violations=violations,
                stats=stats,
            )

        stats["schema_files_checked"] = 1

        # Parse the schema file and look for required fields in class definitions
        with open(schema_path, "r") as f:
            source = f.read()

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            violations.append(
                Violation(
                    rule=self.name,
                    file=schema_path,
                    line=e.lineno,
                    message=f"Syntax error in schema module: {e.msg}",
                    severity=mode,
                )
            )
            return ScanResult(
                scanner_name=self.name,
                passed=False,
                mode=mode,
                violations=violations,
                stats=stats,
            )

        # Collect all field names from class definitions (Pydantic models)
        all_fields = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        all_fields.add(item.target.id)

        # Check required fields
        for field_name in required_fields:
            if field_name in all_fields:
                stats["required_fields_found"] += 1
            else:
                violations.append(
                    Violation(
                        rule=self.name,
                        file=schema_path,
                        line=None,
                        message=f"Required schema field '{field_name}' not found in any model class",
                        severity=mode,
                    )
                )

        return ScanResult(
            scanner_name=self.name,
            passed=len(violations) == 0,
            mode=mode,
            violations=violations,
            stats=stats,
        )
