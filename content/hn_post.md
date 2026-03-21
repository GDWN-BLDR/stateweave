# Show HN: StateWeave – git for agent brains

URL: https://github.com/GDWN-BLDR/stateweave

---

## First Author Comment (post immediately)

I've been learning about AI agent frameworks — LangGraph, CrewAI,
AutoGen, MCP — and kept finding the same complaints in communities and
issue trackers: once your agent accumulates real knowledge on one
framework, it's stuck there. Switch frameworks and you start over.

I wanted to build something useful in open source, and this seemed like
a real gap nobody had filled. So I built StateWeave — think `git` for
agent brains.

The core idea: serialize everything an agent knows (conversation history,
working memory, goals, tool results) into a universal schema. One
adapter per framework, star topology — 10 adapters give you portability
across all 10 without N² translation pairs.

```python
from stateweave import LangGraphAdapter, MCPAdapter

payload = LangGraphAdapter().export_state("my-agent")
MCPAdapter().import_state(payload)
```

Because everything goes through a versioned schema, you also get state
versioning for free: checkpoint, rollback, diff, branch. Like `git log`
for your agent's cognitive state.

Some details that might interest this crowd:
- AES-256-GCM encryption + Ed25519 signing for state in transit
- PBKDF2 with 600K iterations (OWASP recommendation)
- Credential stripping — API keys are flagged and removed during export
- No pickle, no eval — JSON + Pydantic only (compliance engine enforces this)
- Delta transport for bandwidth-efficient sync
- A2A protocol bridge for inter-agent state transfer

Also ships as an MCP Server, so any MCP-compatible assistant can use
export/import/diff as tools directly. CLI with 25+ commands.

730+ tests, Apache 2.0. This is genuinely a learning project that
grew into something I think might be useful — would really appreciate
feedback, especially from anyone who's needed to move agent state
between frameworks.

`pip install stateweave`
