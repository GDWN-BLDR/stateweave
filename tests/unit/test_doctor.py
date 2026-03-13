"""Tests for stateweave doctor — diagnostic health checks."""

import unittest

from stateweave.core.doctor import (
    DiagnosticCheck,
    DoctorReport,
    run_doctor,
)


class TestDiagnosticCheck(unittest.TestCase):
    """Test individual diagnostic check data."""

    def test_ok_icon(self):
        check = DiagnosticCheck(name="test", status="ok", message="All good")
        self.assertEqual(check.icon, "✓")

    def test_warn_icon(self):
        check = DiagnosticCheck(name="test", status="warn", message="Watch out")
        self.assertEqual(check.icon, "⚠")

    def test_error_icon(self):
        check = DiagnosticCheck(name="test", status="error", message="Broken")
        self.assertEqual(check.icon, "✗")


class TestDoctorReport(unittest.TestCase):
    """Test the doctor report."""

    def test_healthy_report(self):
        report = DoctorReport(checks=[
            DiagnosticCheck(name="a", status="ok", message="Good"),
            DiagnosticCheck(name="b", status="ok", message="Also good"),
        ])
        self.assertTrue(report.healthy)
        self.assertEqual(report.ok_count, 2)
        self.assertEqual(report.error_count, 0)

    def test_unhealthy_report(self):
        report = DoctorReport(checks=[
            DiagnosticCheck(name="a", status="ok", message="Good"),
            DiagnosticCheck(name="b", status="error", message="Bad"),
        ])
        self.assertFalse(report.healthy)
        self.assertEqual(report.error_count, 1)

    def test_format_output(self):
        report = DoctorReport(checks=[
            DiagnosticCheck(name="a", status="ok", message="Python 3.11"),
            DiagnosticCheck(name="b", status="warn", message="No frameworks",
                          suggestion="pip install langgraph"),
        ])
        output = report.format()
        self.assertIn("StateWeave Doctor", output)
        self.assertIn("Python 3.11", output)
        self.assertIn("pip install langgraph", output)
        self.assertIn("1 warnings", output)


class TestRunDoctor(unittest.TestCase):
    """Test the full doctor run."""

    def test_run_doctor_returns_report(self):
        report = run_doctor()
        self.assertIsInstance(report, DoctorReport)
        self.assertTrue(len(report.checks) > 0)

    def test_doctor_checks_python(self):
        report = run_doctor()
        python_checks = [c for c in report.checks if c.name == "python"]
        self.assertEqual(len(python_checks), 1)
        self.assertEqual(python_checks[0].status, "ok")

    def test_doctor_checks_stateweave(self):
        report = run_doctor()
        sw_checks = [c for c in report.checks if c.name == "stateweave"]
        self.assertEqual(len(sw_checks), 1)
        self.assertEqual(sw_checks[0].status, "ok")

    def test_doctor_checks_encryption(self):
        report = run_doctor()
        enc_checks = [c for c in report.checks if c.name == "encryption"]
        self.assertEqual(len(enc_checks), 1)
        # Either ok (cryptography installed) or warn (not installed)
        self.assertIn(enc_checks[0].status, ["ok", "warn"])

    def test_doctor_checks_serialization(self):
        report = run_doctor()
        ser_checks = [c for c in report.checks if c.name == "serialization"]
        self.assertEqual(len(ser_checks), 1)
        self.assertEqual(ser_checks[0].status, "ok")

    def test_doctor_format_contains_verdict(self):
        report = run_doctor()
        output = report.format()
        self.assertTrue("healthy" in output or "needs attention" in output)


if __name__ == "__main__":
    unittest.main()
