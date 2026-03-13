"""
Serialization Safety Scanner (Law 3)
=====================================
Detects side-channel serialization that bypasses StateWeaveSerializer.
Catches raw pickle, msgpack, or json.dumps usage outside allowed files.
"""

import os

from stateweave.compliance.scanner_base import BaseScanner, ScanResult, Violation


class SerializationSafetyScanner(BaseScanner):
    @property
    def name(self) -> str:
        return "serialization_safety"

    def scan(self, config: dict, project_root: str) -> ScanResult:
        mode = self._get_mode(config)
        violations = []
        stats = {"files_scanned": 0, "violations_found": 0}

        forbidden_patterns = config.get("forbidden_patterns", [])
        allowed_in = config.get("allowed_in", [])
        scan_paths = config.get("scan_paths", ["stateweave/"])

        for scan_path in scan_paths:
            abs_scan_path = os.path.join(project_root, scan_path)
            if not os.path.exists(abs_scan_path):
                continue

            for root, _dirs, files in os.walk(abs_scan_path):
                for fname in sorted(files):
                    if not fname.endswith(".py"):
                        continue

                    fpath = os.path.join(root, fname)
                    rel_path = os.path.relpath(fpath, project_root)

                    if self._should_skip(rel_path, config):
                        continue

                    # Check if file is in allowed list
                    is_allowed = any(
                        rel_path.startswith(allowed.rstrip("/")) for allowed in allowed_in
                    )
                    if is_allowed:
                        continue

                    stats["files_scanned"] += 1

                    with open(fpath, "r") as f:
                        lines = f.readlines()

                    for line_num, line in enumerate(lines, 1):
                        # Skip comments
                        stripped = line.strip()
                        if stripped.startswith("#"):
                            continue

                        for pattern in forbidden_patterns:
                            if pattern in line:
                                violations.append(
                                    Violation(
                                        rule=self.name,
                                        file=rel_path,
                                        line=line_num,
                                        message=f"Forbidden serialization pattern '{pattern}' — use StateWeaveSerializer",
                                        severity=mode,
                                    )
                                )
                                stats["violations_found"] += 1

        return ScanResult(
            scanner_name=self.name,
            passed=len(violations) == 0,
            mode=mode,
            violations=violations,
            stats=stats,
        )
