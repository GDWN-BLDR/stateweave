# 🚀 Launch Playbook — Surface-by-Surface

> Research-backed. Every recommendation cites what actually worked.

---

## Rules Across All Surfaces

### How To Not Sound Like An LLM

These patterns instantly flag content as AI-generated. Avoid them.

| AI Pattern | Fix |
|-----------|-----|
| "In today's rapidly evolving landscape..." | Just start with the problem |
| "Game-changing", "Revolutionary", "Cutting-edge" | State what it does, let people decide |
| Perfect parallel structure in every point | Mix long and short sentences |
| Every paragraph is exactly 3 sentences | Vary length. One-liners are fine |
| "Here's why it matters:" | Just explain it |
| Emoji in every bullet | Use them sparingly or not at all |
| Lists of exactly 5 things | Lists can have 3 or 7 or 4 |
| "Whether you're a X or a Y..." | Pick one audience per post |
| No contractions | Use "I've", "can't", "doesn't" — people talk that way |
| No first-person opinion | Say "I think", "I was frustrated by", "this drove me crazy" |

### Tone Model: Ruff's Launch

Ruff (now 50K+ GitHub stars) launched with this HN title:

> "Show HN: Ruff – a fast Python linter written in Rust"

And the author's first comment called it a **"proof of concept"**. No hyperbole. No "revolutionary." Just: "here's a thing I built, it's fast, here's why." It was direct, technically interesting, and humble. That's the energy.

---

## Surface 1: Hacker News

### Research-Backed Strategy

| What Works | Source |
|-----------|--------|
| Titles under 55 chars get 24% more upvotes | Reddit analysis of 1000+ Show HN posts |
| "Open Source" in title → +38% points | Same study |
| "AI-Powered" in title → -15% points | Same study |
| Link to GitHub, not landing page | HN guidelines + community preference |
| First author comment with backstory is essential | YC official Show HN guidelines |
| GIFs/demos get 2.5x more replies | Show HN analysis |
| Tue/Wed 8-11am UTC is optimal | Multiple analyses |

### Title

```
Show HN: StateWeave – Open-source agent state portability across 10 frameworks
```
(74 chars — slightly over 55, but "Open Source" + specificity is worth it)

Backup:
```
Show HN: StateWeave – Move your AI agent between frameworks, keep its brain
```

### URL

Link to: `https://github.com/GDWN-BLDR/stateweave`

NOT the website. HN readers want to see the code.

### First Author Comment (Post immediately after submitting)

```
I built this because I kept losing agent state every time I moved between
frameworks.

I had a LangGraph agent with 800+ messages of conversation history, working
memory, and tool results. I needed to run it through CrewAI for multi-agent
orchestration. The only option was to start over. All that accumulated
knowledge — gone.

StateWeave serializes everything an agent knows into a universal format.
Export from one framework, import into another. Conversation history, working
memory, goals, tool results, trust parameters — all of it transfers.

Star topology — 10 adapters, not 45 translation pairs. Adding a new
framework is one adapter implementation, instant compatibility with
everything else.

It also ships as an MCP Server, so any MCP-compatible assistant can use
export/import/diff as tools directly.

Some details that might interest this crowd:
- AES-256-GCM encryption + Ed25519 signing for state in transit
- PBKDF2 with 600K iterations (OWASP recommendation)
- Credential stripping — API keys are flagged and removed during export
- No pickle, no eval — JSON + Pydantic only (UCE enforces this)
- Delta transport for bandwidth-efficient sync
- CRDT-inspired merge for parallel agent handoffs

315 tests, Apache 2.0. Still early — would genuinely appreciate feedback,
especially from anyone running multi-framework agent setups.

pip install stateweave
```

### Why This Works
- Starts with personal frustration, not a pitch
- Specific numbers (800+ messages, 10 adapters, 315 tests) — not vague promises
- Technical details for the HN crowd (AES params, PBKDF2 iterations, "no pickle")
- Calls it "still early" — humble, invites feedback
- No buzzwords, no superlatives, no "game-changing"
- Ends with the install command, not a marketing URL

