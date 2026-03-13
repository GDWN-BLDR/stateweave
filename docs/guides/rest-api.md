# REST API

StateWeave includes a REST API wrapper for non-MCP consumers.

## Running the REST API

```bash
# Directly
python -m stateweave.rest_api

# Via Docker
docker compose up stateweave-api
```

The server starts on port 8080 by default.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STATEWEAVE_HOST` | `0.0.0.0` | Bind address |
| `STATEWEAVE_PORT` | `8080` | Listen port |
| `STATEWEAVE_LOG_LEVEL` | `INFO` | Logging level |
| `STATEWEAVE_LOG_FORMAT` | `json` | Log format (`json` or `text`) |

## Health Check

```bash
curl http://localhost:8080/health
```
