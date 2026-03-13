"""
MCP Protocol Scanner
=====================
Validates MCP server implementation has all required tools.
"""

import ast
import os

from stateweave.compliance.scanner_base import BaseScanner, ScanResult, Violation


class MCPProtocolScanner(BaseScanner):
    @property
    def name(self) -> str:
        return "mcp_protocol"

    def scan(self, config: dict, project_root: str) -> ScanResult:
        mode = self._get_mode(config)
        violations = []
        stats = {"tools_found": 0, "tools_required": 0}

        server_dir = os.path.join(project_root, config.get("server_dir", "stateweave/mcp_server"))
        required_tools = config.get("required_tool_names", [])
        stats["tools_required"] = len(required_tools)

        if not os.path.exists(server_dir):
            violations.append(
                Violation(
                    rule=self.name,
                    file=server_dir,
                    line=None,
                    message="MCP server directory not found",
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

        # Scan all Python files in server directory for tool function definitions
        found_tools = set()
        for fname in sorted(os.listdir(server_dir)):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue

            fpath = os.path.join(server_dir, fname)
            with open(fpath, "r") as f:
                source = f.read()

            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    found_tools.add(node.name)
                # Also check string literals (tool name registrations)
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    found_tools.add(node.value)

        stats["tools_found"] = len(found_tools & set(required_tools))

        for tool_name in required_tools:
            if tool_name not in found_tools:
                violations.append(
                    Violation(
                        rule=self.name,
                        file=os.path.relpath(server_dir, project_root),
                        line=None,
                        message=f"Required MCP tool '{tool_name}' not found in server implementation",
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
