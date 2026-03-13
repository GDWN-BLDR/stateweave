# Twitter Thread (4 tweets)

## Tweet 1 (Hook — works as standalone RT)

Every time you move an AI agent between frameworks, it forgets everything it learned.

I built an open-source tool to fix that.

pip install stateweave

## Tweet 2 (What it does)

StateWeave exports your agent's full cognitive state — conversation history, memory, goals, tool results — into a universal format.

Import it into any of 10 frameworks. Nothing lost.

LangGraph ↔ CrewAI ↔ AutoGen ↔ MCP ↔ DSPy + 5 more

## Tweet 3 (Technical credibility)

Security details:
- AES-256-GCM + Ed25519 signing
- Credential stripping (API keys never leave)
- No pickle, no eval — JSON + Pydantic only

315 tests. Apache 2.0.

## Tweet 4 (CTA + genuine question)

GitHub: github.com/GDWN-BLDR/stateweave
PyPI: pip install stateweave

If you've dealt with the pain of losing agent state when switching frameworks, I'd love to hear how you solved it (or didn't)
