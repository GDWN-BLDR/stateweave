# 🧶 Cloud-to-Local Sandbox Escape

**A LangGraph cloud agent hits a VPN wall. StateWeave rescues its brain.**

## The Scenario

Your cloud-hosted LangGraph agent is researching internal documents. It hits a VPN-protected resource it can't access from the cloud. Without StateWeave, you'd start over with a local agent — losing everything the cloud agent learned.

With StateWeave:

```
Cloud Agent (LangGraph)          Local Agent (MCP)
┌─────────────────────┐          ┌─────────────────────┐
│ 8 messages           │  ──────> │ 8 messages           │
│ 4 research findings  │  export  │ 4 research findings  │
│ 3 active goals       │  ──────> │ 3 active goals       │
│ confidence: 0.87     │          │ confidence: 0.87     │
└─────────────────────┘          └─────────────────────┘
         ▲                                │
         │                                ▼
    VPN blocked                    VPN accessible
```

The local agent picks up the exact train of thought, accesses the VPN data, and — if needed — sends results back to the cloud agent. The boundary between cloud and local AI is erased.

## Run

```bash
pip install stateweave
python sandbox_escape.py
```

## What It Demonstrates

1. **Export** — Cloud agent's full cognitive state (messages, memory, goals, confidence)
2. **Encrypt** — AES-256-GCM authenticated encryption for transport
3. **Transport** — Simulated cloud → local transfer
4. **Decrypt + Import** — Local agent receives and validates state
5. **Diff** — Verify zero data loss between cloud and local
6. **Rollback** — Time travel back to pre-migration state if needed

## Why This Matters

Without portability, agents are prisoners of their deployment environment. StateWeave makes agent intelligence portable across:
- Cloud ↔ Local (this demo)
- Framework ↔ Framework (LangGraph ↔ MCP ↔ CrewAI ↔ AutoGen ↔ ...)
- Team ↔ Team (encrypted handoffs)
