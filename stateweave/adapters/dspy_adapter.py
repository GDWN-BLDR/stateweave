"""
DSPy Adapter — Translates DSPy module state ↔ Universal Schema.
=================================================================
Maps DSPy's internal state (signatures, demos, LM configurations)
to the StateWeave Universal Schema for cross-framework portability.

DSPy stores state as:
  - Signatures (input/output field definitions)
  - Demos (few-shot examples used for in-context learning)
  - LM configurations (model, temperature, etc.)
  - Module metadata (traces, train examples)
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from stateweave.adapters.base import AdapterTier, ExportError, ImportError_, StateWeaveAdapter
from stateweave.schema.v1 import (
    AccessPolicy,
    AgentInfo,
    AgentMetadata,
    AuditAction,
    AuditEntry,
    CognitiveState,
    Message,
    MessageRole,
    NonPortableWarning,
    NonPortableWarningSeverity,
    StateWeavePayload,
    ToolResult,
)

logger = logging.getLogger("stateweave.adapters.dspy")

DSPY_TARGET_VERSION = "2.6.x"

# DSPy state keys that are internal/non-portable
DSPY_INTERNAL_KEYS = {
    "__class__",
    "__version__",
    "_compiled",
    "_compiled_with",
    "_lm_client_ref",
}


class DSPyAdapter(StateWeaveAdapter):
    """Adapter for DSPy (dspy>=2.6.0).

    Translates between DSPy's module state representation (signatures,
    demos, LM configs, traces) and the StateWeave Universal Schema.

    DSPy modules save state via module.save() which produces a JSON dict
    containing signatures, demos, LM configurations, and metadata. This
    adapter reads that JSON state and maps it to CognitiveState fields.

    Usage:
        adapter = DSPyAdapter(module=my_dspy_module)
        payload = adapter.export_state("my-module")
    """

    def __init__(
        self,
        module: Optional[Any] = None,
        state_path: Optional[str] = None,
    ):
        """Initialize the DSPy adapter.

        Args:
            module: A DSPy module instance (dspy.Module subclass).
            state_path: Path to a saved DSPy state JSON file.
        """
        self._module = module
        self._state_path = state_path
        self._agents: Dict[str, Dict[str, Any]] = {}

    @property
    def framework_name(self) -> str:
        return "dspy"

    @property
    def tier(self) -> AdapterTier:
        return AdapterTier.TIER_2

    def export_state(
        self,
        agent_id: str,
        **kwargs,
    ) -> StateWeavePayload:
        """Export DSPy module state to Universal Schema.

        Args:
            agent_id: Identifier for this module/program.
            **kwargs: Additional options:
                - include_demos: bool (default True) — include few-shot demos
                - include_traces: bool (default True) — include execution traces

        Returns:
            StateWeavePayload with the module's cognitive state.
        """
        include_demos = kwargs.get("include_demos", True)
        include_traces = kwargs.get("include_traces", True)

        try:
            state = self._get_module_state(agent_id)
        except Exception as e:
            raise ExportError(f"Failed to get DSPy state for '{agent_id}': {e}") from e

        cognitive_state = self._translate_to_cognitive_state(state, include_demos, include_traces)

        warnings = self._detect_non_portable(state)

        metadata = AgentMetadata(
            agent_id=agent_id,
            agent_name=kwargs.get("agent_name", f"dspy-{agent_id}"),
            namespace=kwargs.get("namespace", "default"),
            tags=kwargs.get("tags", ["dspy"]),
            access_policy=AccessPolicy.PRIVATE,
            framework_capabilities={
                "module_type": type(self._module).__name__ if self._module else "unknown",
                "has_compiled": state.get("_compiled", False),
            },
        )

        audit_trail = [
            AuditEntry(
                timestamp=datetime.utcnow(),
                action=AuditAction.EXPORT,
                framework="dspy",
                success=True,
                details={
                    "module_id": agent_id,
                    "state_keys": list(state.keys()),
                    "num_demos": len(state.get("demos", [])),
                },
            )
        ]

        return StateWeavePayload(
            source_framework="dspy",
            source_version=DSPY_TARGET_VERSION,
            exported_at=datetime.utcnow(),
            cognitive_state=cognitive_state,
            metadata=metadata,
            audit_trail=audit_trail,
            non_portable_warnings=warnings,
        )

    def import_state(
        self,
        payload: StateWeavePayload,
        **kwargs,
    ) -> Any:
        """Import a StateWeavePayload into DSPy module state.

        Args:
            payload: The Universal Schema payload to import.
            **kwargs: Additional options:
                - module_id: str — target module identifier

        Returns:
            Dict with module_id and restored state info.
        """
        module_id = kwargs.get("module_id", payload.metadata.agent_id)

        try:
            state_dict = self._translate_from_cognitive_state(payload.cognitive_state)

            if self._module and hasattr(self._module, "load_state"):
                self._module.load_state(state_dict)
            else:
                self._agents[module_id] = state_dict

            logger.info(
                f"Imported state into DSPy module '{module_id}' (from {payload.source_framework})"
            )

            return {
                "module_id": module_id,
                "framework": "dspy",
                "state_keys": list(state_dict.keys()),
                "import_source": payload.source_framework,
            }

        except Exception as e:
            raise ImportError_(f"Failed to import state into DSPy module '{module_id}': {e}") from e

    def list_agents(self) -> List[AgentInfo]:
        """List all known DSPy modules."""
        agents = []

        if self._module:
            agents.append(
                AgentInfo(
                    agent_id="default",
                    agent_name=f"dspy-{type(self._module).__name__}",
                    framework="dspy",
                    metadata={"source": "live_module"},
                )
            )

        for module_id, state in self._agents.items():
            agents.append(
                AgentInfo(
                    agent_id=module_id,
                    agent_name=f"dspy-{module_id}",
                    framework="dspy",
                    metadata={"source": "local_store"},
                )
            )

        return agents

    def _get_module_state(self, agent_id: str = "") -> Dict[str, Any]:
        """Extract state from DSPy module, file, or local store."""
        if self._module:
            if hasattr(self._module, "save"):
                # DSPy >=2.6: module.save() returns state dict
                import os
                import tempfile

                tmp = tempfile.mktemp(suffix=".json")
                try:
                    self._module.save(tmp, save_program=False)
                    with open(tmp) as f:
                        return json.load(f)
                finally:
                    if os.path.exists(tmp):
                        os.remove(tmp)
            elif hasattr(self._module, "dump_state"):
                return self._module.dump_state()
        elif self._state_path:
            with open(self._state_path) as f:
                return json.load(f)
        elif agent_id and agent_id in self._agents:
            return self._agents[agent_id]

        return {}

    def _translate_to_cognitive_state(
        self,
        state: Dict[str, Any],
        include_demos: bool = True,
        include_traces: bool = True,
    ) -> CognitiveState:
        """Translate DSPy module state to Universal Schema CognitiveState."""
        messages = []
        working_memory: Dict[str, Any] = {}
        tool_results: Dict[str, ToolResult] = {}

        # Extract demos as conversation history
        if include_demos and "demos" in state:
            for i, demo in enumerate(state["demos"]):
                if isinstance(demo, dict):
                    # Each demo is typically an input-output pair
                    content_parts = []
                    for k, v in demo.items():
                        content_parts.append(f"{k}: {v}")
                    messages.append(
                        Message(
                            role=MessageRole.HUMAN,
                            content="\n".join(content_parts),
                            metadata={"demo_index": i, "source": "dspy_demo"},
                        )
                    )

        # Extract signatures into working memory
        if "signature" in state:
            working_memory["dspy_signature"] = state["signature"]

        # Extract LM configuration
        if "lm" in state:
            working_memory["dspy_lm_config"] = state["lm"]

        # Extract traces as tool results
        if include_traces and "traces" in state:
            for i, trace in enumerate(state["traces"]):
                if isinstance(trace, dict):
                    tool_results[f"trace_{i}"] = ToolResult(
                        tool_name="dspy_trace",
                        arguments=trace.get("inputs", {}),
                        result=trace.get("outputs", {}),
                        success=True,
                    )

        # Extract train examples into episodic memory
        episodic_memory = []
        if "train" in state:
            for example in state["train"]:
                if isinstance(example, dict):
                    episodic_memory.append(example)

        # Remaining metadata into working memory
        for key in ("metadata", "config"):
            if key in state and isinstance(state[key], dict):
                working_memory[f"dspy_{key}"] = state[key]

        return CognitiveState(
            conversation_history=messages,
            working_memory=working_memory,
            tool_results_cache=tool_results,
            episodic_memory=episodic_memory,
        )

    def _translate_from_cognitive_state(
        self,
        cognitive_state: CognitiveState,
    ) -> Dict[str, Any]:
        """Translate Universal Schema CognitiveState to DSPy state dict."""
        state: Dict[str, Any] = {}

        # Restore demos from conversation history
        demos = []
        for msg in cognitive_state.conversation_history:
            if msg.metadata.get("source") == "dspy_demo":
                demo = {}
                for line in msg.content.split("\n"):
                    if ": " in line:
                        k, v = line.split(": ", 1)
                        demo[k] = v
                demos.append(demo)
        if demos:
            state["demos"] = demos

        # Restore signature from working memory
        if "dspy_signature" in cognitive_state.working_memory:
            state["signature"] = cognitive_state.working_memory["dspy_signature"]

        # Restore LM config
        if "dspy_lm_config" in cognitive_state.working_memory:
            state["lm"] = cognitive_state.working_memory["dspy_lm_config"]

        # Restore traces from tool results
        traces = []
        for key, result in cognitive_state.tool_results_cache.items():
            if isinstance(result, ToolResult) and result.tool_name == "dspy_trace":
                traces.append(
                    {
                        "inputs": result.arguments,
                        "outputs": result.result,
                    }
                )
        if traces:
            state["traces"] = traces

        # Restore train examples from episodic memory
        if cognitive_state.episodic_memory:
            state["train"] = cognitive_state.episodic_memory

        # Restore metadata
        if "dspy_metadata" in cognitive_state.working_memory:
            state["metadata"] = cognitive_state.working_memory["dspy_metadata"]
        if "dspy_config" in cognitive_state.working_memory:
            state["config"] = cognitive_state.working_memory["dspy_config"]

        return state

    def _detect_non_portable(
        self,
        state: Dict[str, Any],
    ) -> List[NonPortableWarning]:
        """Detect DSPy-specific non-portable elements."""
        warnings = []

        # LM client references are non-portable
        if "_lm_client_ref" in state or "lm" in state:
            lm_config = state.get("lm", {})
            if isinstance(lm_config, dict) and lm_config.get("api_key"):
                warnings.append(
                    NonPortableWarning(
                        field="lm.api_key",
                        reason="API key is framework-specific and will be stripped",
                        severity=NonPortableWarningSeverity.CRITICAL,
                        data_loss=False,
                        recommendation=(
                            "Reconfigure LM credentials after import using "
                            "the target framework's auth mechanism"
                        ),
                    )
                )

        # Compiled optimizers are DSPy-specific
        if state.get("_compiled"):
            warnings.append(
                NonPortableWarning(
                    field="_compiled",
                    reason=("DSPy compilation state (optimizer artifacts) is framework-specific"),
                    severity=NonPortableWarningSeverity.WARN,
                    data_loss=True,
                    recommendation=(
                        "Re-compile the module after import using the target "
                        "framework's optimization tools"
                    ),
                )
            )

        for key in state:
            if key in DSPY_INTERNAL_KEYS:
                warnings.append(
                    NonPortableWarning(
                        field=f"state.{key}",
                        reason=f"DSPy internal field '{key}' is framework-specific",
                        severity=NonPortableWarningSeverity.INFO,
                        data_loss=False,
                        recommendation="This field will be stripped during export",
                    )
                )

        return warnings
