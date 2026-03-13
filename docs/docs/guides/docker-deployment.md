# Docker Deployment

## Quick Start

### REST API (Production)

```bash
docker-compose up -d stateweave-api
```

The REST API is available at `http://localhost:8080`.

### MCP Server (Development)

```bash
docker-compose up stateweave-mcp
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check (version, adapter count) |
| `GET` | `/adapters` | List all adapters with tier info |
| `GET` | `/schema` | Universal Schema JSON Schema |
| `POST` | `/export` | Export agent state |
| `POST` | `/import` | Import agent state |
| `POST` | `/detect` | Auto-detect framework |
| `POST` | `/diff` | Diff two payloads |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STATEWEAVE_HOST` | `0.0.0.0` | Bind address |
| `STATEWEAVE_PORT` | `8080` | Port |
| `STATEWEAVE_LOG_LEVEL` | `INFO` | Log level |
| `STATEWEAVE_LOG_FORMAT` | `json` | `json` or `text` |

## Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stateweave-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: stateweave-api
  template:
    metadata:
      labels:
        app: stateweave-api
    spec:
      containers:
        - name: stateweave
          image: ghcr.io/gdwn-bldr/stateweave:latest
          command: ["python", "-m", "stateweave.rest_api"]
          ports:
            - containerPort: 8080
          env:
            - name: STATEWEAVE_LOG_FORMAT
              value: json
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: stateweave-api
spec:
  selector:
    app: stateweave-api
  ports:
    - port: 8080
      targetPort: 8080
  type: ClusterIP
```
