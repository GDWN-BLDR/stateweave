# Show HN: StateWeave – Open-source agent state portability across 10 frameworks

URL: https://github.com/GDWN-BLDR/stateweave

---

## First Author Comment (post immediately)

I built this because I kept losing agent state every time I moved between frameworks.

I had a LangGraph agent with 800+ messages of conversation history, working memory, and tool results. I needed to run it through CrewAI for multi-agent orchestration. The only option was to start over. All that accumulated knowledge — gone.

StateWeave serializes everything an agent knows into a universal format. Export from one framework, import into another. Conversation history, working memory, goals, tool results, trust parameters — all of it transfers.

Star topology — 10 adapters, not 45 translation pairs. Adding a new framework is one adapter implementation, instant compatibility with everything else.

It also ships as an MCP Server, so any MCP-compatible assistant can use export/import/diff as tools directly.

Some details that might interest this crowd:

- AES-256-GCM encryption + Ed25519 signing for state in transit
- PBKDF2 with 600K iterations (OWASP recommendation)
- Credential stripping — API keys are flagged and removed during export
- No pickle, no eval — JSON + Pydantic only (UCE enforces this)
- Delta transport for bandwidth-efficient sync
- CRDT-inspired merge for parallel agent handoffs

315 tests, Apache 2.0. Still early — would genuinely appreciate feedback, especially from anyone running multi-framework agent setups.

`pip install stateweave`
