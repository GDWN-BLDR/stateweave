# Twitter Thread (4 tweets)

## Tweet 1 (Hook — works as standalone RT)

Your AI agent accumulates real knowledge — then you need to switch frameworks and it all disappears.

I built an open-source tool that exports everything your agent knows and imports it into any of 10 frameworks.

git for agent brains.

pip install stateweave

## Tweet 2 (What it does)

StateWeave serializes your agent's full cognitive state — conversation history, memory, goals, tool results — into a universal schema.

LangGraph → CrewAI → AutoGen → MCP → DSPy + 5 more.

One adapter per framework. Star topology, not N² translations.

## Tweet 3 (Security + quality)

Security:
- AES-256-GCM encryption + Ed25519 signing
- Credential stripping (API keys never leave)
- No pickle, no eval — JSON + Pydantic only

Plus: state versioning with checkpoint, rollback, diff, branch.

730+ tests. Apache 2.0.

## Tweet 4 (CTA + genuine question)

GitHub: github.com/GDWN-BLDR/stateweave

Built this as a learning project that turned into something I think might actually be useful. Still early.

Have you ever needed to move an agent's accumulated knowledge to a different framework?
