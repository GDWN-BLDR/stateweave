"""
MCP Server entry point — run with `python -m stateweave.mcp_server`.
=====================================================================
Launches the StateWeave MCP Server over stdio, making export/import/diff
tools available to any MCP-compatible client.
"""

import asyncio
import json
import logging
import sys

from stateweave.mcp_server.server import (
    BACKUP_BEFORE_RISKY_OPERATION,
    MIGRATION_GUIDE,
    diff_agent_states,
    export_agent_state,
    get_agent_snapshot_resource,
    get_migration_history_resource,
    get_schema_resource,
    import_agent_state,
)

logger = logging.getLogger("stateweave.mcp_server")


async def handle_jsonrpc(request: dict) -> dict:
    """Handle a JSON-RPC 2.0 request."""
    method = request.get("method", "")
    params = request.get("params", {})
    req_id = request.get("id")

    try:
        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"listChanged": False},
                    "prompts": {"listChanged": False},
                },
                "serverInfo": {
                    "name": "stateweave",
                    "version": "0.1.0",
                },
            }

        elif method == "notifications/initialized":
            return None  # No response for notifications

        elif method == "tools/list":
            result = {
                "tools": [
                    {
                        "name": "export_agent_state",
                        "description": "Export an agent's cognitive state from a supported framework",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "framework": {
                                    "type": "string",
                                    "description": "Source framework (langgraph, mcp, crewai, autogen)",
                                },
                                "agent_id": {
                                    "type": "string",
                                    "description": "Agent identifier",
                                },
                                "encrypt": {
                                    "type": "boolean",
                                    "description": "Whether to encrypt the payload",
                                    "default": False,
                                },
                            },
                            "required": ["framework", "agent_id"],
                        },
                    },
                    {
                        "name": "import_agent_state",
                        "description": "Import an agent's cognitive state into a target framework",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "target_framework": {
                                    "type": "string",
                                    "description": "Target framework (langgraph, mcp, crewai, autogen)",
                                },
                                "payload": {
                                    "type": "object",
                                    "description": "StateWeavePayload as JSON",
                                },
                                "agent_id": {
                                    "type": "string",
                                    "description": "Optional target agent ID",
                                },
                            },
                            "required": ["target_framework", "payload"],
                        },
                    },
                    {
                        "name": "diff_agent_states",
                        "description": "Compare two agent states and return a diff report",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "state_a": {
                                    "type": "object",
                                    "description": "The 'before' StateWeavePayload",
                                },
                                "state_b": {
                                    "type": "object",
                                    "description": "The 'after' StateWeavePayload",
                                },
                            },
                            "required": ["state_a", "state_b"],
                        },
                    },
                ],
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name == "export_agent_state":
                tool_result = await export_agent_state(**arguments)
            elif tool_name == "import_agent_state":
                tool_result = await import_agent_state(**arguments)
            elif tool_name == "diff_agent_states":
                tool_result = await diff_agent_states(**arguments)
            else:
                tool_result = {"error": f"Unknown tool: {tool_name}"}

            result = {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(tool_result, indent=2, default=str),
                    }
                ],
            }

        elif method == "resources/list":
            result = {
                "resources": [
                    {
                        "uri": "stateweave://schemas/v1",
                        "name": "Universal Schema v1",
                        "description": "The canonical JSON Schema for agent cognitive state",
                        "mimeType": "application/json",
                    },
                    {
                        "uri": "stateweave://migrations/history",
                        "name": "Migration History",
                        "description": "Log of all export/import operations",
                        "mimeType": "application/json",
                    },
                ],
            }

        elif method == "resources/read":
            uri = params.get("uri", "")
            if uri == "stateweave://schemas/v1":
                resource = get_schema_resource()
            elif uri == "stateweave://migrations/history":
                resource = get_migration_history_resource()
            elif uri.startswith("stateweave://agents/") and uri.endswith("/snapshot"):
                agent_id = uri.replace("stateweave://agents/", "").replace("/snapshot", "")
                resource = get_agent_snapshot_resource(agent_id)
            else:
                resource = {"error": f"Unknown resource: {uri}"}

            result = {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": resource.get("mimeType", "application/json"),
                        "text": resource.get("content", json.dumps(resource)),
                    }
                ],
            }

        elif method == "prompts/list":
            result = {
                "prompts": [
                    {
                        "name": BACKUP_BEFORE_RISKY_OPERATION["name"],
                        "description": BACKUP_BEFORE_RISKY_OPERATION["description"],
                        "arguments": BACKUP_BEFORE_RISKY_OPERATION["arguments"],
                    },
                    {
                        "name": MIGRATION_GUIDE["name"],
                        "description": MIGRATION_GUIDE["description"],
                        "arguments": MIGRATION_GUIDE["arguments"],
                    },
                ],
            }

        elif method == "prompts/get":
            prompt_name = params.get("name")
            arguments = params.get("arguments", {})

            if prompt_name == "backup_before_risky_operation":
                text = BACKUP_BEFORE_RISKY_OPERATION["template"].format(**arguments)
            elif prompt_name == "migration_guide":
                text = MIGRATION_GUIDE["template"].format(**arguments)
            else:
                text = f"Unknown prompt: {prompt_name}"

            result = {
                "description": f"Prompt: {prompt_name}",
                "messages": [
                    {
                        "role": "user",
                        "content": {"type": "text", "text": text},
                    }
                ],
            }

        else:
            result = {"error": f"Unknown method: {method}"}

    except Exception as e:
        logger.error(f"Error handling {method}: {e}")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32603, "message": str(e)},
        }

    if result is None:
        return None

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": result,
    }


async def main():
    """Run the MCP server over stdio."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,  # Logs to stderr, JSON-RPC to stdout
    )
    logger.info("StateWeave MCP Server starting (stdio transport)")

    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

    writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
        asyncio.streams.FlowControlMixin, sys.stdout
    )
    writer = asyncio.StreamWriter(
        writer_transport, writer_protocol, reader, asyncio.get_event_loop()
    )

    logger.info("StateWeave MCP Server ready")

    buffer = b""
    while True:
        try:
            chunk = await reader.read(4096)
            if not chunk:
                break

            buffer += chunk

            # Try to parse complete JSON-RPC messages
            while buffer:
                # Look for Content-Length header
                if b"Content-Length:" in buffer:
                    header_end = buffer.find(b"\r\n\r\n")
                    if header_end == -1:
                        break

                    header = buffer[:header_end].decode("utf-8")
                    content_length = None
                    for line in header.split("\r\n"):
                        if line.startswith("Content-Length:"):
                            content_length = int(line.split(":")[1].strip())

                    if content_length is None:
                        break

                    body_start = header_end + 4
                    if len(buffer) < body_start + content_length:
                        break

                    body = buffer[body_start : body_start + content_length]
                    buffer = buffer[body_start + content_length :]

                    request = json.loads(body)
                    response = await handle_jsonrpc(request)

                    if response is not None:
                        response_bytes = json.dumps(response).encode("utf-8")
                        header = f"Content-Length: {len(response_bytes)}\r\n\r\n"
                        writer.write(header.encode("utf-8") + response_bytes)
                        await writer.drain()
                else:
                    # Try parsing as raw JSON (some clients don't use headers)
                    try:
                        request = json.loads(buffer.decode("utf-8"))
                        buffer = b""

                        response = await handle_jsonrpc(request)
                        if response is not None:
                            response_bytes = json.dumps(response).encode("utf-8")
                            writer.write(response_bytes + b"\n")
                            await writer.drain()
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        break

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Server error: {e}")
            continue

    logger.info("StateWeave MCP Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
