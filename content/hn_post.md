# Show HN: StateWeave – git for agent brains

URL: https://github.com/GDWN-BLDR/stateweave

---

## First Author Comment (post immediately)

I've been learning about AI agent frameworks — LangGraph, CrewAI,
AutoGen, MCP — and kept seeing the same complaints in communities and
issue trackers: people lose all their agent's accumulated context when
they switch frameworks, and debugging complex multi-step workflows is
brutal because you can't just "undo" a bad step.

I wanted to build something useful in open source, and this seemed like
a real gap nobody was filling. So I built StateWeave — think `git` for
agent brains.

The core idea: serialize everything an agent knows (conversation history,
working memory, goals, tool results) into a universal schema. From
there you get two things for free:

1. **Time travel** — checkpoint, rollback, diff, and branch agent state.
   Content-addressable storage with SHA-256 and parent hash chains.
   When step 15 of 20 goes wrong, rewind instead of restarting.

2. **Cross-framework portability** — export from LangGraph, import into
   CrewAI (or any of 10 supported frameworks). Star topology: N
   adapters, not N² translations.

Some details that might interest this crowd:
- AES-256-GCM encryption + Ed25519 signing for state in transit
- PBKDF2 with 600K iterations (OWASP recommendation)
- Credential stripping — API keys are flagged and removed during export
- No pickle, no eval — JSON + Pydantic only (compliance engine enforces this)
- Delta transport for bandwidth-efficient sync
- A2A protocol bridge for inter-agent state transfer

Also ships as an MCP Server, so any MCP-compatible assistant can use
export/import/diff as tools directly. CLI with 14 commands.

440+ tests, Apache 2.0. This is genuinely a learning project that
grew into something I think might be useful — would really appreciate
feedback, especially from anyone running multi-framework agent setups
or struggling with agent debugging.

`pip install stateweave`
