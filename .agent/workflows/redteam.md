---
description: Run a comprehensive red team audit of all StateWeave public surfaces
---

# /redteam — Red Team Audit

Run this workflow whenever you need to verify launch readiness, after major changes,
or before any public release. It has five phases: automated scan, live surface
verification, persona walk-throughs, consistency matrix, and report.

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

## Phase 1.5: Live Surface Verification (MANDATORY)

**Every public-facing URL must be loaded in a real browser and visually verified.**
The automated scan uses API calls and HTTP fetches — it does NOT render pages.
Personas judge what real users see, not API responses. Do NOT skip this phase.

### Surface 1: GitHub Repo Page
- **Open:** https://github.com/GDWN-BLDR/stateweave
- **Check:** README renders correctly, demo GIF loads and plays, badges (PyPI, CI, License, Python) all show green, star topology diagram renders, framework table is readable
- **Take a screenshot** of the hero section with demo GIF

### Surface 2: Website
- **Open:** https://stateweave.pantollventures.com
- **Check:** Page loads without errors, hero section visible, demo section visible, framework table with tier indicators renders, security section shows crypto specs, FAQ section works, mobile responsive (resize window to 375px)
- **Scroll every section** — top to bottom
- **Take screenshots** of: hero, demo, frameworks table, security, footer

### Surface 3: PyPI Listing
- **Open:** https://pypi.org/project/stateweave/
- **Check:** Description renders, version matches (`0.3.3` or current), links to GitHub work, license shows Apache 2.0, Python version classifiers correct
- **Take a screenshot** of the listing page

### Surface 4: Demo GIF on GitHub
- **Open:** https://raw.githubusercontent.com/GDWN-BLDR/stateweave/main/assets/demo.gif
- **Check:** GIF loads, plays, is readable (text not too small), shows real framework output (not mocks), duration is watchable (not 0.25s)

### Surface 5: OG Social Card Preview
- **Open:** https://www.opengraph.xyz/url/https://stateweave.pantollventures.com
  (or paste the URL into Twitter/Slack/Discord to see the card preview)
- **Check:** Title, description, and image render correctly for social sharing

### Surface 6: llms.txt
- **Open:** https://stateweave.pantollventures.com/llms.txt
- **Check:** Content loads, contains canonical tagline, properly formatted

### Verification Criteria
- If ANY surface fails to load, renders incorrectly, or shows stale content → **fix before proceeding**
- If the demo GIF doesn't play or is unreadable → **re-record before proceeding**
- If the website shows old content that doesn't match the repo → **redeploy before proceeding**

---

## Phase 2: Red Team Personas

Walk each of the 11 personas below through the relevant surface. Each persona has
a specific attack angle — do NOT skip any. For each persona, open the relevant
URL/file and evaluate from their perspective.

