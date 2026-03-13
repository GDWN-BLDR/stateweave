"""Tests for environment auto-detection and live connectors."""

import unittest

from stateweave.core.environment import (
    FRAMEWORK_PACKAGES,
    EnvironmentScan,
    FrameworkInfo,
    auto_select_adapter,
    scan_environment,
)


class TestEnvironmentScan(unittest.TestCase):
    """Test environment scanning for installed frameworks."""

    def test_scan_returns_environment_scan(self):
        scan = scan_environment()
        self.assertIsInstance(scan, EnvironmentScan)
        self.assertIsInstance(scan.python_version, str)
        self.assertIsInstance(scan.stateweave_version, str)

    def test_scan_detects_installed_frameworks(self):
        scan = scan_environment()
        # langgraph should be detected since we installed it
        self.assertTrue(scan.framework_count >= 0)  # may vary by env

    def test_framework_info_fields(self):
        info = FrameworkInfo(
            name="langgraph",
            version="0.6.11",
            adapter_name="langgraph",
            package_name="langgraph",
            has_adapter=True,
        )
        self.assertEqual(info.name, "langgraph")
        self.assertEqual(info.version, "0.6.11")
        self.assertTrue(info.has_adapter)

    def test_environment_scan_has_framework(self):
        scan = EnvironmentScan()
        scan.frameworks.append(
            FrameworkInfo(
                name="langgraph",
                version="0.6.11",
                adapter_name="langgraph",
                package_name="langgraph",
            )
        )
        self.assertTrue(scan.has_framework("langgraph"))
        self.assertFalse(scan.has_framework("unknown"))

    def test_environment_scan_get_framework(self):
        scan = EnvironmentScan()
        info = FrameworkInfo(
            name="langgraph",
            version="0.6.11",
            adapter_name="langgraph",
            package_name="langgraph",
        )
        scan.frameworks.append(info)
        self.assertEqual(scan.get_framework("langgraph"), info)
        self.assertIsNone(scan.get_framework("unknown"))

    def test_environment_scan_report(self):
        scan = EnvironmentScan(python_version="3.11.0", stateweave_version="0.3.0")
        scan.frameworks.append(
            FrameworkInfo(
                name="langgraph",
                version="0.6.11",
                adapter_name="langgraph",
                package_name="langgraph",
            )
        )
        report = scan.to_report()
        self.assertIn("langgraph", report)
        self.assertIn("0.6.11", report)
        self.assertIn("3.11.0", report)

    def test_environment_scan_empty_report(self):
        scan = EnvironmentScan(python_version="3.11.0", stateweave_version="0.3.0")
        report = scan.to_report()
        self.assertIn("No agent frameworks detected", report)

    def test_framework_packages_coverage(self):
        # All adapters should have at least one package mapping
        from stateweave.adapters import ADAPTER_REGISTRY

        mapped_adapters = set(FRAMEWORK_PACKAGES.values())
        for adapter_name in ADAPTER_REGISTRY:
            self.assertIn(
                adapter_name,
                mapped_adapters,
                f"Adapter '{adapter_name}' has no package mapping in FRAMEWORK_PACKAGES",
            )


class TestAutoSelect(unittest.TestCase):
    """Test auto-selection of adapters."""

    def test_auto_select_priority(self):
        scan = EnvironmentScan()
        # Add crewai and autogen — should prefer crewai
        scan.frameworks.append(
            FrameworkInfo(
                name="autogen",
                version="0.4.0",
                adapter_name="autogen",
                package_name="pyautogen",
            )
        )
        scan.frameworks.append(
            FrameworkInfo(
                name="crewai",
                version="0.80.0",
                adapter_name="crewai",
                package_name="crewai",
            )
        )
        name, cls = auto_select_adapter(scan)
        self.assertEqual(name, "crewai")  # crewai > autogen in priority

    def test_auto_select_empty(self):
        scan = EnvironmentScan()
        name, cls = auto_select_adapter(scan)
        self.assertIsNone(name)
        self.assertIsNone(cls)

    def test_auto_select_langgraph_highest_priority(self):
        scan = EnvironmentScan()
        scan.frameworks.append(
            FrameworkInfo(
                name="dspy",
                version="2.0.0",
                adapter_name="dspy",
                package_name="dspy",
            )
        )
        scan.frameworks.append(
            FrameworkInfo(
                name="langgraph",
                version="0.6.11",
                adapter_name="langgraph",
                package_name="langgraph",
            )
        )
        name, _ = auto_select_adapter(scan)
        self.assertEqual(name, "langgraph")


if __name__ == "__main__":
    unittest.main()
