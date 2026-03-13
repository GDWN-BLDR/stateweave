"""
Test Coverage Gate (Law 8)
============================
Enforces minimum test file coverage by checking that source modules
have corresponding test files.
"""

import os

from stateweave.compliance.scanner_base import BaseScanner, ScanResult, Violation


class TestCoverageGateScanner(BaseScanner):
    @property
    def name(self) -> str:
        return "test_coverage_gate"

    def scan(self, config: dict, project_root: str) -> ScanResult:
        mode = self._get_mode(config)
        violations = []
        stats = {"source_modules": 0, "tested_modules": 0, "coverage_ratio": 0.0}

        test_dir = os.path.join(project_root, config.get("test_dir", "tests"))
        source_dir = os.path.join(project_root, config.get("source_dir", "stateweave"))
        minimum_ratio = config.get("minimum_test_ratio", 0.5)
        excluded_dirs = config.get("excluded_dirs", [])

        if not os.path.exists(test_dir):
            violations.append(
                Violation(
                    rule=self.name,
                    file="tests/",
                    line=None,
                    message="Test directory not found",
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

        # Collect all source modules (non-init, non-test Python files)
        source_modules = []
        for root, _dirs, files in os.walk(source_dir):
            rel_root = os.path.relpath(root, source_dir)

            # Check excluded dirs
            skip = False
            for excluded in excluded_dirs:
                if rel_root.startswith(excluded):
                    skip = True
                    break
            if skip:
                continue

            for fname in sorted(files):
                if not fname.endswith(".py") or fname.startswith("_"):
                    continue
                source_modules.append(fname[:-3])  # strip .py

        stats["source_modules"] = len(source_modules)

        # Collect all test files
        test_files = set()
        for root, _dirs, files in os.walk(test_dir):
            for fname in sorted(files):
                if fname.startswith("test_") and fname.endswith(".py"):
                    # Extract the module name being tested
                    test_target = fname[5:-3]  # strip test_ prefix and .py
                    test_files.add(test_target)

        # Check coverage
        tested = 0
        untested = []
        for module in source_modules:
            if module in test_files:
                tested += 1
            else:
                untested.append(module)

        stats["tested_modules"] = tested
        stats["coverage_ratio"] = round(tested / max(len(source_modules), 1), 2)

        if stats["coverage_ratio"] < minimum_ratio:
            violations.append(
                Violation(
                    rule=self.name,
                    file="tests/",
                    line=None,
                    message=(
                        f"Test coverage ratio {stats['coverage_ratio']:.0%} "
                        f"is below minimum {minimum_ratio:.0%}. "
                        f"Untested modules: {', '.join(untested[:5])}"
                        + (f" (+{len(untested) - 5} more)" if len(untested) > 5 else "")
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
