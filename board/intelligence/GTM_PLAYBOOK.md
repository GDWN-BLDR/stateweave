# 🎯 StateWeave GTM Playbook

**Last Updated**: 2026-03-13
**Owner**: Strategist (📣)
**Status**: Pre-Launch

---

## 1. Pricing Model

### Free Forever (Apache 2.0)

**Everything in this repository is free.** All adapters, serializer, encryption, diff engine, MCP server, UCE scanners — open source, forever.

**Rationale**: Open-source companies command **median $482M** in M&A vs $34M for proprietary (14x multiplier). Apache 2.0 specifically provides an explicit patent shield and maximum adoption velocity (no legal review friction). This is the Promptfoo/Traceloop/Bun playbook — all three were acquired in 2025-2026 as open-source projects.

### Enterprise Tier (Month 6-12, SaaS)

| Feature | Free (Open Source) | Enterprise |
|---------|:--:|:--:|
| All adapters (10 frameworks) | ✅ | ✅ |
| Universal Schema + Serializer | ✅ | ✅ |
| AES-256-GCM encryption | ✅ | ✅ |
| Diff engine + portability analyzer | ✅ | ✅ |
| MCP Server | ✅ | ✅ |
| UCE compliance scanners | ✅ | ✅ |
| **Fleet state management dashboard** | ❌ | ✅ |
| **EU AI Act compliance doc generator** | ❌ | ✅ |
| **Multi-tenant SSO / RBAC** | ❌ | ✅ |
| **Custom adapter development** | ❌ | ✅ |
| **Priority support SLA (4hr P1)** | ❌ | ✅ |
| **State migration audit reports** | ❌ | ✅ |
| **Hosted StateWeave Cloud** | ❌ | ✅ |

**Pricing target**: $500-2,000/mo per team (based on Promptfoo enterprise pricing precedent).

**Key principle**: Never gate core functionality. Enterprise features are exclusively fleet management, compliance reporting, and support. If a solo developer needs to migrate an agent's state, it's free. If a Fortune 500 company needs to manage 500 agents across 3 frameworks with audit reports for the EU AI Act, that's enterprise.

---

## 2. Distribution Channels

| Channel | Format | Discovery Mechanism | Priority |
|---------|--------|-------------------|----------|
| **PyPI** | `pip install stateweave` | Search, GitHub links, blog posts, README | P0 |
| **MCP Registry** | `mcp-server-stateweave` | Glama (19,136 servers), MCP ecosystem browsing | P0 |
| **GitHub** | Source + releases | GitHub Trending, stars, search | P0 |
| **Docker Hub** | `stateweave/mcp-server` | Enterprise deployment, docker-compose | P1 |
| **Conda** | `conda install stateweave` | Data science community | P2 |

### MCP Registry Strategy

The MCP ecosystem is our most important distribution channel after PyPI. As of March 2026:
- 19,136 MCP servers listed on Glama
- Growth: 100 (Nov 2024) → 4,000 (May 2025) → 19,136 (Mar 2026)
- Top category: Developer Tools (4,258 servers in Apr 2025)
- Official registry launched preview Sep 2025

**Action**: List on both Glama and the official MCP Registry on launch day. Include screenshots showing the export/import/diff tools in action.

---

## 3. Growth Strategy: 0 → 10K Stars

### Phase 1: Seed (0 → 100 users) — Week 4

**Goal**: Get the first 100 real users who have actually tried to migrate agent state.

| Action | Channel | Expected Impact |
|--------|---------|-----------------|
| "Show HN" post with demo GIF | Hacker News | 30-50 stars day 1 |
| Posts to r/LangChain, r/MachineLearning, r/LocalLLaMA | Reddit | 20-30 stars |
| Direct outreach to 10-20 devs who've posted about state migration pain | Discord/GitHub Issues | 10-20 power users |
| Tweet thread with code snippets | Twitter/X | 15-25 stars |
| List on MCP Registry + Glama | MCP ecosystem | 10-15 installs |

**The HN post title**: *"Show HN: StateWeave – Time-travel debugging for AI agents (checkpoint, rollback, diff across 10 frameworks)"*