### Timing
- **Post on Tuesday or Wednesday**
- **Between 8-11 AM UTC** (3-6 AM EST, midnight-3 AM PST)
- Have 3-5 genuine friends/colleagues ready to check it out and comment if they find it interesting
- Stay online and respond to every comment for 4+ hours

---

## Surface 2: Reddit

### Subreddit Strategy

| Subreddit | Audience | Approach |
|-----------|----------|----------|
| r/LangChain | LangGraph users | Solve their specific migration pain |
| r/MachineLearning | ML researchers/engineers | Frame as infrastructure contribution |
| r/LocalLLaMA | Local model enthusiasts | Cloud-to-local handoff use case |
| r/Python | Python developers | Focus on the library itself |

### Key Rules
- Don't post to all subreddits on the same day — spread over a week
- Each post must be genuinely tailored, not a copy-paste
- Don't use the word "announce" — Reddit users hate announcements
- Engage in the comments, don't just post and leave
- If you've been active in the subreddit before, mention it

### r/LangChain Post

**Title:** `Built a tool to export LangGraph agent state to CrewAI/MCP/AutoGen without losing anything`

**Body:**

```
Been using LangGraph for a while and kept running into the same problem —
whenever I needed to move agent state to a different framework, the only
option was basically starting over.

The specific case that pushed me to build this: I had a research agent with
months of accumulated context. Needed to run it through CrewAI for a
multi-agent workflow. Couldn't bring anything along.

StateWeave is a state serializer — it takes everything an agent knows
(conversation history, working memory, goal tree, tool results) and
converts it to a universal format that any adapter can read back.

    pip install stateweave

Works with LangGraph, MCP, CrewAI, AutoGen, DSPy, and 5 others. Each
framework only needs one adapter, and that gives you portability to all
9 others (star topology instead of N² translations).

GitHub: https://github.com/GDWN-BLDR/stateweave

Open source, Apache 2.0, 315 tests. Still early so very open to feedback —
especially interested if anyone else has solved this differently.
```

### r/MachineLearning Post

**Title:** `[P] Cross-framework state portability for AI agents (10 adapters, Apache 2.0)`

**Body:**

```
StateWeave is a Python library that serializes AI agent cognitive state
into a framework-agnostic format. The core idea: each framework only needs
one adapter to translate to/from a universal schema, giving you N-1
migration paths instead of N² translation pairs.

The schema captures: conversation history, working memory, goal trees,
tool results, trust parameters, long-term/episodic memory, and an audit
trail. Non-portable elements (DB connections, OAuth tokens) are explicitly
flagged with severity, data loss impact, and remediation guidance — no
silent data loss.

Supports: LangGraph, MCP, CrewAI, AutoGen, DSPy, LlamaIndex, OpenAI
Agents, Haystack, Letta, Semantic Kernel.

Security: AES-256-GCM encryption, Ed25519 signing, PBKDF2 key derivation,
automatic credential stripping. JSON + Pydantic deserialization only (no
pickle/eval).

v0.3.0 adds delta transport (send only changes) and CRDT-inspired merge
for parallel agent state reconciliation.

pip install stateweave
GitHub: https://github.com/GDWN-BLDR/stateweave
```

### r/LocalLLaMA Post

**Title:** `Move your cloud agent's brain to a local agent — StateWeave serializes full agent state across frameworks`

**Body:**

```
Use case that might interest this sub: cloud agent hits a VPN wall or
data restriction. Export its entire cognitive state — conversation history,
working memory, goals, everything — to a file. Spin up a local agent
with a local model, import the state. It picks up the exact train of
thought.

That's what StateWeave does. It's a state serializer that works across
10 frameworks (LangGraph, CrewAI, AutoGen, MCP, etc.). Everything is
AES-256-GCM encrypted in transit.

    pip install stateweave

Apache 2.0:  https://github.com/GDWN-BLDR/stateweave
```

