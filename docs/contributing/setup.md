# Development Setup

## Prerequisites

- Python 3.10+
- Git

## Clone and Install

```bash
git clone https://github.com/GDWN-BLDR/stateweave.git
cd stateweave
pip install -e ".[dev]"
```

## Run Tests

```bash
# All tests
pytest tests/ -v

# Specific module
pytest tests/unit/test_encryption.py -v

# With coverage
pytest tests/ --cov=stateweave --cov-report=term-missing
```

## Run UCE

```bash
python scripts/uce.py

# CI mode (exit 1 on failure)
python scripts/uce.py --mode=CI --json
```

## Linting

```bash
ruff check stateweave/
ruff format stateweave/
```

## Type Checking

```bash
mypy stateweave/
```

## Project Structure

```
stateweave/
├── schema/        # Universal Schema (Pydantic models)
├── core/          # Engine (serializer, encryption, diff, delta, merge, migration)
├── adapters/      # Framework adapters (10 total)
├── mcp_server/    # MCP Server implementation
└── compliance/    # UCE scanners (10 total)
```
