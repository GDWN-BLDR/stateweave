# Board Session Output Templates

## Full Session Format

```markdown
# 🏛️ BOARD SESSION: [DATE]

## 🚨 EXECUTIVE SUMMARY
**Verdict:** [GREEN / YELLOW / RED]
**Consensus:** [One brutal sentence summing up the state of the project]

---

## ⚡ COMPLIANCE BATTERY (Step 0)

| # | Gate | Status | Mode |
|---|------|--------|------|
| 1 | Schema Integrity | ✅/❌ | BLOCK |
| 2 | Adapter Contract | ✅/❌ | BLOCK |
| 3 | Serialization Safety | ✅/❌ | BLOCK |
| 4 | Encryption Compliance | ✅/❌ | BLOCK |
| 5 | MCP Protocol | ✅/❌ | BLOCK |
| 6 | Import Discipline | ✅/❌ | BLOCK |
| 7 | Logger Naming | ✅/❌ | BLOCK |
| 8 | Test Coverage Gate | ✅/❌ | BLOCK |
| 9 | File Architecture | ✅/⚠️ | WARN |
| 10 | Dependency Cycles | ✅/❌ | BLOCK |

**SSOT Scan:** [COMPLIANT / VIOLATION]

---

## 📋 DOCUMENT MAINTENANCE (Step 0.5)

| Document | Owner | Last Verified | Status |
|----------|-------|---------------|--------|
| (from MANIFEST.md) | | | ✅/⚠️ |

---

## 🗣️ MEMBER STATEMENTS

### 👔 THE ARCHITECT (Protocol Design)
**Status:** [Designing / Stable / Concerned]
**Schema Health:** [v1 stable? Breaking changes pending?]
**Framework Coverage:** [X/Y target frameworks adapted]
**Observation:** "[Critique of schema design decisions]"
**Directive:** [Schema or protocol evolution]

### 🛡️ THE GUARDIAN (Security)
**Risk Level:** [CRITICAL / ELEVATED / NOMINAL]
**Encryption Coverage:** [All state payloads encrypted? YES/NO]
**Veto Check:** [Did we pass "The Naked State" test? (no unencrypted transit)]
**Data Loss Audit:** [non_portable_warnings fully populated? YES/NO]
**Mandate:** [Security enforcement action]

### ⚙️ THE ENGINEER (Infrastructure)
**System Pulse:** [Strong / Arrhythmic / Flatline]
**UCE Status:** [X/10 gates PASS]
**Unification Laws:** [X/8 laws in compliance]
**CI/CD Health:** [Tests passing? Coverage thresholds met?]
**Debt Alert:** [Specific stability concern]

### 📣 THE ADVOCATE (Developer Experience)
**DX Grade:** [A to F]
**API Ergonomics:** [Can a developer use StateWeave in < 5 minutes?]
**Documentation:** [README current? Examples working?]
**Friction Points:** [Where do developers get stuck?]
**Directive:** [DX improvement]

### 🎯 THE STRATEGIST (Competitive Position)
**Market Position:** [Dominant / Competitive / Threatened]
**Adoption Metrics:** [GitHub stars, pip downloads, MCP registry presence]
**Competitive Intel:** [New entrants? Framework vendors building native?]
**Timeline Risk:** [Anthropic June 2026 MCP stateful roadmap status]
**Directive:** [Strategic action]

### 🧹 THE PERFECTIONIST (Code Quality)
**Code Grade:** [A to F]
**The "Smell":** [Ugliest piece of logic found]
**Logger Scan:** [All loggers follow stateweave.* convention? YES/NO]
**Test Coverage:** [Line coverage by module]
**Refactor Order:** [Immediate cleanup task]

---

## 🚀 THE MOONSHOT PROPOSAL
**Proponent:** [Member Name]
**Concept:** [Radical Idea]
**Alpha Thesis:** [Why this increases adoption, not just polish]

## 📋 BINDING RESOLUTIONS (ACTION ITEMS)
1. **[P0 - CRITICAL]** [Task] (Owner: [Persona])
2. **[P1 - HIGH]** [Task] (Owner: [Persona])
3. **[P2 - OPTIMIZATION]** [Task] (Owner: [Persona])
```

## Brief Mode (--brief)

For daily operations, use abbreviated output showing only RED/YELLOW items:

```markdown
# 🏛️ BOARD BRIEF: [DATE]
**Verdict:** [GREEN/YELLOW/RED]
**Compliance:** [X/10 gates PASS]

## ⚠️ FLAGGED ITEMS
- [Member]: [Issue] → [Action]

## 📋 CRITICAL ACTIONS
1. [P0/P1 items only]
```
