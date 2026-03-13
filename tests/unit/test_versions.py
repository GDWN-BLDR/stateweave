"""
Unit Tests: Schema Versions
==============================
Tests for version registry and migration.
"""

import pytest

from stateweave.schema.versions import (
    CURRENT_VERSION,
    get_current_version,
    get_supported_versions,
    is_version_supported,
    migrate_payload,
)


class TestVersions:
    def test_current_version(self):
        assert get_current_version() == CURRENT_VERSION

    def test_supported_versions(self):
        versions = get_supported_versions()
        assert "0.1.0" in versions

    def test_unsupported_version(self):
        assert is_version_supported("99.0.0") is False

    def test_migrate_same_version(self):
        payload = {"stateweave_version": "0.1.0", "data": "test"}
        result = migrate_payload(payload, target_version="0.1.0")
        assert result["data"] == "test"

    def test_migrate_no_path(self):
        with pytest.raises(ValueError, match="No migration path"):
            migrate_payload(
                {"stateweave_version": "0.1.0"},
                target_version="99.0.0",
            )
