# Building an Adapter

Add support for any agent framework by subclassing `StateWeaveAdapter`.

## The ABC

```python
from stateweave.adapters.base import StateWeaveAdapter, AdapterTier
from stateweave.schema.v1 import StateWeavePayload, AgentInfo

class MyFrameworkAdapter(StateWeaveAdapter):
    @property
    def framework_name(self) -> str:
        return "my-framework"

    @property
    def tier(self) -> AdapterTier:
        return AdapterTier.COMMUNITY

    def export_state(self, agent_id: str, **kwargs) -> StateWeavePayload:
        # Read your framework's state and map to Universal Schema
        ...

    def import_state(self, payload: StateWeavePayload, **kwargs):
        # Read Universal Schema and write to your framework's state
        ...

    def list_agents(self) -> list[AgentInfo]:
        # Return discoverable agents
        ...
```

## Scaffold Generator

Generate adapter boilerplate automatically:

```bash
stateweave generate-adapter my-framework --output-dir ./adapters
```

This creates a complete adapter file with all required methods stubbed out.

## Key Principles

1. **Map to Universal Schema fields** — `conversation_history`, `working_memory`, `goal_tree`, etc.
2. **Add `non_portable_warnings`** — be honest about what can't transfer.
3. **Include audit entries** — log export/import operations.
4. **The UCE `adapter_contract` scanner** verifies your adapter implements the full ABC.

## Testing

Write tests that verify roundtrip fidelity:

```python
def test_roundtrip():
    adapter = MyFrameworkAdapter()
    adapter.setup_some_state("agent-1", state_data)

    payload = adapter.export_state("agent-1")
    adapter2 = MyFrameworkAdapter()
    adapter2.import_state(payload)

    payload2 = adapter2.export_state("agent-1")
    assert payload.cognitive_state == payload2.cognitive_state
```
