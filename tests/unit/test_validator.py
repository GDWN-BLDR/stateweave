"""
Unit Tests: Schema Validator
===============================
Tests for validation utilities.
"""

import pytest

from stateweave.schema.validator import (
    SchemaValidationError,
    get_schema_json,
    validate_payload,
    validate_payload_strict,
    validate_version_compatibility,
)


class TestValidator:
    def test_valid_minimal(self):
        is_valid, errors = validate_payload(
            {
                "source_framework": "test",
                "metadata": {"agent_id": "a1"},
            }
        )
        assert is_valid

    def test_invalid_missing_fields(self):
        is_valid, errors = validate_payload({})
        assert not is_valid
        assert len(errors) > 0

    def test_strict_raises(self):
        with pytest.raises(SchemaValidationError):
            validate_payload_strict({})

    def test_version_compat_same_major(self):
        assert validate_version_compatibility("0.2.0") is True

    def test_version_compat_diff_major(self):
        assert validate_version_compatibility("1.0.0") is False

    def test_json_schema(self):
        schema = get_schema_json()
        assert "properties" in schema
        assert "title" in schema
