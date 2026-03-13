"""
Ruff Code Quality Scanner (Law 9)
====================================
[BOARD 2026-03-13] Enforces code style, formatting, and import hygiene
via ruff. BLOCK mode — no lint or format violations reach production.

This scanner shells out to `ruff check` and `ruff format --check`,
converting violations into UCE-native ScanResult/Violation objects.
"""

import logging
import os
import subprocess
import sys

from stateweave.compliance.scanner_base import BaseScanner, ScanResult, Violation

logger = logging.getLogger("stateweave.compliance.ruff_quality")


class RuffQualityScanner(BaseScanner):
    @property
    def name(self) -> str:
        return "ruff_quality"

    def scan(self, config: dict, project_root: str) -> ScanResult:
        mode = self._get_mode(config)
        violations = []
        stats = {"lint_errors": 0, "format_errors": 0}

        scan_paths = config.get("scan_paths", ["stateweave/", "tests/"])
        abs_paths = [os.path.join(project_root, p) for p in scan_paths]

        # --- Ruff lint check ---
        lint_violations = self._run_ruff_check(abs_paths, project_root, mode)
        violations.extend(lint_violations)
        stats["lint_errors"] = len(lint_violations)

        # --- Ruff format check ---
        format_violations = self._run_ruff_format_check(abs_paths, project_root, mode)
        violations.extend(format_violations)
        stats["format_errors"] = len(format_violations)

        return ScanResult(
            scanner_name=self.name,
            passed=len(violations) == 0,
            mode=mode,
            violations=violations,
            stats=stats,
        )

    def _get_ruff_cmd(self) -> list:
        """Get the ruff command, falling back to sys.executable -m ruff."""
        # Try direct ruff binary first
        try:
            subprocess.run(
                ["ruff", "--version"],
                capture_output=True,
                timeout=5,
            )
            return ["ruff"]
        except FileNotFoundError:
            pass

        # Fall back to python -m ruff
        return [sys.executable, "-m", "ruff"]

    def _run_ruff_check(self, paths: list, project_root: str, mode) -> list:
        """Run `ruff check` and parse violations."""
        violations = []
        try:
            ruff_cmd = self._get_ruff_cmd()
            result = subprocess.run(
                [*ruff_cmd, "check", "--output-format=concise", *paths],
                capture_output=True,
                text=True,
                cwd=project_root,
                timeout=30,
            )

            if result.returncode != 0 and result.stdout.strip():
                for line in result.stdout.strip().splitlines():
                    # Format: path:line:col: CODE message
                    parsed = self._parse_ruff_line(line, project_root)
                    if parsed:
                        file_path, line_num, message = parsed
                        violations.append(
                            Violation(
                                rule=self.name,
                                file=file_path,
                                line=line_num,
                                message=f"ruff lint: {message}",
                                severity=mode,
                            )
                        )
        except FileNotFoundError:
            logger.warning("ruff not found — install with: pip install ruff")
        except subprocess.TimeoutExpired:
            logger.warning("ruff check timed out after 30s")

        return violations

    def _run_ruff_format_check(self, paths: list, project_root: str, mode) -> list:
        """Run `ruff format --check` and parse violations."""
        violations = []
        try:
            ruff_cmd = self._get_ruff_cmd()
            result = subprocess.run(
                [*ruff_cmd, "format", "--check", *paths],
                capture_output=True,
                text=True,
                cwd=project_root,
                timeout=30,
            )

            if result.returncode != 0 and result.stdout.strip():
                for line in result.stdout.strip().splitlines():
                    line = line.strip()
                    if line.startswith("Would reformat:"):
                        file_path = line.replace("Would reformat:", "").strip()
                        rel_path = os.path.relpath(file_path, project_root)
                        violations.append(
                            Violation(
                                rule=self.name,
                                file=rel_path,
                                line=None,
                                message="ruff format: file needs reformatting",
                                severity=mode,
                            )
                        )
        except FileNotFoundError:
            logger.warning("ruff not found — install with: pip install ruff")
        except subprocess.TimeoutExpired:
            logger.warning("ruff format --check timed out after 30s")

        return violations

    @staticmethod
    def _parse_ruff_line(line: str, project_root: str):
        """Parse a concise ruff output line into (file, line_num, message)."""
        # Format: path/to/file.py:42:1: E501 Line too long
        try:
            parts = line.split(":", 3)
            if len(parts) >= 4:
                file_path = os.path.relpath(parts[0].strip(), project_root)
                line_num = int(parts[1].strip())
                message = parts[3].strip()
                return file_path, line_num, message
        except (ValueError, IndexError):
            pass
        return None
