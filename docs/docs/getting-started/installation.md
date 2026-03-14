# Installation

## Python Package

```bash
pip install stateweave
```

**Requirements:** Python ≥ 3.10

## Verify Installation

```python
import stateweave
print(stateweave.__version__)  # 0.3.1
```

## Optional Extras

```bash
# With MCP server support
pip install stateweave[server]

# Development install
git clone https://github.com/GDWN-BLDR/stateweave.git
cd stateweave
pip install -e ".[dev]"
```

## Docker

```bash
# MCP Server (stdio mode)
docker-compose up stateweave-mcp

# REST API (HTTP mode)
docker-compose up stateweave-api
```

## TypeScript SDK

```bash
npm install @stateweave/sdk
```

```typescript
import { StateWeaveClient } from '@stateweave/sdk';

const client = new StateWeaveClient('http://localhost:8080');
const health = await client.health();
```
