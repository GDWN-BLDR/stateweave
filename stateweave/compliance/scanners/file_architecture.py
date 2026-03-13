"""
File Architecture Scanner
==========================
Detects orphan files not registered in MANIFEST.md.
"""

import os
import re

from stateweave.compliance.scanner_base import BaseScanner, ScanResult, Violation


class FileArchitectureScanner(BaseScanner):
    @property
    def name(self) -> str:
        return "file_architecture"

    def scan(self, config: dict, project_root: str) -> ScanResult:
        mode = self._get_mode(config)
        violations = []
        stats = {"files_found": 0, "registered": 0, "orphans": 0}

        manifest_path = os.path.join(project_root, config.get("manifest_path", "board/MANIFEST.md"))
        scan_paths = config.get("scan_paths", ["stateweave/", "scripts/"])

        # Read manifest and extract all referenced paths
        registered_paths = set()
        if os.path.exists(manifest_path):
            with open(manifest_path, "r") as f:
                content = f.read()
            # Extract paths from markdown table cells (backtick-wrapped)
            path_pattern = re.compile(r"`([^`]+\.(?:py|yaml|yml))`")
            for match in path_pattern.finditer(content):
                registered_paths.add(match.group(1))

        # Scan project files
        for scan_path in scan_paths:
            abs_path = os.path.join(project_root, scan_path)
            if not os.path.exists(abs_path):
                continue

            for root, _dirs, files in os.walk(abs_path):
                for fname in sorted(files):
                    if not fname.endswith((".py", ".yaml", ".yml")):
                        continue
                    if fname.startswith("_"):
                        continue

                    fpath = os.path.join(root, fname)
                    rel_path = os.path.relpath(fpath, project_root)
                    stats["files_found"] += 1

                    if self._should_skip(rel_path, config):
                        continue

                    # Check if registered
                    if rel_path in registered_paths:
                        stats["registered"] += 1
                    else:
                        stats["orphans"] += 1
                        violations.append(
                            Violation(
                                rule=self.name,
                                file=rel_path,
                                line=None,
                                message="File not registered in MANIFEST.md",
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