### Persona 1: Skeptical HN Commenter
- **Surface:** GitHub README first page (open in browser: https://github.com/GDWN-BLDR/stateweave)
- **Attack:** "This was built in a weekend. Show me the tests that actually run against a real framework."
- **Check:** Does the README acknowledge limitations honestly? Is there proof (demo, test badges)?

### Persona 2: Framework Maintainer (LangGraph/CrewAI)
- **Surface:** `stateweave/adapters/langgraph_adapter.py`, integration tests
- **Attack:** "Your adapter doesn't actually import my framework. It's a dict translator."
- **Check:** Do the adapters conditionally import the framework? Is the distinction between schema-level and framework-level integration clear?

### Persona 3: Security Auditor
- **Surface:** `stateweave/core/encryption.py`, `stateweave/compliance/`
- **Attack:** "Is the crypto real? Are there any pickle/eval paths? Hardcoded secrets?"
- **Check:** AES-256-GCM with proper nonce? PBKDF2 iterations ≥ 600K? The automated scan covers grep but the auditor checks crypto correctness.

### Persona 4: Competitor (Langchain, Pydantic, etc.)
- **Surface:** PyPI listing (open in browser: https://pypi.org/project/stateweave/), website claims
- **Attack:** "These claims are inflated. 10 adapters but only 4 are Tier 1."
- **Check:** Are tier distinctions clearly communicated? Does the website honestly label Community vs Tier 1?

### Persona 5: Copy Editor (Grammar + Tone)
- **Surface:** All `content/*.md`, README, website HTML
- **Check:** Typos, passive voice, buzzword density, inconsistent capitalization, developer cringe factor.
- **Rule:** If a sentence makes you wince, rewrite it.

### Persona 6: UX Designer
- **Surface:** Website (load in browser: https://stateweave.pantollventures.com, scroll every section)
- **Check:** Visual hierarchy, spacing, color contrast, mobile responsiveness, call-to-action clarity, demo visibility.
- **Rule:** Take a screenshot of hero, demo, frameworks table, and footer. Report any section that looks "meh."

### Persona 7: First-Time User
- **Surface:** `pip install stateweave`, `python examples/quickstart.py`
- **Attack:** "I followed the README and it didn't work."
- **Check:** Does the install command work in a clean environment? Does the quickstart produce the expected output?

### Persona 8: Journalist / Analyst
- **Surface:** `content/blog_post.md`, `content/hn_post.md`, website (open in browser)
- **Attack:** "The numbers don't add up. The blog says X but the website says Y."
- **Check:** Cross-reference every number across all surfaces. Framework count, test count, CLI count, adapter names must match everywhere.

### Persona 9: SMB Customer (Solo Founder / Small Team)
- **Surface:** Website hero + Quick Start (open in browser), README "See it working", PyPI install
- **Attack:** "I have 2 devs and no time. Can I get value in 15 minutes, or is this a science project?"
- **Check:**
  - Time to first working demo: Is `pip install stateweave && python examples/full_demo.py` genuinely < 60 seconds?
  - Is there a clear "what do I do next" after the demo? Or does the journey dead-end?
  - Vendor risk: Is this 1 person's side project? Would I bet my agent infra on it? (check contributor count, commit velocity, bus factor)
  - Pricing: Is it clear this is free/open-source? Or does the website feel like it's hiding a "Contact Sales" wall?
  - **Rule:** If the SMB can't go from zero to working in one terminal session, it's a fail.

### Persona 10: Mid-Market Customer (Engineering Manager, 10–50 eng)
- **Surface:** Website (Frameworks table, Security section, FAQ — open in browser), docs, CONTRIBUTING.md
- **Attack:** "My team uses LangGraph today and might switch to CrewAI next quarter. Can I actually mandate this as a standard?"
- **Check:**
  - Is the framework coverage table honest about what's Tier 1 vs Community? Would a manager trust the Community-tier adapters in prod?
  - Documentation: Is there enough for a team to adopt without hand-holding? Are there migration guides?
  - Support: Is there a path to get help? (GitHub Issues, Discussions, Discord?) Is it discoverable from the website?
  - Testing story: Can I tell my VP "this has 440+ tests and CI" with a straight face? Are the test badges real?
  - **Rule:** If the engineering manager can't write a one-paragraph justification to their VP, the positioning is too vague.

### Persona 11: Enterprise Customer (Platform Architect / Procurement)
- **Surface:** Security section (open website in browser), LICENSE, SECURITY.md, encryption code, compliance scanners
- **Attack:** "Our legal team needs to approve this. Our CISO needs to sign off. Show me your audit trail."
- **Check:**
  - License: Is Apache-2.0 clearly stated? Any ambiguity about commercial use?
  - Security: Is the encryption real (AES-256-GCM)? Is there a SECURITY.md with a vulnerability disclosure process?
  - Compliance: Are there audit-friendly features? (state diffs = audit trail, encryption at rest, non-portable warnings)
  - Data residency: Does state ever leave the customer's infra? Is that clear?
  - Maturity signals: Is there a CHANGELOG? Semantic versioning? Deprecation policy? Or does this look like a v0 hobby project?
  - **Rule:** If the enterprise architect can't answer "where does my data go?" in 30 seconds from the website, it's a fail.

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
- Live surface verification results (screenshots embedded or described)
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

- **Automated scan only (fast):** `python3 scripts/redteam_audit.py --quick`
- **Full audit with TTV + personas:** `python3 scripts/redteam_audit.py --personas`
- **JSON output for CI:** `python3 scripts/redteam_audit.py --quick --json --no-history`
- **After fixes:** Re-run Phase 1 to verify, then update the report

### v3 Features
- **Phase 1.5: Live Surface Verification** — mandatory browser-based visual inspection of all 6 public URLs
- **Auto consistency matrix** — extracts numbers from every surface and flags mismatches
- **Time-to-value test** — fresh venv install + demo in < 90s (requires Python ≥ 3.10)
- **Persona scorecards** — auto-scored 1-5 for 7 personas (HN, Security, Competitor, First-Time User, Journalist, SMB, MM, Enterprise)
- **Audit history** — appends to `breakdown/audit_history.jsonl`, shows trends vs previous run
- **CI integration** — `.github/workflows/redteam-audit.yml` runs `--quick` on every push, full on manual trigger
