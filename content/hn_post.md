# Show HN: StateWeave – git for agent brains

URL: https://github.com/GDWN-BLDR/stateweave

---

## First Author Comment (post immediately)

Here's the problem that got me started: when a 20-step autonomous agent
workflow derails at step 15, the only option is usually to restart from
scratch. That's expensive, slow, and you lose all the context the agent
built up.

I wanted `git` for agent brains — checkpoint at any step, rollback to a
known-good state, diff to see exactly what changed, and branch to fork
an agent's cognition for experiments. That's StateWeave.

Along the way, the architecture naturally led to cross-framework
portability. Since every agent's state gets translated to a universal
schema, you can export from LangGraph and import into CrewAI (or any of
10 supported frameworks) as a free bonus.

Supports: LangGraph, MCP, CrewAI, AutoGen, DSPy, LlamaIndex, OpenAI
Agents, Haystack, Letta, Semantic Kernel. The LangGraph adapter works
directly with real StateGraph + MemorySaver (integration tests against
the actual framework, not mocks).

**Time Travel** — checkpoint, rollback, branch, and diff agent state.
Content-addressable storage with SHA-256 hashing and parent hash chains.
Think `git log` but for your agent's cognitive state.

**Security** — AES-256-GCM encryption, Ed25519 signing, PBKDF2 key
derivation with 600K iterations, credential stripping on export. No pickle
or eval anywhere — JSON + Pydantic only. Compliance engine with 12
automated scanners enforces this across the codebase.

**Smart Checkpointing** — three strategies: checkpoint every N steps,
checkpoint only on significant state changes (delta-threshold), or
manual-only for hot paths. Plus timing instrumentation so you can
measure overhead.

**A2A Bridge** — integration with Google's Agent2Agent protocol. A2A
defines how agents talk to each other; StateWeave adds what they know.
When one agent hands off to another, the full cognitive state goes with it.

**Zero-Loss Round-Trips** — framework-specific state (like LangGraph's
internal channels) is preserved in `framework_specific` instead of being
silently dropped. Same-framework round-trips are truly lossless.

CLI with 14 commands (export, import, diff, checkpoint, rollback, history,
scan, etc.). Also ships as an MCP Server. Apache 2.0.

Still early and there's a lot more to do — genuinely looking for feedback
and anyone who wants to help build out deeper framework integrations.

`pip install stateweave`
