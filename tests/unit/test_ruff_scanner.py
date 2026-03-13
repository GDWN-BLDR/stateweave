"""Tests for the Ruff Quality UCE Scanner."""

import os
import tempfile
import unittest

from stateweave.compliance.scanner_base import Mode
from stateweave.compliance.scanners.ruff_quality import RuffQualityScanner


class TestRuffQualityScanner(unittest.TestCase):
    """Test suite for RuffQualityScanner."""

    def setUp(self):
        self.scanner = RuffQualityScanner()
        self.project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

    def test_scanner_name(self):
        self.assertEqual(self.scanner.name, "ruff_quality")

    def test_clean_codebase_passes(self):
        """The current codebase should pass ruff checks."""
        config = {
            "mode": "BLOCK",
            "scan_paths": ["stateweave/", "tests/"],
        }
        result = self.scanner.scan(config, self.project_root)
        self.assertTrue(
            result.passed,
            f"Ruff scanner failed with {len(result.violations)} violations: "
            + "; ".join(v.message for v in result.violations[:5]),
        )
        self.assertEqual(result.scanner_name, "ruff_quality")
        self.assertEqual(result.mode, Mode.BLOCK)

    def test_detects_lint_violations(self):
        """Scanner should detect ruff lint violations in dirty code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with an unused import (F401)
            dirty_file = os.path.join(tmpdir, "dirty.py")
            with open(dirty_file, "w") as f:
                f.write("import os\nimport sys\n\nprint('hello')\n")

            config = {
                "mode": "BLOCK",
                "scan_paths": [tmpdir],
            }
            # Use tmpdir as both scan path and project root
            result = self.scanner.scan(config, tmpdir)

            # Should detect unused import for 'os'
            self.assertFalse(result.passed)
            self.assertGreater(result.stats["lint_errors"], 0)

    def test_detects_format_violations(self):
        """Scanner should detect ruff format violations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with bad formatting (inconsistent quotes, bad spacing)
            dirty_file = os.path.join(tmpdir, "ugly.py")
            with open(dirty_file, "w") as f:
                f.write(
                    "def foo(a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z):\n"
                    "    return     {  'a' :a,'b':b,   'c':c,\n"
                    "'d':d,'e':e  ,'f':f  ,'g'   :g ,'h':h}\n"
                )

            config = {
                "mode": "BLOCK",
                "scan_paths": [tmpdir],
            }
            result = self.scanner.scan(config, tmpdir)

            # Should detect formatting issue
            self.assertFalse(result.passed)
            self.assertGreater(result.stats["format_errors"], 0)

    def test_parse_ruff_line(self):
        """Test parsing of ruff concise output format."""
        line = "stateweave/foo.py:42:1: F401 `os` imported but unused"
        parsed = RuffQualityScanner._parse_ruff_line(line, "/project")
        self.assertIsNotNone(parsed)
        file_path, line_num, message = parsed
        self.assertEqual(line_num, 42)
        self.assertIn("F401", message)

    def test_parse_ruff_line_invalid(self):
        """Test parsing of invalid ruff output returns None."""
        self.assertIsNone(RuffQualityScanner._parse_ruff_line("not a ruff line", "/project"))

    def test_warn_mode(self):
        """Scanner should respect WARN mode configuration."""
        config = {
            "mode": "WARN",
            "scan_paths": ["stateweave/", "tests/"],
        }
        result = self.scanner.scan(config, self.project_root)
        self.assertEqual(result.mode, Mode.WARN)


if __name__ == "__main__":
    unittest.main()
