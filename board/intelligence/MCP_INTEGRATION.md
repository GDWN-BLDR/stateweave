# MCP Integration Map

**Owner:** Engineer / Architect
**Last Updated:** 2026-03-13
**Status:** ✅ FEASIBILITY CONFIRMED

---

## MCP Protocol State Architecture

### Core Design: Inherently Stateless
MCP (Model Context Protocol) is **stateless at the protocol level**. State management is delegated to individual server implementations. This means:

- No standardized state format across MCP servers
- Server state is implementation-specific (Redis, SQLite, in-memory, etc.)
- Session context travels via JSON-RPC `_meta` fields

### StateWeave's MCP Strategy
Since MCP has no single "agent state" to export, StateWeave operates at the **MCP client level**:

1. **Aggregate** state from multiple MCP server interactions
2. **Capture** conversation context, tool call history, resource reads
3. **Package** into Universal Schema format

---

## JSON-RPC Message Mapping

### MCP → Universal Schema

| MCP Concept | Universal Schema Field |
|------------|----------------------|
| Client session context | `cognitive_state.working_memory` |
| Conversation messages | `cognitive_state.conversation_history` |
| Tool call results | `cognitive_state.tool_results_cache` |
| Resource reads cache | `cognitive_state.working_memory.resources` |
| Prompt template state | `cognitive_state.working_memory.active_prompts` |
| Server capabilities | `metadata.framework_capabilities` |

### MCP Tool Call History → Audit Trail
```json
{
    "audit_trail": [
        {
            "timestamp": "2026-03-13T10:30:00Z",
            "action": "tool_call",
            "details": {
                "server": "mcp-server-filesystem",
                "tool": "read_file",
                "arguments": {"path": "/data/report.csv"},
                "result_hash": "sha256:abc123..."
            }
        }
    ]
}
```

---

## MCP Server Distribution

### StateWeave as an MCP Server
StateWeave itself ships as an MCP Server, giving any MCP-compatible agent access to:

| Primitive | Exposed As |
|-----------|-----------|
| **Tools** | `export_agent_state`, `import_agent_state`, `diff_agent_states` |
| **Resources** | Schema docs, migration history, live snapshots |
| **Prompts** | Backup templates, migration guides |

### Server Discovery
- Listed on MCP Registry (19,136+ servers as of March 2026)
- Server Card (`.well-known`) for structured capability discovery
- Supports stdio and SSE transports

---

## Security: JSON-RPC as RCE Sanitization

### Built-in Security Benefit
MCP's JSON-RPC translation provides inherent RCE sanitization:
- All data passes through JSON serialization/deserialization
- Binary payloads are Base64-encoded
- No arbitrary code execution through state payloads
- CVE-2025-64439 attack surface is stripped by protocol constraint

### StateWeave Encryption Layer
On top of MCP's protocol-level safety:
- AES-256-GCM encryption for state payloads in transit
- Key exchange via `EncryptionFacade`
- Nonce-per-operation to prevent replay attacks

---

## Non-Portable Elements (MCP-Specific)

| Element | Reason | Warning Severity |
|---------|--------|-----------------|
| Server connection state | Live TCP/WebSocket handles | WARN |
| SSE event stream position | Stream cursor is server-specific | WARN |
| OAuth tokens | Security-sensitive, should not transfer | CRITICAL |
| Server-specific `_meta` | Implementation detail | INFO |
