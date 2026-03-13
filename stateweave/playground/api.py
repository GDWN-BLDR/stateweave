"""
StateWeave Playground API — Interactive state translation and exploration.
==========================================================================
REST API endpoints for the interactive playground web app.
Enables developers to:
- Translate state between frameworks without installing anything
- Explore the Universal Schema interactively
- Try time travel (checkpoint, rollback, diff)

Usage:
    python -m stateweave.playground.api
    # Serves on http://localhost:8077
"""

import json
import logging
import tempfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict

from stateweave.adapters import ADAPTER_REGISTRY
from stateweave.core.diff import diff_payloads
from stateweave.core.doctor import run_doctor
from stateweave.core.serializer import StateWeaveSerializer
from stateweave.core.timetravel import CheckpointStore

logger = logging.getLogger("stateweave.playground")

PLAYGROUND_PORT = 8077


class PlaygroundAPI:
    """Core API logic for the playground (framework-agnostic)."""

    def __init__(self):
        self._serializer = StateWeaveSerializer(pretty=True)
        self._tmpdir = tempfile.mkdtemp(prefix="stateweave-playground-")
        self._store = CheckpointStore(store_dir=self._tmpdir)

    def translate(self, payload_dict: Dict, target_framework: str) -> Dict[str, Any]:
        """Translate a payload to a target framework's format.

        Args:
            payload_dict: Raw payload dict.
            target_framework: Target framework name.

        Returns:
            Dict with translated state and metadata.
        """
        payload = self._serializer.from_dict(payload_dict)

        if target_framework not in ADAPTER_REGISTRY:
            return {
                "error": f"Unknown framework: {target_framework}",
                "available": list(ADAPTER_REGISTRY.keys()),
            }

        adapter_cls = ADAPTER_REGISTRY[target_framework]
        adapter = adapter_cls()

        # Export to target format
        target_dict = (
            adapter.to_framework_format(payload)
            if hasattr(adapter, "to_framework_format")
            else self._serializer.to_dict(payload)
        )

        return {
            "source_framework": payload.source_framework,
            "target_framework": target_framework,
            "universal_schema": self._serializer.to_dict(payload),
            "target_format": target_dict,
            "message_count": len(payload.cognitive_state.conversation_history),
            "memory_keys": len(payload.cognitive_state.working_memory),
            "non_portable_warnings": len(payload.non_portable_warnings),
        }

    def diff(self, state_a: Dict, state_b: Dict) -> Dict[str, Any]:
        """Diff two states."""
        payload_a = self._serializer.from_dict(state_a)
        payload_b = self._serializer.from_dict(state_b)
        result = diff_payloads(payload_a, payload_b)
        return {
            "report": result.to_report(),
            "total_changes": result.added_count + result.removed_count + result.modified_count,
            "additions": result.added_count,
            "deletions": result.removed_count,
            "modifications": result.modified_count,
        }

    def checkpoint(self, payload_dict: Dict, label: str = "") -> Dict[str, Any]:
        """Create a checkpoint."""
        payload = self._serializer.from_dict(payload_dict)
        meta = self._store.checkpoint(payload, label=label or None)
        return {
            "version": meta.version,
            "hash": meta.hash,
            "agent_id": meta.agent_id,
            "label": meta.label,
        }

    def get_history(self, agent_id: str) -> Dict[str, Any]:
        """Get checkpoint history."""
        history = self._store.history(agent_id)
        return {
            "agent_id": agent_id,
            "version_count": history.version_count,
            "checkpoints": [cp.to_dict() for cp in history.checkpoints],
            "formatted": self._store.format_history(agent_id),
        }

    def validate(self, payload_dict: Dict) -> Dict[str, Any]:
        """Validate a payload."""
        try:
            payload = self._serializer.from_dict(payload_dict)
            return {
                "valid": True,
                "source_framework": payload.source_framework,
                "agent_id": payload.metadata.agent_id,
                "messages": len(payload.cognitive_state.conversation_history),
                "warnings": len(payload.non_portable_warnings),
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def doctor(self) -> Dict[str, Any]:
        """Run doctor diagnostics."""
        report = run_doctor()
        return {
            "healthy": report.healthy,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status,
                    "message": c.message,
                    "suggestion": c.suggestion,
                }
                for c in report.checks
            ],
            "formatted": report.format(),
        }

    def info(self) -> Dict[str, Any]:
        """Get playground info."""
        import stateweave

        return {
            "version": stateweave.__version__,
            "adapters": list(ADAPTER_REGISTRY.keys()),
            "adapter_count": len(ADAPTER_REGISTRY),
            "endpoints": [
                "POST /api/translate",
                "POST /api/diff",
                "POST /api/checkpoint",
                "POST /api/validate",
                "GET  /api/history/{agent_id}",
                "GET  /api/doctor",
                "GET  /api/info",
            ],
        }


