"""
Logger Naming Scanner (Law 1)
===============================
Enforces stateweave.* logger naming convention.
"""

import os
import re

from stateweave.compliance.scanner_base import BaseScanner, ScanResult, Violation


class LoggerNamingScanner(BaseScanner):
    @property
    def name(self) -> str:
        return "logger_naming"

    def scan(self, config: dict, project_root: str) -> ScanResult:
        mode = self._get_mode(config)
        violations = []
        stats = {"files_scanned": 0, "loggers_found": 0, "compliant": 0}

        required_prefix = config.get("required_prefix", "stateweave.")
        scan_paths = config.get("scan_paths", ["stateweave/"])
        ignore_files = config.get("ignore_files", [])

        # Pattern to match getLogger calls
        logger_pattern = re.compile(
            r'(?:logging\.getLogger|getLogger)\s*\(\s*["\']([^"\']+)["\']\s*\)'
        )

        for scan_path in scan_paths:
            abs_scan_path = os.path.join(project_root, scan_path)
            if not os.path.exists(abs_scan_path):
                continue

            for root, _dirs, files in os.walk(abs_scan_path):
                for fname in sorted(files):
                    if not fname.endswith(".py"):
                        continue
                    if fname in ignore_files:
                        continue

                    fpath = os.path.join(root, fname)
                    rel_path = os.path.relpath(fpath, project_root)

                    if self._should_skip(rel_path, config):
                        continue

                    stats["files_scanned"] += 1

                    with open(fpath, "r") as f:
                        content = f.read()

                    for match in logger_pattern.finditer(content):
                        logger_name = match.group(1)
                        stats["loggers_found"] += 1

                        # Find line number
                        line_num = content[: match.start()].count("\n") + 1

                        if logger_name.startswith(required_prefix):
                            stats["compliant"] += 1
                        else:
                            violations.append(
                                Violation(
                                    rule=self.name,
                                    file=rel_path,
                                    line=line_num,
                                    message=(
                                        f"Logger '{logger_name}' does not use "
                                        f"'{required_prefix}*' convention"
                                    ),
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
