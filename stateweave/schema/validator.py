"""
Schema Validator — JSON Schema validation utilities.
=====================================================
Validates StateWeavePayload instances against the canonical schema.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from stateweave.schema.v1 import SCHEMA_VERSION, StateWeavePayload

logger = logging.getLogger("stateweave.schema.validator")


class SchemaValidationError(Exception):
    """Raised when a payload fails schema validation."""

    def __init__(self, errors: List[Dict[str, Any]], message: str = "Schema validation failed"):
        self.errors = errors
        super().__init__(f"{message}: {len(errors)} error(s)")


def validate_payload(data: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
    """Validate a raw dictionary against the StateWeavePayload schema.

    Args:
        data: Raw dictionary to validate.

    Returns:
        Tuple of (is_valid, errors). errors is empty list if valid.
    """
    try:
        StateWeavePayload(**data)
        return True, []
    except ValidationError as e:
        errors = []
        for error in e.errors():
            errors.append(
                {
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                }
            )
        return False, errors


def validate_payload_strict(data: Dict[str, Any]) -> StateWeavePayload:
    """Validate and return a StateWeavePayload or raise SchemaValidationError.

    Args:
        data: Raw dictionary to validate.

    Returns:
        Validated StateWeavePayload instance.

    Raises:
        SchemaValidationError: If validation fails.
    """
    is_valid, errors = validate_payload(data)
    if not is_valid:
        raise SchemaValidationError(errors)
    return StateWeavePayload(**data)


def validate_version_compatibility(
    payload_version: str,
    supported_versions: Optional[List[str]] = None,
) -> bool:
    """Check if a payload version is compatible with the current schema.

    Args:
        payload_version: The version string from the payload.
        supported_versions: List of supported versions. Defaults to [SCHEMA_VERSION].

    Returns:
        True if compatible, False otherwise.
    """
    if supported_versions is None:
        supported_versions = [SCHEMA_VERSION]

    # Extract major.minor for compatibility check
    try:
        payload_major, payload_minor, _ = payload_version.split(".")
        for supported in supported_versions:
            sup_major, sup_minor, _ = supported.split(".")
            # Same major version = backward compatible
            if payload_major == sup_major:
                return True
    except (ValueError, AttributeError):
        logger.error(f"Invalid version format: {payload_version}")
        return False

    return False


def get_schema_json() -> Dict[str, Any]:
    """Get the JSON Schema representation of StateWeavePayload.

    Returns:
        JSON Schema dictionary.
    """
    return StateWeavePayload.model_json_schema()