### Why These Work
- Each targets a different pain point relevant to that subreddit
- Written in first person with specific scenarios
- No corporate language, no "we're excited to announce"
- Install command is casual, inline — not a CTA block
- Asks for feedback genuinely
- Short enough that people will actually read them

---

## Surface 3: Twitter/X

### Research-Backed Strategy

| What Works | What Doesn't |
|-----------|-------------|
| Hook tweet with a specific problem | "We're excited to launch..." |
| Code screenshots (not pasted text) | Walls of text |
| Single-tweet version for retweets | 15-tweet mega-threads |
| Tag framework creators if relevant | @-ing random influencers |
| Real numbers, not adjectives | "Blazing fast" / "incredibly powerful" |

### Approach: Short Thread (5 tweets max)

Long threads perform poorly for unknown accounts. Keep it tight.

**Tweet 1 (Hook — standalone shareable)**
```
Every time you move an AI agent between frameworks, it forgets
everything it learned.

I built an open-source tool to fix that.

pip install stateweave
```

**Tweet 2 (What it does)**
```
StateWeave exports your agent's full cognitive state — conversation
history, memory, goals, tool results — into a universal format.

Import it into any of 10 frameworks. Nothing lost.

LangGraph ↔ CrewAI ↔ AutoGen ↔ MCP ↔ DSPy + 5 more
```

**Tweet 3 (Technical hook for devs)**
```
Security:
- AES-256-GCM + Ed25519 signing
- Credential stripping (API keys never leave)
- No pickle, no eval — JSON + Pydantic only

315 tests. Apache 2.0.
```

**Tweet 4 (CTA)**
```
GitHub: github.com/GDWN-BLDR/stateweave
PyPI: pip install stateweave

If you've dealt with the pain of losing agent state when switching
frameworks, I'd love to hear how you solved it (or didn't)
```

### Why This Works
- 4 tweets, not 9 — respects attention span
- Tweet 1 works as a standalone — people can RT just that
- No "🚀" or "🔥" or "Here's a thread 🧵"
- Asks a genuine question in the CTA — invites replies
- Technical details for credibility without being exhaustive
- Doesn't tag anyone — earn attention, don't beg for it

---

## Surface 4: Blog Post (dev.to or personal blog)

### Strategy
- dev.to gets you indexed and into their community feed
- Title should be problem-focused, not product-focused
- The blog post is the long-form asset that everything else links to

### Title Options
```
The missing middleware layer for AI agents
```
or
```
Why your agent loses its brain when you switch frameworks
```

### Structure
1. Open with the specific frustration (800 messages lost)
2. Explain why this happens (each framework stores state differently)
3. Show the architecture (star topology diagram — include img)
4. Code example (copy-pasteable)
5. Links (GitHub, PyPI)
6. Don't end with a CTA — end with a question

---

## Sequencing & Timing

| Day | Action |
|-----|--------|
| **Day 0 (Tue/Wed)** | Post Show HN at 8-10 AM UTC. Stay online 4+ hours responding. |
| **Day 0 + 2 hours** | Tweet the 4-tweet thread. Link to HN thread in a reply, not main tweet. |
| **Day 1** | Post to r/LangChain |
| **Day 2** | Post to r/MachineLearning |
| **Day 3** | Post to r/LocalLLaMA |
| **Day 4** | Publish blog post on dev.to |
| **Day 5** | Post to r/Python (with link to blog post) |
| **Day 7** | Retweet original thread with any early feedback/stats |

### Critical Rules
- Never post the same text to two surfaces
- Never ask for upvotes anywhere
- Respond to EVERY comment on every platform for the first week
- If HN doesn't take off, you can repost in 2-3 weeks with "[v0.3.1]" or a new angle
- Share the HN thread link on Twitter, not your GitHub — this drives HN engagement specifically
