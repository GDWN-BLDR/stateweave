# stateweave.adapters — Framework adapters
"""
Framework adapters for StateWeave. Each adapter translates between
a framework's native state representation and the Universal Schema.
"""

from stateweave.adapters.autogen_adapter import AutoGenAdapter
from stateweave.adapters.base import AdapterTier, StateWeaveAdapter
from stateweave.adapters.crewai_adapter import CrewAIAdapter
from stateweave.adapters.dspy_adapter import DSPyAdapter
from stateweave.adapters.haystack_adapter import HaystackAdapter
from stateweave.adapters.langgraph_adapter import LangGraphAdapter
from stateweave.adapters.letta_adapter import LettaAdapter
from stateweave.adapters.llamaindex_adapter import LlamaIndexAdapter
from stateweave.adapters.mcp_adapter import MCPAdapter
from stateweave.adapters.openai_agents_adapter import OpenAIAgentsAdapter
from stateweave.adapters.semantic_kernel_adapter import SemanticKernelAdapter

__all__ = [
    "AdapterTier",
    "StateWeaveAdapter",
    "LangGraphAdapter",
    "MCPAdapter",
    "CrewAIAdapter",
    "AutoGenAdapter",
    "DSPyAdapter",
    "LlamaIndexAdapter",
    "OpenAIAgentsAdapter",
    "HaystackAdapter",
    "LettaAdapter",
    "SemanticKernelAdapter",
]

# Adapter registry for auto-detection and CLI
ADAPTER_REGISTRY = {
    "langgraph": LangGraphAdapter,
    "mcp": MCPAdapter,
    "crewai": CrewAIAdapter,
    "autogen": AutoGenAdapter,
    "dspy": DSPyAdapter,
    "llamaindex": LlamaIndexAdapter,
    "openai_agents": OpenAIAgentsAdapter,
    "haystack": HaystackAdapter,
    "letta": LettaAdapter,
    "semantic_kernel": SemanticKernelAdapter,
}
