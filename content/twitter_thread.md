# Twitter Thread (4 tweets)

## Tweet 1 (Hook — works as standalone RT)

I've been learning agent frameworks and kept seeing the same complaint: when a 20-step workflow breaks at step 15, you restart from scratch.

So I built an open-source tool to fix it — checkpoint, rollback, diff, branch agent state across 10 frameworks.

`git` for agent brains.

pip install stateweave

## Tweet 2 (What it does)

What StateWeave gives you:

🔍 git-like versioning for agent state — checkpoint any step, rollback, diff
🔒 AES-256-GCM encryption + Ed25519 signing
⚡ Smart checkpointing — only save on significant changes
📊 Cross-framework portability — export LangGraph, import into CrewAI

No pickle. No eval. JSON + Pydantic only.

## Tweet 3 (Technical depth)

The architecture: one universal schema, 10 adapters. Star topology.

Adding a framework = one adapter. Instant portability to all others.

Plus: A2A protocol bridge, 14 CLI commands, MCP Server, compliance engine with 12 scanners. Apache 2.0.

## Tweet 4 (CTA + genuine question)

GitHub: github.com/GDWN-BLDR/stateweave

Built this as a learning project that turned into something I think might
actually be useful. Still early.

What's your current approach when an agent workflow goes sideways
at step 15?
