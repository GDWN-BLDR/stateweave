---
description: Run a comprehensive red team audit of all StateWeave public surfaces
---

# /redteam — Red Team Audit v3

Run this workflow whenever you need to verify launch readiness, after major changes,
or before any public release. It has seven phases: automated scan, adversarial testing,
supply chain audit, persona walk, differential regression, accessibility, and reporting.

---

## Phase 1: Automated Scan

// turbo
1. Run the automated audit script:
```
python scripts/redteam_audit.py --skip-browser --skip-supply-chain
```

2. Read the scorecard output. If there are **any ❌ FAIL results**, fix them immediately before proceeding.
   Loop: fix → re-run → until 0 failures.

3. Review any ⚠️ warnings and decide if they are acceptable or need fixes.

---

## Phase 2: Adversarial Testing (P0)

// turbo
1. Run the adversarial test suite:
```
python -m pytest tests/redteam/ -v --tb=short -x
```

2. If any tests fail, they represent **real security or resilience bugs**. Fix them before proceeding.

The adversarial suite covers:
- **Schema fuzzing** — malformed JSON, deserialization attacks, depth/size bombs, Unicode edge cases
- **Encryption attacks** — nonce reuse, bit-flip sweeps, PBKDF2 edge cases, Ed25519 signature attacks
- **CLI injection** — shell metacharacters, path traversal, symlink attacks, resource exhaustion
- **REST API attacks** — oversized bodies, method confusion, CORS validation, response leak detection
- **Chaos/fault injection** — mid-checkpoint corruption, disk full, concurrent writes, clock skew

---

## Phase 3: Supply Chain Audit

// turbo
1. Run the supply chain audit:
```
python scripts/supply_chain_audit.py
```

2. Review for:
   - CVEs in dependencies (via `pip audit`)
   - License compatibility issues (copyleft vs Apache-2.0)
   - Floating dependency pins without upper bounds
   - Typosquat package names
   - Transitive dependency bloat

---

## Phase 4: Red Team Personas

Walk each of the 11 personas below through the relevant surface. Each persona has
a specific attack angle — do NOT skip any. For each persona, open the relevant
URL/file and evaluate from their perspective.

### Persona 1: Skeptical HN Commenter
- **Surface:** GitHub README first page
- **Attack:** "This was built in a weekend. Show me the tests that actually run against a real framework."
- **Check:** Does the README acknowledge limitations honestly? Is there proof (demo, test badges)?

### Persona 2: Framework Maintainer (LangGraph/CrewAI)
- **Surface:** `stateweave/adapters/langgraph_adapter.py`, integration tests
- **Attack:** "Your adapter doesn't actually import my framework. It's a dict translator."
- **Check:** Do the adapters conditionally import the framework? Does import produce an actionable `AdapterError` when framework is missing?

### Persona 3: Security Auditor
- **Surface:** `stateweave/core/encryption.py`, `stateweave/compliance/`, adversarial test results
- **Attack:** "Is the crypto real? Are there any pickle/eval paths? Hardcoded secrets?"
- **Check:** AES-256-GCM with proper nonce? PBKDF2 iterations ≥ 600K? The adversarial tests pass.

### Persona 4: Competitor (Langchain, Pydantic, etc.)
- **Surface:** PyPI listing, website claims
- **Attack:** "These claims are inflated. 10 adapters but only 4 are Tier 1."
- **Check:** Are tier distinctions clearly communicated? Does the website honestly label Community vs Tier 1?

### Persona 5: Copy Editor (Grammar + Tone)
- **Surface:** All `content/*.md`, README, website HTML
- **Check:** Typos, passive voice, buzzword density, inconsistent capitalization, developer cringe factor.
- **Rule:** If a sentence makes you wince, rewrite it.

### Persona 6: UX Designer
- **Surface:** Website (load in browser, scroll every section)
- **Check:** Visual hierarchy, spacing, color contrast, mobile responsiveness, call-to-action clarity, demo visibility.
- **Rule:** Check screenshots in `breakdown/screenshots/` from the accessibility audit.

### Persona 7: First-Time User
- **Surface:** `pip install stateweave`, `python examples/quickstart.py`
- **Attack:** "I followed the README and it didn't work."
- **Check:** Does the install work? Does the demo print "next steps"? Is `--help` concise (≤50 lines)?

### Persona 8: Journalist / Analyst
- **Surface:** `content/blog_post.md`, `content/hn_post.md`, website
- **Attack:** "The numbers don't add up. The blog says X but the website says Y."
- **Check:** Cross-reference every number across all surfaces. Framework count, test count, CLI count, adapter names must match everywhere.

### Persona 9: SMB Customer (Solo Founder / Small Team)
- **Surface:** Website hero + Quick Start, README "See it working", PyPI install
- **Attack:** "I have 2 devs and no time. Can I get value in 15 minutes?"
- **Check:** TTV < 60s? Getting-started doc exists? Clear open-source licensing?

