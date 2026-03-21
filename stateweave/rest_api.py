"""
StateWeave REST API — HTTP wrapper for StateWeave operations.

Provides RESTful endpoints for export, import, diff, detect, and health.
This is a lightweight alternative to the MCP Server for non-MCP consumers.

Run:
    python -m stateweave.rest_api          # Starts on port 8080
    STATEWEAVE_PORT=9000 python -m stateweave.rest_api  # Custom port
"""

import json
import logging
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

from stateweave import __version__
from stateweave.adapters import ADAPTER_REGISTRY
from stateweave.core.detect import detect_framework
from stateweave.core.diff import diff_payloads
from stateweave.core.serializer import StateWeaveSerializer

logger = logging.getLogger("stateweave.rest_api")

serializer = StateWeaveSerializer()


class StateWeaveHandler(BaseHTTPRequestHandler):
    """HTTP request handler for StateWeave REST API."""

    server_version = f"StateWeave/{__version__}"

    def _send_json(self, status: int, data: dict) -> None:
        """Send a JSON response."""
        body = json.dumps(data, indent=2, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    # Sentinel value for malformed JSON (body was present but unparseable)
    _BAD_JSON = object()

    def _read_body(self) -> Optional[dict]:
        """Read and parse JSON request body."""
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self.send_response(400)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "application/json")
            error_body = json.dumps({"error": f"Invalid JSON: {e}"}).encode()
            self.send_header("Content-Length", str(len(error_body)))
            self.end_headers()
            self.wfile.write(error_body)
            return self._BAD_JSON

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self._send_json(
                200,
                {
                    "status": "healthy",
                    "version": __version__,
                    "adapters": len(ADAPTER_REGISTRY),
                },
            )
        elif self.path == "/adapters":
            adapters = []
            for name, cls in ADAPTER_REGISTRY.items():
                adapter = cls()
                adapters.append(
                    {
                        "name": name,
                        "tier": adapter.tier.value if hasattr(adapter, "tier") else "unknown",
                        "framework_name": adapter.framework_name,
                    }
                )
            self._send_json(200, {"adapters": adapters})
        elif self.path == "/schema":
            from stateweave.schema.v1 import StateWeavePayload

            self._send_json(200, StateWeavePayload.model_json_schema())
        else:
            self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        """Handle POST requests."""
        body = self._read_body()
        if body is self._BAD_JSON:
            return  # 400 already sent by _read_body
        if body is None:
            self._send_json(400, {"error": "Request body required"})
            return

        try:
            if self.path == "/export":
                framework = body.get("framework")
                agent_id = body.get("agent_id", "default")
                if framework not in ADAPTER_REGISTRY:
                    self._send_json(400, {"error": f"Unknown framework: {framework}"})
                    return
                adapter = ADAPTER_REGISTRY[framework]()
                payload = adapter.export_state(agent_id)
                self._send_json(200, serializer.to_dict(payload))

            elif self.path == "/import":
                framework = body.get("framework")
                payload_data = body.get("payload")
                if not framework or not payload_data:
                    self._send_json(400, {"error": "framework and payload required"})
                    return
                if framework not in ADAPTER_REGISTRY:
                    self._send_json(400, {"error": f"Unknown framework: {framework}"})
                    return
                adapter = ADAPTER_REGISTRY[framework]()
                payload = serializer.from_dict(payload_data)
                result = adapter.import_state(payload)
                self._send_json(200, {"result": result})

            elif self.path == "/detect":
                state = body.get("state", {})
                result = detect_framework(state)
                self._send_json(200, {"detected_framework": result})

            elif self.path == "/diff":
                state_a = body.get("state_a")
                state_b = body.get("state_b")
                if not state_a or not state_b:
                    self._send_json(400, {"error": "state_a and state_b required"})
                    return
                payload_a = serializer.from_dict(state_a)
                payload_b = serializer.from_dict(state_b)
                diff = diff_payloads(payload_a, payload_b)
                self._send_json(
                    200,
                    {
                        "changes": len(diff.entries),
                        "added": diff.added_count,
                        "removed": diff.removed_count,
                        "modified": diff.modified_count,
                        "entries": [e.model_dump() for e in diff.entries],
                    },
                )

            else:
                self._send_json(404, {"error": "Not found"})

        except Exception as e:
            logger.exception("REST API error")
            self._send_json(500, {"error": str(e)})

    def log_message(self, fmt, *args):
        """Use Python logging instead of stderr."""
        logger.info(fmt, *args)


def main():
    """Start the REST API server."""
    host = os.environ.get("STATEWEAVE_HOST", "0.0.0.0")
    port = int(os.environ.get("STATEWEAVE_PORT", "8080"))

    logging.basicConfig(
        level=os.environ.get("STATEWEAVE_LOG_LEVEL", "INFO"),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    server = HTTPServer((host, port), StateWeaveHandler)
    logger.info(f"StateWeave REST API v{__version__} listening on {host}:{port}")
    logger.info("Endpoints: GET /health /adapters /schema | POST /export /import /detect /diff")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.server_close()


if __name__ == "__main__":
    main()
