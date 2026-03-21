"""
Red Team: Adversarial REST API Fuzzing
==========================================
Attack the StateWeave REST API (http.server-based) with oversized bodies,
malformed requests, path traversal, HTTP method confusion, and CORS abuse.
Uses raw http.client to bypass any framework safety nets.
"""

import http.client
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from contextlib import contextmanager
from http.server import HTTPServer

import pytest

# RemoteDisconnected is raised when the server crashes on bad input — this is
# itself a finding (server should return 400, not drop the connection).
from http.client import RemoteDisconnected


def find_free_port():
    """Find a free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def api_server():
    """Start a StateWeave REST API server in a subprocess for testing."""
    port = find_free_port()
    env = os.environ.copy()
    env["STATEWEAVE_HOST"] = "127.0.0.1"
    env["STATEWEAVE_PORT"] = str(port)
    env["STATEWEAVE_LOG_LEVEL"] = "WARNING"

    proc = subprocess.Popen(
        [sys.executable, "-m", "stateweave.rest_api"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to be ready
    for attempt in range(50):
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1)
            conn.request("GET", "/health")
            resp = conn.getresponse()
            if resp.status == 200:
                conn.close()
                break
            conn.close()
        except (ConnectionRefusedError, OSError):
            time.sleep(0.1)
    else:
        proc.terminate()
        pytest.fail("REST API server failed to start within 5 seconds")

    yield port

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def api_request(port, method, path, body=None, headers=None, timeout=10):
    """Make a raw HTTP request. Returns (status, headers_dict, body_str)."""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    hdrs = headers or {}
    if body is not None and "Content-Type" not in hdrs:
        hdrs["Content-Type"] = "application/json"

    body_bytes = None
    if body is not None:
        if isinstance(body, bytes):
            body_bytes = body
        elif isinstance(body, str):
            body_bytes = body.encode()
        else:
            body_bytes = json.dumps(body).encode()

    conn.request(method, path, body=body_bytes, headers=hdrs)
    resp = conn.getresponse()
    resp_body = resp.read().decode("utf-8", errors="replace")
    status = resp.status
    resp_headers = dict(resp.getheaders())
    conn.close()
    return status, resp_headers, resp_body


# ═══════════════════════════════════════════════════════════════════
# 1. MALFORMED REQUEST BODIES
# ═══════════════════════════════════════════════════════════════════

class TestMalformedBodies:
    """Send broken request bodies to POST endpoints."""

    def test_empty_body_on_post(self, api_server):
        """POST with empty body must return 400, not crash."""
        status, _, body = api_request(api_server, "POST", "/import", body=b"")
        assert status == 400

    def test_truncated_json(self, api_server):
        """Truncated JSON must return 400, not crash."""
        status, _, body = api_request(
            api_server, "POST", "/import",
            body=b'{"framework": "langgraph", "payload":'
        )
        assert status == 400
        assert "Invalid JSON" in body or "error" in body.lower()

    def test_binary_garbage_body(self, api_server):
        """Random binary data as body must return 400, not crash."""
        status, _, body = api_request(
            api_server, "POST", "/import",
            body=os.urandom(500)
        )
        assert status == 400
        assert "Invalid JSON" in body or "error" in body.lower()

    def test_json_with_trailing_comma(self, api_server):
        """JSON with trailing comma (invalid) must return 400."""
        status, _, body = api_request(
            api_server, "POST", "/import",
            body=b'{"framework": "langgraph",}'
        )
        assert status == 400
        assert "Invalid JSON" in body or "error" in body.lower()

    def test_null_body(self, api_server):
        """JSON null as body must return error."""
        status, _, body = api_request(
            api_server, "POST", "/import",
            body=b"null"
        )
        assert status in (400, 500)

    def test_json_array_instead_of_object(self, api_server):
        """JSON array instead of object must be handled."""
        status, _, body = api_request(
            api_server, "POST", "/import",
            body=b'[1, 2, 3]'
        )
        assert status in (400, 500)


# ═══════════════════════════════════════════════════════════════════
# 2. PATH TRAVERSAL IN URL
# ═══════════════════════════════════════════════════════════════════

class TestURLPathTraversal:
    """Attempt to access files via URL path traversal."""

    TRAVERSAL_PATHS = [
        "/../../../etc/passwd",
        "/%2e%2e/%2e%2e/etc/passwd",
        "/..%252f..%252f..%252fetc/passwd",
        "/health/../../../etc/passwd",
        "//etc/passwd",
        "/./././health",
    ]

    @pytest.mark.parametrize("path", TRAVERSAL_PATHS)
    def test_path_traversal_get(self, api_server, path):
        """Path traversal via GET must return 404, not file contents."""
        status, _, body = api_request(api_server, "GET", path)
        assert "root:" not in body  # No /etc/passwd leak
        assert status in (400, 404, 301)  # Not 200 with file contents

    @pytest.mark.parametrize("path", TRAVERSAL_PATHS)
    def test_path_traversal_post(self, api_server, path):
        """Path traversal via POST must not execute or leak."""
        status, _, body = api_request(
            api_server, "POST", path,
            body=b'{"test": true}'
        )
        assert "root:" not in body


# ═══════════════════════════════════════════════════════════════════
# 3. HTTP METHOD CONFUSION
# ═══════════════════════════════════════════════════════════════════

class TestHTTPMethodConfusion:
    """Send unexpected HTTP methods."""

    UNEXPECTED_METHODS = ["PUT", "DELETE", "PATCH", "HEAD"]

    @pytest.mark.parametrize("method", UNEXPECTED_METHODS)
    def test_unexpected_method_on_import(self, api_server, method):
        """Unexpected HTTP methods on /import must not execute side effects."""
        try:
            status, _, body = api_request(
                api_server, method, "/import",
                body=b'{"framework":"langgraph"}'
            )
            # Should return error or method not allowed
            assert status in (400, 404, 405, 501)
        except (http.client.BadStatusLine, ConnectionError):
            pass  # Server rejecting the connection is also OK

    @pytest.mark.parametrize("method", UNEXPECTED_METHODS)
    def test_unexpected_method_on_health(self, api_server, method):
        """Unexpected methods on /health."""
        try:
            status, _, _ = api_request(api_server, method, "/health")
            # HEAD on a GET endpoint returning 200 is actually fine per HTTP spec
            if method == "HEAD":
                assert status in (200, 404, 405, 501)
            else:
                assert status in (400, 404, 405, 501)
        except (http.client.BadStatusLine, ConnectionError):
            pass


# ═══════════════════════════════════════════════════════════════════
# 4. CORS VALIDATION
# ═══════════════════════════════════════════════════════════════════

class TestCORSValidation:
    """Verify CORS headers are present and not leaking credentials."""

    def test_cors_headers_on_get(self, api_server):
        """GET /health must include CORS headers."""
        status, headers, _ = api_request(api_server, "GET", "/health")
        assert status == 200
        # Verify CORS is set
        assert "Access-Control-Allow-Origin" in headers or "access-control-allow-origin" in headers

    def test_options_preflight(self, api_server):
        """OPTIONS request must return CORS preflight headers."""
        status, headers, _ = api_request(
            api_server, "OPTIONS", "/import",
            headers={"Origin": "http://evil.com"}
        )
        assert status == 204
        assert "Access-Control-Allow-Methods" in headers or "access-control-allow-methods" in headers

    def test_no_credentials_in_cors(self, api_server):
        """CORS must NOT include Access-Control-Allow-Credentials."""
        status, headers, _ = api_request(api_server, "GET", "/health")
        # Allowing credentials with wildcard origin is a security antipattern
        cred_header = headers.get("Access-Control-Allow-Credentials",
                                  headers.get("access-control-allow-credentials"))
        if cred_header:
            assert cred_header.lower() != "true", \
                "Credentials allowed with wildcard origin is dangerous"


# ═══════════════════════════════════════════════════════════════════
# 5. CONTENT-TYPE CONFUSION
# ═══════════════════════════════════════════════════════════════════

class TestContentTypeConfusion:
    """Send wrong Content-Type headers."""

    def test_xml_content_type(self, api_server):
        """XML Content-Type with JSON body must still parse or reject cleanly."""
        status, _, body = api_request(
            api_server, "POST", "/import",
            body=b'{"framework":"langgraph","payload":{}}',
            headers={"Content-Type": "text/xml"}
        )
        # Should either work (ignoring Content-Type) or fail cleanly
        assert status in (200, 400, 415, 500)

    def test_multipart_content_type(self, api_server):
        """multipart/form-data Content-Type must not crash."""
        status, _, body = api_request(
            api_server, "POST", "/import",
            body=b'{"framework":"langgraph"}',
            headers={"Content-Type": "multipart/form-data; boundary=----"}
        )
        assert status in (200, 400, 415, 500)

    def test_no_content_type(self, api_server):
        """Missing Content-Type header must be handled."""
        conn = http.client.HTTPConnection("127.0.0.1", api_server, timeout=5)
        conn.request("POST", "/import", body=b'{"framework":"langgraph"}')
        resp = conn.getresponse()
        assert resp.status in (200, 400, 500)
        conn.close()


# ═══════════════════════════════════════════════════════════════════
# 6. RESPONSE VALIDATION
# ═══════════════════════════════════════════════════════════════════

class TestResponseValidation:
    """Verify responses don't leak internal details."""

    def test_error_response_no_stack_trace(self, api_server):
        """Error responses must NOT contain Python tracebacks."""
        status, _, body = api_request(
            api_server, "POST", "/import",
            body=b'{"framework":"nonexistent"}'
        )
        assert "Traceback" not in body
        assert "File \"" not in body
        assert "line " not in body or "error" in body.lower()

    def test_404_no_internal_paths(self, api_server):
        """404 responses must not leak filesystem paths."""
        status, _, body = api_request(api_server, "GET", "/nonexistent")
        assert status == 404
        assert "/Users/" not in body
        assert "/home/" not in body
        assert "stateweave/" not in body or "error" in body.lower()

    def test_health_endpoint_returns_json(self, api_server):
        """Health endpoint must return valid JSON."""
        status, headers, body = api_request(api_server, "GET", "/health")
        assert status == 200
        data = json.loads(body)
        assert data["status"] == "healthy"
        assert "version" in data

    def test_server_header_present(self, api_server):
        """Server header must identify as StateWeave."""
        status, headers, body = api_request(api_server, "GET", "/health")
        server_header = headers.get("Server", headers.get("server", ""))
        assert "StateWeave" in server_header or "stateweave" in server_header.lower()


# ═══════════════════════════════════════════════════════════════════
# 7. UNKNOWN FRAMEWORK IN API
# ═══════════════════════════════════════════════════════════════════

class TestUnknownFramework:
    """Verify API handles unknown framework names gracefully."""

    def test_export_unknown_framework(self, api_server):
        """Export with unknown framework must return 400."""
        status, _, body = api_request(
            api_server, "POST", "/export",
            body={"framework": "nonexistent_framework", "agent_id": "test"}
        )
        assert status == 400
        data = json.loads(body)
        assert "error" in data

    def test_import_unknown_framework(self, api_server):
        """Import with unknown framework must return 400."""
        status, _, body = api_request(
            api_server, "POST", "/import",
            body={"framework": "evil_framework", "payload": {}}
        )
        assert status == 400

    def test_export_missing_framework(self, api_server):
        """Export without framework field must return 400."""
        status, _, body = api_request(
            api_server, "POST", "/export",
            body={"agent_id": "test"}
        )
        assert status == 400
