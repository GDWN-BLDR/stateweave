"""
Migration Engine — Orchestrates full state migration pipeline.
===============================================================
Manages the complete flow: export → validate → encrypt → transport →
decrypt → validate → import. The central coordination point for
all StateWeave operations.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from stateweave.core.diff import StateDiff, diff_payloads
from stateweave.core.encryption import EncryptionError, EncryptionFacade
from stateweave.core.portability import PortabilityAnalyzer
from stateweave.core.serializer import SerializationError, StateWeaveSerializer
from stateweave.schema.v1 import (
    AuditAction,
    AuditEntry,
    EncryptionInfo,
    StateWeavePayload,
)
from stateweave.schema.validator import SchemaValidationError, validate_payload_strict

logger = logging.getLogger("stateweave.core.migration")


class MigrationError(Exception):
    """Raised when a migration operation fails."""

    pass


class MigrationResult:
    """Result of a migration operation."""

    def __init__(
        self,
        success: bool,
        payload: Optional[StateWeavePayload] = None,
        encrypted_data: Optional[bytes] = None,
        nonce: Optional[bytes] = None,
        warnings: Optional[List[Dict[str, Any]]] = None,
        error: Optional[str] = None,
        audit_trail: Optional[List[AuditEntry]] = None,
    ):
        self.success = success
        self.payload = payload
        self.encrypted_data = encrypted_data
        self.nonce = nonce
        self.warnings = warnings or []
        self.error = error
        self.audit_trail = audit_trail or []


class MigrationEngine:
    """Orchestrates complete state migration pipelines.

    The MigrationEngine is the high-level coordinator that combines
    serialization, validation, encryption, portability analysis,
    and adapter interactions into a coherent migration flow.

    Usage:
        engine = MigrationEngine()

        # Export from adapter
        result = engine.export_state(
            adapter=langgraph_adapter,
            agent_id="my-agent",
            encrypt_key=my_key,
        )

        # Import to another adapter
        result = engine.import_state(
            adapter=mcp_adapter,
            payload=result.payload,
        )
    """

    def __init__(
        self,
        serializer: Optional[StateWeaveSerializer] = None,
        encryption: Optional[EncryptionFacade] = None,
    ):
        """Initialize the migration engine.

        Args:
            serializer: Custom serializer instance. Uses default if None.
            encryption: Encryption facade instance. No encryption if None.
        """
        self._serializer = serializer or StateWeaveSerializer()
        self._encryption = encryption

    def export_state(
        self,
        adapter: Any,  # StateWeaveAdapter (avoiding circular import)
        agent_id: str,
        encrypt: bool = True,
        analyze_portability: bool = True,
        **kwargs,
    ) -> MigrationResult:
        """Export agent state through the full pipeline.

        Pipeline: adapter.export → validate → portability analysis → serialize → encrypt

        Args:
            adapter: The framework adapter to export from.
            agent_id: ID of the agent to export.
            encrypt: Whether to encrypt the payload.
            analyze_portability: Whether to run portability analysis.
            **kwargs: Additional arguments passed to the adapter.

        Returns:
            MigrationResult with the exported payload.
        """
        audit_trail = []
        timestamp = datetime.utcnow()

        try:
            # Step 1: Export from adapter
            logger.info(f"Exporting state from {adapter.framework_name}/{agent_id}")
            payload = adapter.export_state(agent_id, **kwargs)
            audit_trail.append(
                AuditEntry(
                    timestamp=timestamp,
                    action=AuditAction.EXPORT,
                    framework=adapter.framework_name,
                    success=True,
                    details={"agent_id": agent_id},
                )
            )

            # Step 2: Portability analysis
            if analyze_portability:
                analyzer = PortabilityAnalyzer(source_framework=adapter.framework_name)
                state_dict = payload.cognitive_state.model_dump()
                warnings = analyzer.analyze(state_dict)
                payload.non_portable_warnings.extend(warnings)
                logger.info(f"Portability analysis: {len(warnings)} warning(s)")

            # Step 3: Validate
            payload_dict = payload.model_dump(mode="json")
            validate_payload_strict(payload_dict)
            audit_trail.append(
                AuditEntry(
                    timestamp=datetime.utcnow(),
                    action=AuditAction.VALIDATE,
                    success=True,
                    details={"stage": "post_export"},
                )
            )

            # Step 4: Serialize
            raw_bytes = self._serializer.dumps(payload)

            # Step 5: Encrypt (if requested and facade available)
            encrypted_data = None
            nonce = None
            if encrypt and self._encryption:
                encrypted_data, nonce = self._encryption.encrypt(raw_bytes)
                payload.encryption = EncryptionInfo(
                    algorithm="AES-256-GCM",
                    key_id=self._encryption.key_id,
                    encrypted=True,
                )
                audit_trail.append(
                    AuditEntry(
                        timestamp=datetime.utcnow(),
                        action=AuditAction.ENCRYPT,
                        success=True,
                        details={"key_id": self._encryption.key_id},
                    )
                )

            payload.audit_trail.extend(audit_trail)

            return MigrationResult(
                success=True,
                payload=payload,
                encrypted_data=encrypted_data,
                nonce=nonce,
                warnings=[w.model_dump() for w in payload.non_portable_warnings],
                audit_trail=audit_trail,
            )

        except SchemaValidationError as e:
            logger.error(f"Schema validation failed: {e}")
            return MigrationResult(
                success=False,
                error=f"Schema validation failed: {e}",
                audit_trail=audit_trail,
            )
        except SerializationError as e:
            logger.error(f"Serialization failed: {e}")
            return MigrationResult(
                success=False,
                error=f"Serialization failed: {e}",
                audit_trail=audit_trail,
            )
        except EncryptionError as e:
            logger.error(f"Encryption failed: {e}")
            return MigrationResult(
                success=False,
                error=f"Encryption failed: {e}",
                audit_trail=audit_trail,
            )
        except Exception as e:
            logger.error(f"Export failed: {e}", exc_info=True)
            return MigrationResult(
                success=False,
                error=f"Export failed: {e}",
                audit_trail=audit_trail,
            )

    def import_state(
        self,
        adapter: Any,  # StateWeaveAdapter
        payload: Optional[StateWeavePayload] = None,
        encrypted_data: Optional[bytes] = None,
        nonce: Optional[bytes] = None,
        **kwargs,
    ) -> MigrationResult:
        """Import agent state through the full pipeline.

        Pipeline: decrypt → deserialize → validate → adapter.import

        Args:
            adapter: The framework adapter to import into.
            payload: Pre-deserialized payload. Mutually exclusive with encrypted_data.
            encrypted_data: Encrypted payload bytes.
            nonce: Encryption nonce (required with encrypted_data).
            **kwargs: Additional arguments passed to the adapter.

        Returns:
            MigrationResult with the imported state.
        """
        audit_trail = []

        try:
            # Step 1: Decrypt if needed
            if encrypted_data is not None:
                if not self._encryption:
                    raise MigrationError(
                        "Encrypted data provided but no encryption facade configured"
                    )
                if nonce is None:
                    raise MigrationError("Nonce required for decryption")

                raw_bytes = self._encryption.decrypt(encrypted_data, nonce)
                audit_trail.append(
                    AuditEntry(
                        timestamp=datetime.utcnow(),
                        action=AuditAction.DECRYPT,
                        success=True,
                    )
                )

                # Step 2: Deserialize
                payload = self._serializer.loads(raw_bytes)

            if payload is None:
                raise MigrationError("No payload or encrypted data provided")

            # Step 3: Validate
            payload_dict = payload.model_dump(mode="json")
            validate_payload_strict(payload_dict)
            audit_trail.append(
                AuditEntry(
                    timestamp=datetime.utcnow(),
                    action=AuditAction.VALIDATE,
                    success=True,
                    details={"stage": "pre_import"},
                )
            )

            # Step 4: Import via adapter
            logger.info(
                f"Importing state into {adapter.framework_name} (from {payload.source_framework})"
            )
            adapter.import_state(payload, **kwargs)
            audit_trail.append(
                AuditEntry(
                    timestamp=datetime.utcnow(),
                    action=AuditAction.IMPORT,
                    framework=adapter.framework_name,
                    success=True,
                    details={
                        "source_framework": payload.source_framework,
                        "agent_id": payload.metadata.agent_id,
                    },
                )
            )

            payload.audit_trail.extend(audit_trail)

            return MigrationResult(
                success=True,
                payload=payload,
                warnings=[w.model_dump() for w in payload.non_portable_warnings],
                audit_trail=audit_trail,
            )

        except (SchemaValidationError, SerializationError, EncryptionError, MigrationError) as e:
            logger.error(f"Import failed: {e}")
            return MigrationResult(
                success=False,
                error=str(e),
                audit_trail=audit_trail,
            )
        except Exception as e:
            logger.error(f"Import failed unexpectedly: {e}", exc_info=True)
            return MigrationResult(
                success=False,
                error=f"Import failed: {e}",
                audit_trail=audit_trail,
            )

    def diff_states(
        self,
        state_a: StateWeavePayload,
        state_b: StateWeavePayload,
    ) -> StateDiff:
        """Compute the diff between two states.

        Args:
            state_a: The "before" state.
            state_b: The "after" state.

        Returns:
            StateDiff with all differences enumerated.
        """
        return diff_payloads(state_a, state_b)
