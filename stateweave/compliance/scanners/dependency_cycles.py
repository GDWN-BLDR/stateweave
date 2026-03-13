"""
Dependency Cycles Scanner
===========================
Detects circular import dependencies in the stateweave package.
"""

import ast
import os
from collections import defaultdict

from stateweave.compliance.scanner_base import BaseScanner, ScanResult, Violation


class DependencyCyclesScanner(BaseScanner):
    @property
    def name(self) -> str:
        return "dependency_cycles"

    def scan(self, config: dict, project_root: str) -> ScanResult:
        mode = self._get_mode(config)
        violations = []
        stats = {"files_scanned": 0, "edges": 0, "cycles_found": 0}

        scan_paths = config.get("scan_paths", ["stateweave/"])
        max_depth = config.get("max_depth", 10)

        # Build import graph
        graph = defaultdict(set)

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

                    # Convert file path to module name
                    module_name = rel_path.replace(os.sep, ".").replace("/", ".")[:-3]
                    if module_name.endswith(".__init__"):
                        module_name = module_name[:-9]

                    stats["files_scanned"] += 1

                    with open(fpath, "r") as f:
                        source = f.read()

                    try:
                        tree = ast.parse(source)
                    except SyntaxError:
                        continue

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                if alias.name.startswith("stateweave."):
                                    graph[module_name].add(alias.name)
                                    stats["edges"] += 1
                        elif isinstance(node, ast.ImportFrom):
                            if node.module and node.module.startswith("stateweave."):
                                graph[module_name].add(node.module)
                                stats["edges"] += 1

        # Detect cycles using DFS
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node, path):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if len(path) < max_depth:
                        result = dfs(neighbor, path + [neighbor])
                        if result:
                            return result
                elif neighbor in rec_stack:
                    cycle_start = path.index(neighbor) if neighbor in path else -1
                    if cycle_start >= 0:
                        cycle = path[cycle_start:] + [neighbor]
                    else:
                        cycle = [node, neighbor]
                    cycles.append(cycle)
                    return cycle

            rec_stack.discard(node)
            return None

        for module in sorted(graph.keys()):
            if module not in visited:
                dfs(module, [module])

        stats["cycles_found"] = len(cycles)

        for cycle in cycles:
            cycle_str = " → ".join(cycle)
            violations.append(
                Violation(
                    rule=self.name,
                    file=cycle[0].replace(".", "/") + ".py",
                    line=None,
                    message=f"Circular dependency: {cycle_str}",
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
