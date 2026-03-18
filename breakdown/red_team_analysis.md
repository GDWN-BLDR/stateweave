# Red Team Analysis v3 — 2026-03-18

## Automated Scan Scorecard

| Metric | Result |
|--------|--------|
| **Total checks** | 47/47 ✅ |
| **Failures** | 0 |
| **Warnings** | 0 |
| **Time-to-value** | 9.1s (target: <90s) |
| **Verdict** | 🟢 LAUNCH READY |

---

## Per-Persona Findings

### 1. Skeptical HN Commenter — ✅ PASS
- Demo GIF exists with real LangGraph framework output (not mocks)
- 442 tests verified by scan
- README uses honest framing ("git for agent brains"), no hype
- `real_framework_demo.py` uses actual `langgraph` + `langchain-core` packages

### 2. Framework Maintainer — ✅ PASS
- `LangGraphAdapter` conditionally imports `langgraph.graph.StateGraph` and `langchain_core.messages`
- Falls back to dict-based mode when framework not installed (graceful degradation)
- `_require_framework()` helper provides actionable error messages
- Adapter tier system (`AdapterTier` enum: TIER_1, TIER_2, COMMUNITY) clearly documented

### 3. Security Auditor — ✅ PASS
- AES-256-GCM via `cryptography.hazmat.primitives.ciphers.aead.AESGCM` ✓
- PBKDF2 with SHA-256, 600,000 iterations (OWASP recommended) ✓
- Ed25519 signing via `cryptography.hazmat.primitives.asymmetric.ed25519` ✓
- Unique 96-bit nonce per encryption operation ✓
- No `pickle`, `eval`, `yaml.load` in source ✓
- No hardcoded API keys or secrets ✓

### 4. Competitor — ✅ PASS
- Website shows tier labels: 🟢 Tier 1 = Core, 🟡 Tier 2 = Maintained, 🔵 Community = Best-effort
- Adapter count (10) matches code, README, website, GTM content
- Claims not inflated — "440+ tests" and code has 442

### 5. Copy Editor — ✅ PASS
- Canonical tagline consistent everywhere: "git for agent brains"
- No stale phrases ("cognitive state serializer" etc.) found in any public file
- README tone is technical but approachable, not buzzword-heavy

### 6. UX Designer — ✅ PASS
- Website has dark theme, clear visual hierarchy, gradient headers
- OG image returns 200 and is `image/png`
- Demo embedded on website
- Framework table with tier indicators is visually clear
- Security section lists crypto specs with labeled cards

### 7. First-Time User — ✅ PASS
- `pip install stateweave` works in 3.8s
- `python examples/full_demo.py` runs successfully in 3.2s
- Total time-to-value: 9.1s
- Demo output contains all expected markers (7/7 steps)
- Clear "try it yourself" instructions in README

### 8. Journalist / Analyst — ✅ PASS
- All numbers consistent across surfaces (see matrix below)
- Test count: Code=442, GTM surfaces say "440+" — accurate
- Framework count: 10 everywhere

### 9. SMB Customer — ✅ PASS
- Time to first working demo: 9.1s (< 60s target ✓)
- Apache 2.0 license clearly stated (badge in README, LICENSE file, PyPI, GitHub)
- Open source — no hidden pricing or "Contact Sales"
- README has clear next-steps: quickstart → full demo → MCP server

### 10. Mid-Market Customer — ✅ PASS
- 442 tests, CI badge in README
- CONTRIBUTING.md exists
- Docs directory with multiple guides
- Tier system lets a manager communicate stability expectations to VP

### 11. Enterprise Customer — ✅ PASS
- Apache-2.0 license — no ambiguity about commercial use
- SECURITY.md with vulnerability disclosure process
- CHANGELOG.md exists with semantic versioning (0.3.3)
- Encryption is real AES-256-GCM, not homebrew crypto
- State never leaves customer infra (runs locally, Docker deployable)
- Audit trail built into every `StateWeavePayload`

---

## Consistency Matrix

| Claim | README | Website | PyPI | GitHub | llms.txt | HN Post | Reddit | Twitter |
|-------|--------|---------|------|--------|----------|---------|--------|---------|
| Tagline | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Framework count | 10 | 10 | 10 | 10 | 10 | 10 | 10 | 10 |
| Test count | 440+ | — | — | — | — | 440 | 440 | 440 |
| Version | 0.3.3 | — | 0.3.3 | — | — | — | — | — |
| GitHub URL | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| License | Apache 2.0 | — | Apache 2.0 | Apache 2.0 | — | — | — | — |

**All cells match — no mismatches.**

---

## Verdict

🟢 **LAUNCH READY**

- 47/47 automated checks pass
- All 11 personas pass with no critical findings
- Consistency matrix is clean across all surfaces
- Time-to-value is 9.1s (target was <90s)
- Real framework integration demo now exists
