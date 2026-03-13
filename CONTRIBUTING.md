# Contributing to StateWeave

Thank you for your interest in contributing to StateWeave! This document provides guidelines and instructions for contributing.

## Development Setup

```bash
git clone https://github.com/GDWN-BLDR/stateweave.git
cd stateweave
pip install -e ".[dev]"
```

## Running Tests

```bash
# Full test suite
pytest tests/ -v

# Run UCE compliance scan
python scripts/uce.py

# Lint
ruff check stateweave/ tests/
```

## Building a New Framework Adapter

The highest-impact way to contribute is building an adapter for a new framework. Here's how:

### 1. Create the Adapter

Create `stateweave/adapters/your_framework_adapter.py`:

```python
from stateweave.adapters.base import StateWeaveAdapter
from stateweave.schema.v1 import StateWeavePayload, AgentInfo

class YourFrameworkAdapter(StateWeaveAdapter):
    @property
    def framework_name(self) -> str:
        return "your-framework"

    def export_state(self, agent_id: str, **kwargs) -> StateWeavePayload:
        # Translate your framework's state → Universal Schema
        ...

    def import_state(self, payload: StateWeavePayload, **kwargs):
        # Translate Universal Schema → your framework's state
        ...

    def list_agents(self) -> list[AgentInfo]:
        ...
```

### 2. Key Rules

- **All state goes through the Universal Schema** — never translate directly between frameworks
- **Detect non-portable elements** — DB cursors, callbacks, live connections, credentials
- **Populate `non_portable_warnings[]`** — no silent data loss
- **Use `logging.getLogger("stateweave.adapters.your_framework")`** — follow Law 1
- **Don't import from `stateweave.core.*` internals** — only use the public API

### 3. Add Tests

Create `tests/unit/test_your_framework_adapter.py` and `tests/integration/test_your_framework_to_*.py`.

Minimum test coverage:
- Export basic state
- Import basic state
- Round-trip (export → import → re-export → compare)
- Non-portable detection
- Error handling (missing agent, invalid state)

### 4. Register the Adapter

1. Add to `stateweave/adapters/__init__.py`
2. Add to `stateweave/__init__.py`
3. Add to `stateweave/mcp_server/server.py` `_adapters` dict
4. Add to `board/MANIFEST.md`
5. Add optional dependency group to `pyproject.toml`

### 5. Run UCE

```bash
python scripts/uce.py
```

All 10 scanners must pass GREEN.

## Code Style

- **Formatter**: `ruff format`
- **Linter**: `ruff check`
- **Line length**: 100 characters
- **Target Python**: 3.10+
- **Type hints**: Required for all public functions
- **Docstrings**: Google style, required for all public classes and functions

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(adapters): add Letta adapter
fix(encryption): handle empty plaintext edge case
test(crewai): add delegation chain round-trip test
docs(readme): update framework support matrix
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch from `main`
3. Write code + tests
4. Run `pytest tests/ -v` — all tests must pass
5. Run `python scripts/uce.py` — all scanners must pass GREEN
6. Run `ruff check stateweave/ tests/` — no lint errors
7. Submit PR with description of changes

## Reporting Issues

Use GitHub Issues with the appropriate template:
- **Bug Report**: Include reproduction steps, expected vs actual behavior
- **Feature Request**: Describe the use case and proposed solution
- **Adapter Request**: Which framework, link to its state API docs

## License

By contributing, you agree that your contributions are licensed under the Apache 2.0 License.
