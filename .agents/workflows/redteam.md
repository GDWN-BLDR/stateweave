---
description: Run a comprehensive red team audit of all StateWeave public surfaces
---

# /redteam — Red Team Audit

Run this workflow whenever you need to verify launch readiness, after major changes,
or before any public release. It has two phases: automated (deterministic, fast) and
human (persona-driven, judgment-based).

---

## Phase 1: Automated Scan

// turbo
1. Run the automated audit script:
```
python scripts/redteam_audit.py
```

2. Read the scorecard output. If there are **any ❌ FAIL results**, fix them immediately before proceeding.
   Loop: fix → re-run → until 0 failures.

3. Review any ⚠️ warnings and decide if they are acceptable or need fixes.

---

## Phase 2: Red Team Personas

Walk each of the 8 personas below through the relevant surface. Each persona has
a specific attack angle — do NOT skip any. For each persona, open the relevant
URL/file and evaluate from their perspective.

### Persona 1: Skeptical HN Commenter
- **Surface:** GitHub README first page
- **Attack:** "This was built in a weekend. Show me the tests that actually run against a real framework."
- **Check:** Does the README acknowledge limitations honestly? Is there proof (demo, test badges)?

### Persona 2: Framework Maintainer (LangGraph/CrewAI)
- **Surface:** `stateweave/adapters/langgraph_adapter.py`, integration tests
- **Attack:** "Your adapter doesn't actually import my framework. It's a dict translator."
- **Check:** Do the adapters conditionally import the framework? Is the distinction between schema-level and framework-level integration clear?

### Persona 3: Security Auditor
- **Surface:** `stateweave/encryption.py`, `stateweave/compliance/`
- **Attack:** "Is the crypto real? Are there any pickle/eval paths? Hardcoded secrets?"
- **Check:** AES-256-GCM with proper nonce? PBKDF2 iterations ≥ 600K? The automated scan covers grep but the auditor checks crypto correctness.

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
- **Rule:** Take a screenshot of hero, demo, frameworks table, and footer. Report any section that looks "meh."

### Persona 7: First-Time User
- **Surface:** `pip install stateweave`, `python examples/quickstart.py`
- **Attack:** "I followed the README and it didn't work."
- **Check:** Does the install command work in a clean environment? Does the quickstart produce the expected output?

### Persona 8: Journalist / Analyst
- **Surface:** `content/blog_post.md`, `content/hn_post.md`, website
- **Attack:** "The numbers don't add up. The blog says X but the website says Y."
- **Check:** Cross-reference every number across all surfaces. Framework count, test count, CLI count, adapter names must match everywhere.

---

## Phase 3: Cross-Surface Consistency Matrix

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

## Phase 4: Write Report

Write the findings to `breakdown/red_team_analysis.md` with:
- Automated scan scorecard (paste output)
- Per-persona findings (what passed, what failed)
- Consistency matrix (filled in)
- Verdict: 🟢 LAUNCH READY / 🟡 READY WITH CAVEATS / 🔴 NOT READY

Commit the report:
```
git add -f breakdown/red_team_analysis.md
git commit -m "docs: red team analysis vN — [date]"
```

---

## Quick Reference

- **Automated scan only:** `python scripts/redteam_audit.py`
- **Full /redteam:** Follow all 4 phases above
- **After fixes:** Re-run Phase 1 to verify, then update the report