**The hook**: When a 20-step autonomous workflow derails at step 15, your only option today is to restart from scratch. StateWeave gives you `git` for agent brains — checkpoint at any step, rollback, diff, branch. Plus AES-256-GCM encryption, Ed25519 signing, and cross-framework migration as a bonus.

### Phase 2: Community (100 → 1K users) — Month 1-2

| Action | Channel | Expected Impact |
|--------|---------|-----------------|
| "Cloud-to-Local Sandbox Escape" demo video (2 min) | YouTube + Twitter | 200-400 stars |
| Technical blog: "How StateWeave Maps LangGraph State to MCP" | Dev.to / Medium | 100-200 stars |
| PR to LangGraph docs: "State portability with StateWeave" | LangGraph repo | Community validation |
| PR to Awesome-MCP: add mcp-server-stateweave | GitHub | Discovery |
| LangChain/LangGraph Discord active presence | Discord | Community trust |
| CrewAI + AutoGen adapter launches → new framework communities | PyPI / GitHub | 150-300 stars per adapter launch |

### Phase 3: Mainstream (1K → 10K stars) — Month 3-12

| Action | Channel | Expected Impact |
|--------|---------|-----------------|
| Conference talk: "The Missing Middleware: Agent State Portability" | PyCon, AI Engineer Summit | 500-1K stars |
| Blog: "Building a Custom Adapter in 100 Lines" | Dev.to | Contributor pipeline |
| Letta `.af` import adapter | GitHub | Letta community crossover |
| A2A (Google) integration | GitHub | Google ecosystem validation |
| GitHub Sponsors + Open Collective | GitHub | Sustainability signal for enterprise |
| Enterprise pilot with 1-2 companies | Direct | Acquisition signal |

### Phase 4: Acquisition Readiness (10K → 15K stars) — Month 12-18