### Persona 10: Mid-Market Customer (Engineering Manager, 10–50 eng)
- **Surface:** Website (Frameworks table, Security section, FAQ), docs, CONTRIBUTING.md
- **Attack:** "Can I mandate this as a standard? Where's the migration guide?"
- **Check:** Migration guide exists? CI badges are live? Test credibility > 400?

### Persona 11: Enterprise Customer (Platform Architect / Procurement)
- **Surface:** Security section, LICENSE, SECURITY.md, encryption code, compliance scanners
- **Attack:** "Our CISO needs to sign off. Show me your audit trail."
- **Check:** SECURITY.md has disclosure process? SBOM generation possible? Encryption real?

---

## Phase 5: Differential Regression

// turbo
1. Run the differential check:
```
python scripts/redteam_diff.py
```

2. Review for:
   - **New API surfaces** (exported symbols, CLI commands, REST endpoints) — each needs adversarial testing
   - **Test count drops** — are tests being deleted?
   - **New vs recurring failures** — is this a new bug or a known issue?

---

## Phase 6: Accessibility Audit

1. Run the accessibility audit (requires Playwright):
```
python scripts/accessibility_audit.py
```

2. Review:
   - Screenshots in `breakdown/screenshots/` at mobile/tablet/desktop
   - Core Web Vitals (LCP < 2.5s, CLS < 0.1)
   - axe-core accessibility violations

---

## Phase 7: Cross-Surface Consistency Matrix

After all personas have walked, verify this matrix. Every cell must be consistent:

| Claim             | README | Website | PyPI | HN Post | Twitter | Reddit | Blog | llms.txt |
|-------------------|--------|---------|------|---------|---------|--------|------|----------|
| Tagline           |        |         |      |         |         |        |      |          |
| Framework count   |        |         |      |         |         |        |      |          |
| Test count        |        |         |      |         |         |        |      |          |
| CLI command count |        |         |      |         |         |        |      |          |
| Version number    |        |         |      |         |         |        |      |          |
| GitHub URL        |        |         |      |         |         |        |      |          |
| License           |        |         |      |         |         |        |      |          |

Fill in each cell. Any mismatch is a fix-before-launch item.

---

## Phase 8: Write Report

Write the findings to `breakdown/red_team_analysis.md` with:
- Automated scan scorecard (paste output)
- Adversarial test results (paste pytest output)
- Supply chain audit results
- Per-persona findings (what passed, what failed)
- Differential regression analysis
- Accessibility audit results
- Consistency matrix (filled in)
- Verdict: 🟢 LAUNCH READY / 🟡 READY WITH CAVEATS / 🔴 NOT READY

Commit the report:
```
git add -f breakdown/red_team_analysis.md
git commit -m "docs: red team analysis vN — [date]"
```

---

## Quick Reference

- **Automated scan only (fast):** `python3 scripts/redteam_audit.py --quick --skip-browser --skip-supply-chain`
- **Full audit with all phases:** `python3 scripts/redteam_audit.py --personas`
- **Adversarial tests only:** `python -m pytest tests/redteam/ -v --tb=short`
- **Supply chain only:** `python3 scripts/supply_chain_audit.py`
- **Differential only:** `python3 scripts/redteam_diff.py`
- **Accessibility only:** `python3 scripts/accessibility_audit.py`
- **JSON output for CI:** `python3 scripts/redteam_audit.py --quick --json --no-history`
- **After fixes:** Re-run Phase 1 to verify, then update the report

### v3 Features (NEW)
- **Adversarial runtime fuzzing** — 5 test files with 100+ adversarial test cases across schema, encryption, CLI, REST API, and chaos scenarios
- **Supply chain audit** — CVE scan, license compatibility, pin verification, typosquat detection
- **Differential regression** — API surface tracking, test count monitoring, failure novelty analysis
- **Accessibility audit** — headless browser viewport tests, Core Web Vitals, axe-core a11y scanning
- **Smarter persona scoring** — real adapter imports, demo output analysis, CLI help conciseness, migration guide checks, SBOM capability
- **Enhanced CI gate** — two-job workflow (quick on every PR, full on release), artifact upload, merge blocking

### v2 Features
- **Auto consistency matrix** — extracts numbers from every surface and flags mismatches
- **Time-to-value test** — fresh venv install + demo in < 90s (requires Python ≥ 3.10)
- **Persona scorecards** — auto-scored 1-5 for 7 personas (HN, Security, Competitor, First-Time User, Journalist, SMB, MM, Enterprise)
- **Audit history** — appends to `breakdown/audit_history.jsonl`, shows trends vs previous run
- **CI integration** — `.github/workflows/redteam-audit.yml` runs on every push