class PlaygroundHandler(BaseHTTPRequestHandler):
    """HTTP handler for the playground API."""

    api = PlaygroundAPI()

    def do_GET(self):
        if self.path == "/api/info":
            self._json_response(self.api.info())
        elif self.path == "/api/doctor":
            self._json_response(self.api.doctor())
        elif self.path.startswith("/api/history/"):
            agent_id = self.path.split("/api/history/")[1]
            self._json_response(self.api.get_history(agent_id))
        elif self.path == "/" or self.path == "/index.html":
            self._serve_playground_html()
        else:
            self._json_response({"error": "Not found"}, status=404)

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._json_response({"error": "Invalid JSON"}, status=400)
            return

        if self.path == "/api/translate":
            result = self.api.translate(data.get("payload", {}), data.get("target", ""))
            self._json_response(result)
        elif self.path == "/api/diff":
            result = self.api.diff(data.get("state_a", {}), data.get("state_b", {}))
            self._json_response(result)
        elif self.path == "/api/checkpoint":
            result = self.api.checkpoint(data.get("payload", {}), data.get("label", ""))
            self._json_response(result)
        elif self.path == "/api/validate":
            result = self.api.validate(data.get("payload", {}))
            self._json_response(result)
        else:
            self._json_response({"error": "Not found"}, status=404)

    def _json_response(self, data: Dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, default=str).encode())

    def _serve_playground_html(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(PLAYGROUND_HTML.encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        logger.debug(format, *args)


PLAYGROUND_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>StateWeave Playground</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #0a0a0f; color: #e0e0e0; }
  .header { padding: 2rem; text-align: center; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); }
  .header h1 { font-size: 2rem; color: #fff; }
  .header p { color: #8b8ba7; margin-top: 0.5rem; }
  .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
  .panels { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-top: 1.5rem; }
  .panel { background: #12121a; border: 1px solid #2a2a3e; border-radius: 12px; padding: 1.5rem; }
  .panel h3 { color: #fff; margin-bottom: 1rem; font-size: 1rem; }
  textarea { width: 100%; height: 300px; background: #0a0a0f; color: #a78bfa; border: 1px solid #2a2a3e;
             border-radius: 8px; padding: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;
             resize: vertical; }
  button { background: linear-gradient(135deg, #6c5ce7 0%, #a78bfa 100%); color: #fff; border: none;
           padding: 0.75rem 1.5rem; border-radius: 8px; cursor: pointer; font-weight: 600;
           transition: all 0.2s; margin-top: 1rem; }
  button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(108, 92, 231, 0.4); }
  .controls { display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; }
  select { background: #0a0a0f; color: #e0e0e0; border: 1px solid #2a2a3e; padding: 0.5rem;
           border-radius: 6px; }
  .status { margin-top: 1rem; padding: 1rem; border-radius: 8px; font-family: monospace;
            font-size: 0.85rem; white-space: pre-wrap; }
  .status.ok { background: #0d2818; border: 1px solid #1a4d2e; color: #4ade80; }
  .status.error { background: #2d0d0d; border: 1px solid #4d1a1a; color: #f87171; }
  .badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.75rem;
           background: #1e1e3a; color: #a78bfa; border: 1px solid #2a2a4a; }
  .actions { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem;
             margin-top: 1.5rem; }
  .action-card { background: #12121a; border: 1px solid #2a2a3e; border-radius: 12px;
                 padding: 1.5rem; cursor: pointer; transition: all 0.2s; text-align: center; }
  .action-card:hover { border-color: #6c5ce7; transform: translateY(-2px); }
  .action-card h4 { color: #fff; margin-bottom: 0.5rem; }
  .action-card p { color: #8b8ba7; font-size: 0.85rem; }
</style>
</head>
<body>
<div class="header">
  <h1>🧶 StateWeave Playground</h1>
  <p>Try state translation, diffing, and time travel — no installation needed</p>
</div>
<div class="container">
  <div class="actions">
    <div class="action-card" onclick="runDoctor()">
      <h4>🩺 Doctor</h4>
      <p>Run diagnostics</p>
    </div>
    <div class="action-card" onclick="showInfo()">
      <h4>ℹ️ Info</h4>
      <p>View adapters & API</p>
    </div>
    <div class="action-card" onclick="validatePayload()">
      <h4>✓ Validate</h4>
      <p>Check a payload</p>
    </div>
    <div class="action-card" onclick="diffPayloads()">
      <h4>🔍 Diff</h4>
      <p>Compare two states</p>
    </div>
  </div>
  <div class="panels">
    <div class="panel">
      <h3>Input Payload (JSON)</h3>
      <textarea id="input" placeholder='Paste a StateWeave payload...'></textarea>
      <div class="controls">
        <select id="target">
          <option value="">Select target framework...</option>
        </select>
        <button onclick="translate()">Translate →</button>
      </div>
    </div>
    <div class="panel">
      <h3>Output</h3>
      <textarea id="output" readonly placeholder="Results appear here..."></textarea>
    </div>
  </div>
  <div id="status"></div>
</div>
<script>
const API = '';
async function api(path, data) {
  const opts = data ? { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data) }
                     : { method: 'GET' };
  const res = await fetch(API + path, opts);
  return res.json();
}
function show(data, ok=true) {
  document.getElementById('output').value = JSON.stringify(data, null, 2);
  const el = document.getElementById('status');
  el.className = 'status ' + (ok ? 'ok' : 'error');
  el.textContent = ok ? '✓ Success' : '✗ Error — see output';
}
async function translate() {
  const payload = JSON.parse(document.getElementById('input').value);
  const target = document.getElementById('target').value;
  show(await api('/api/translate', { payload, target }));
}
async function validatePayload() {
  const payload = JSON.parse(document.getElementById('input').value);
  const res = await api('/api/validate', { payload });
  show(res, res.valid);
}
async function diffPayloads() {
  show({hint: 'Paste state_a in Input, then call diff with state_b in a second textarea (coming soon)'});
}
async function runDoctor() { show(await api('/api/doctor')); }
async function showInfo() { show(await api('/api/info')); }
// Load adapters on start
api('/api/info').then(data => {
  const sel = document.getElementById('target');
  (data.adapters || []).forEach(a => { const o = document.createElement('option'); o.value = a; o.textContent = a; sel.appendChild(o); });
}).catch(() => {});
</script>
</body>
</html>
"""


def serve(port: int = PLAYGROUND_PORT):
    """Start the playground server."""
    server = HTTPServer(("", port), PlaygroundHandler)
    print(f"🧶 StateWeave Playground running at http://localhost:{port}")
    print(f"   API endpoints: http://localhost:{port}/api/info")
    print("   Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    serve()