| Metric | Target | Why It Matters |
|--------|--------|----------------|
| GitHub stars | 10K-15K | Triggers acquisition interest (Bun: 82K → Anthropic acquired) |
| PyPI monthly downloads | 5M+ | Scale proof |
| Fortune 500 adoption | 25%+ | Enterprise validation (Promptfoo's benchmark for nine-figure exit) |
| Framework adapters | 10+ | Moat depth |
| Contributors | 50+ | Community health signal |

---

## 4. Content Calendar

### Launch Week

| Day | Content | Channel | Owner |
|-----|---------|---------|-------|
| Mon | "Show HN" post | Hacker News | Strategist |
| Mon | Tweet thread (8 tweets with code) | Twitter/X | Advocate |
| Tue | Reddit posts (r/LangChain, r/MachineLearning, r/LocalLLaMA) | Reddit | Advocate |
| Wed | Demo video: "Cloud-to-Local Sandbox Escape" (2 min) | YouTube + Twitter | Engineer |
| Thu | Blog: "Why Agent State Portability is the Missing Middleware" | Dev.to | Architect |
| Fri | List on MCP Registry + Glama | MCP ecosystem | Engineer |

### Month 1

| Week | Content | Channel |
|------|---------|---------|
| 2 | Blog: "How StateWeave Maps LangGraph State to MCP" | Dev.to |
| 3 | PR to LangGraph docs + Awesome-MCP | GitHub |
| 4 | Blog: "StateWeave vs SAMEP: Building on the Standard" | Dev.to |

### Month 2-3

| Week | Content | Channel |
|------|---------|---------|
| 5-6 | CrewAI adapter launch post | Twitter + Reddit |
| 7-8 | AutoGen adapter launch post | Twitter + Reddit |
| 9-10 | Blog: "Adding a New Framework Adapter in 100 Lines" | Dev.to |
| 11-12 | Conference talk proposal submissions | PyCon / AI Eng Summit |

---

## 5. Competitive Positioning

### One-Line Positioning Statements

| Competitor | Our Position |
|------------|-------------|
| **Letta `.af`** | "Letta proved the demand. We made it cross-framework." |
| **SAMEP** | "SAMEP is the paper. We're the implementation." |
| **SuperMemory MCP** | "SuperMemory manages user memories. We manage agent cognition." |
| **Building it yourself** | "Maintaining compatibility with competitors' state formats is something no lab wants to do internally." |

### Category Creation

We are NOT "agent memory management" — that's Mem0, Zep, SuperMemory.

We ARE **"`git` for agent brains"** — the agent time-travel debugger + security control plane — a category with zero production competitors.

The analogy: **`git` + Vault for agent brains.** `git` gives you version control. Vault gives you secrets management. StateWeave gives agents both — plus cross-framework portability.

---

## 6. Acquisition Logic

### Who Would Acquire StateWeave (and Why)

| Acquirer | Strategic Rationale | Urgency | Exit Range |
|----------|-------------------|---------|------------|
| **Anthropic** | MCP is stateless by design. StateWeave fills their gap. They could acquire to strengthen MCP ecosystem | HIGH — MCP stateful roadmap targets June 2026 | $5-50M |
| **Google** | A2A has task-level state but no cross-framework portability. StateWeave bridges agents INTO Google's ecosystem | HIGH — A2A vs MCP competition | $10-100M |
| **OpenAI** | OpenClaw needs to receive handoffs from cloud agents. StateWeave enables cloud→local migration | MEDIUM | $5-50M |
| **Meta** | Moltbook handles identity. StateWeave handles the cognitive state that identity refers to. Natural complement | MEDIUM | $5-50M |
| **LangChain** | Defensive — if StateWeave makes it easy to leave LangGraph, LangChain wants to own the migration layer | HIGH — defensive | $5-20M |

### M&A Readiness Checklist

- [x] Apache 2.0 license (14x M&A multiplier)
- [x] Clean codebase (UCE-enforced, 440+ tests, 10 adapters, 12 scanners)
- [x] No third-party code dependencies beyond standard libraries
- [ ] 10K-15K GitHub stars
- [ ] 5M+ monthly pip downloads
- [ ] 25%+ Fortune 500 adoption
- [ ] Defensive publication of core algorithms
- [ ] Metrics dashboard (adoption, framework breakdown, migration volume)
- [ ] Clean IP assignment documentation

### Key M&A Intelligence

- Open-source companies: **median $482M** in M&A vs $34M proprietary (14x multiplier)
- Anthropic acquired **Bun** after 82K stars + 7M monthly downloads (Dec 2025)
- OpenAI attempted to acquire **Windsurf** for $3B (collapsed); Google reverse-hired at $2.4B
- ServiceNow acquired **Traceloop** for $60-80M (March 2026, same category)
- OpenAI acquired **Promptfoo** at $86M valuation (March 2026)

---

## 7. Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| Anthropic builds native MCP state serialization by June 2026 | **HIGH** | Ship before June. Position as the community standard they adopt rather than compete with |
| LangGraph v2.0 breaks SerializerProtocol | Medium | Abstract away from protocol internals. Property-based tests catch schema drift automatically |
| Framework churn (LangGraph changed state schema 3x in 2025) | Medium | Adapter versioning. Each adapter targets a specific framework version range |
| Non-portable state causes data loss complaints | Medium | Explicit `non_portable_warnings[]`. Zero silent data loss policy |
| Enterprise security teams reject open-source state transfer | Low | AES-256-GCM encryption, SAMEP-derived access policies, Apache 2.0 license |

---

## 8. Success Metrics

### Week 4 (Launch)
- [ ] 100+ GitHub stars
- [ ] 500+ PyPI downloads
- [ ] Listed on MCP Registry
- [ ] 1+ blog post with 1K+ views

### Month 3
- [ ] 1K+ GitHub stars
- [ ] 10K+ PyPI monthly downloads
- [ ] 10 adapters stable (LG, MCP, CrewAI, AutoGen, DSPy, LlamaIndex, OpenAI Agents, Haystack, Letta, SK) ✅ **DONE**
- [ ] 5+ community contributors

### Month 12
- [ ] 10K+ GitHub stars
- [ ] 1M+ PyPI monthly downloads
- [ ] Featured in 2+ conference talks
- [ ] Enterprise pilot running

### Month 18
- [ ] 15K+ GitHub stars
- [ ] 5M+ PyPI monthly downloads
- [ ] 25%+ Fortune 500 penetration
- [ ] Acquisition conversations active
