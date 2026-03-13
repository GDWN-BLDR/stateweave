# stateweave.core — Core engine components
"""
Core engine for StateWeave: serialization, encryption, diffing,
migration, and portability analysis.
"""

from stateweave.core.diff import StateDiff, diff_payloads
from stateweave.core.encryption import EncryptionFacade
from stateweave.core.migration import MigrationEngine
from stateweave.core.portability import PortabilityAnalyzer
from stateweave.core.serializer import StateWeaveSerializer

__all__ = [
    "StateWeaveSerializer",
    "EncryptionFacade",
    "MigrationEngine",
    "diff_payloads",
    "StateDiff",
    "PortabilityAnalyzer",
]
