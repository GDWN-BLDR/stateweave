# Adapters

All adapters extend `StateWeaveAdapter` and implement 4 methods.

## Adapter Registry

```python
from stateweave.adapters import ADAPTER_REGISTRY

for name, adapter_cls in ADAPTER_REGISTRY.items():
    instance = adapter_cls()
    print(f"{name}: {instance.tier.value}")
```

## Available Adapters

| Adapter | Class | Tier |
|---------|-------|------|
| LangGraph | `LangGraphAdapter` | 🟢 Tier 1 |
| MCP | `MCPAdapter` | 🟢 Tier 1 |
| CrewAI | `CrewAIAdapter` | 🟢 Tier 1 |
| AutoGen | `AutoGenAdapter` | 🟢 Tier 1 |
| DSPy | `DSPyAdapter` | 🟡 Tier 2 |
| OpenAI Agents | `OpenAIAgentsAdapter` | 🟡 Tier 2 |
| LlamaIndex | `LlamaIndexAdapter` | 🔵 Community |
| Haystack | `HaystackAdapter` | 🔵 Community |
| Letta | `LettaAdapter` | 🔵 Community |
| Semantic Kernel | `SemanticKernelAdapter` | 🔵 Community |

## StateWeaveAdapter ABC

```python
class StateWeaveAdapter(ABC):
    @property
    @abstractmethod
    def framework_name(self) -> str: ...

    @property
    @abstractmethod
    def tier(self) -> AdapterTier: ...

    @abstractmethod
    def export_state(self, agent_id: str, **kwargs) -> StateWeavePayload: ...

    @abstractmethod
    def import_state(self, payload: StateWeavePayload, **kwargs): ...

    @abstractmethod
    def list_agents(self) -> list[AgentInfo]: ...
```

## AdapterTier Enum

```python
class AdapterTier(str, Enum):
    TIER_1 = "tier_1"       # Core team, guaranteed stability
    TIER_2 = "tier_2"       # Actively maintained
    COMMUNITY = "community" # Best-effort
```
