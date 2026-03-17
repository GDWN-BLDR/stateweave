# 🔴 Red Team Analysis v8 — GTM Materials Pre-Launch Audit

**Date**: 2026-03-17
**Scope**: Every surface a customer, journalist, or agent would interact with
**Verdict**: 🟡 READY WITH CAVEATS — 5 blockers, 8 should-fix, 5 nits

---

## Automated Scan Scorecard

```
✅ Passed: 43/44
❌ Failed: 1/44

FAILURE:
  ❌ full_demo.py crashes in clean install (langgraph not installed)
```

---

## 🔴 P0 — Fix Before Launch (5 items)

### 1. `full_demo.py` crashes in clean `pip install stateweave` environment

**Surface**: README, website, first-time user experience
**Issue**: The README tells users to run `pip install stateweave && python examples/full_demo.py`. In a clean environment, this crashes with `AdapterError: langgraph is not installed`.
**Root Cause**: The redteam_audit.py TTV test installs stateweave in a fresh venv. Even though `LangGraphAdapter()` without args shouldn't trigger `_require_framework`, the error occurs during the clean-install run.
**Fix**: Either (a) ensure full_demo.py works without any framework extras (use only dict-based mode), or (b) change the README to say `pip install "stateweave[langgraph]" && python examples/full_demo.py`, or (c) add a try/except in full_demo.py that catches the error and prints a helpful message.

### 2. Blog post (`blog/why-we-built-stateweave.md`) has 3 incorrect API paths

**Surface**: Blog, dev.to post
**Lines 78-89**: Code that doesn't match the actual API.

| Blog Code | Actual API |
|-----------|-----------|
| `from stateweave.core.signing import sign_payload, generate_keypair` | Module doesn't exist. Signing is `EncryptionFacade.sign()`, `EncryptionFacade.generate_signing_keypair()` |
| `store.checkpoint(payload, message="before risky operation")` | Parameter is `label=`, not `message=` |
| `payload = store.rollback()` | Requires `agent_id` and `version` args: `store.rollback("my-agent", version=3)` |

**Fix**: Rewrite the blog Time Travel and Security code blocks to match actual API.

### 3. `full_demo.py` banner says `v0.3.1`, product is `v0.3.2`

**Surface**: Demo output, README (embedded demo output)
**Line 6**: `print("  StateWeave v0.3.1 — Real End-to-End Demo")`
**Fix**: Update to `v0.3.2`.

### 4. "440+ tests" claim is massively stale

**Surface**: `llms.txt` (line 70), `reddit_posts.md` (line 142), `launch_playbook.md` (lines 98, 165, 276), `GTM_PLAYBOOK.md` (line 183)
**Actual**: ~1,326 test functions across 46 test files. "440+" undersells by 3x.
**Fix**: Update to "1,300+ tests" everywhere, or use a safe round-down like "1,000+ tests".

### 5. "10 scanners" claim is stale — actually 12

**Surface**: README (line 488), `blog_post.md` (line 48), `twitter_thread.md` (line 32)
**Actual**: 12 scanners (`adapter_isolation` and `ruff_quality` were added but never reflected in copy).
**Fix**: Update to "12 scanners" and add the two missing scanners to the README UCE table.

---

## 🟡 P1 — Should Fix Before Launch (8 items)

### 6. README schema example shows `stateweave_version="0.3.1"` (line 262)

Should be `0.3.2`. A journalist will cross-reference this.

### 7. Website schema example shows `stateweave_version="0.3.0"` (FAQ section)

Same issue. Stale version string.

### 8. README has two near-identical comparison tables

Lines 515-524 ("Why Not Just Serialize to JSON Yourself?") and lines 583-590 ("What StateWeave Replaces") cover almost identical ground with slightly different wording. This is redundant and makes the README feel padded.

**Recommendation**: Remove "What StateWeave Replaces" section entirely — it adds nothing the earlier table didn't cover.

### 9. README UCE table is missing 2 scanners

Table at line 490-501 lists 10 scanners. Missing:
- `adapter_isolation` — Ensures adapters don't import across isolation boundaries
- `ruff_quality` — Enforces ruff formatting standards

**Fix**: Add both to the table.

### 10. `llms.txt` is missing time-travel and security as primary features

The "Key Features" list in `llms.txt` buries time travel at bullet 3 and doesn't mention the compliance engine at all. Since llms.txt is what AI agents read, and the product has repositioned around debugging+security, the feature ordering should match.

### 11. Website code blocks appear duplicated

The website renders each code example twice (visible in the markdown extraction). This is likely a CSS/JS tab-switching issue where both "before" and "after" states render simultaneously. Needs visual verification.

### 12. CHANGELOG test counts create an archaeology trail

CHANGELOG entries record `168 → 254 → 315 → 440+` test count progression. This is fine for internal history, but a competitor or journalist can reconstruct the build timeline. Not a blocker, but worth being aware of.

### 13. `LANGGRAPH_TARGET_VERSION = "1.0.x"` in adapter (line 46)

The adapter code says it targets LangGraph `1.0.x`, but the CI matrix tests against `0.2.0-0.2.62`. The version claim should match what's actually tested.

---

## 🟢 P2 — Nits (5 items)

### 14. HN post title (hn_post.md, line 1) is 102 chars — over the 55-char sweet spot

The title in `hn_post.md` is: `Show HN: StateWeave – Time-travel debugging for AI agents (checkpoint, rollback, diff across 10 frameworks)`. The launch_playbook.md says 43-char titles get 24% more upvotes. The launch playbook already has the shorter version: `Show HN: StateWeave – git for agent brains`. Use that one.

### 15. Blog says "We built" / "We believe" — who's "we"?

The blog post switches between "I" and "we" which is fine for a company, but with 1 contributor on GitHub, "we" invites skepticism. Consider using "I" throughout to match the HN post tone.

### 16. `quickstart.py` accesses `lg._agents` directly (private attr)

This is the first code a new user sees. Accessing private attributes (`_agents`) feels hacky and untested. Not a copy issue, but a UX issue.

### 17. Twitter thread uses emoji (tweets 2) despite launch playbook advising against it

Tweet 2 uses 🔍🔒⚡📊. The launch playbook explicitly says "Use them sparingly or not at all." The emoji here add visual structure, but the inconsistency is worth noting.

### 18. Pantoll Ventures link in blog footer (line 113)

`https://pantollventures.com` — verify this resolves correctly and looks professional. This is the only link in all GTM materials that goes to the company rather than the product.

---

## Cross-Surface Consistency Matrix

| Claim | README | Website | PyPI | HN Post | Twitter | Reddit | Blog | llms.txt |
|-------|--------|---------|------|---------|---------|--------|------|----------|
| **Tagline** | ✅ git for agent brains | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Framework count** | ✅ 10 | ✅ 10 | ✅ 10 | ✅ 10 | ✅ 10 | ✅ 10 | ✅ 10 | ✅ 10 |
| **Test count** | — (not stated) | — | — | — | — | ❌ 440+ | — | ❌ 440+ |
| **Scanner count** | ❌ 10 | — | — | ❌ 10 | ❌ 10 | — | ❌ 10 | — |
| **CLI command count** | ✅ 14 | — | — | ✅ 14 | ✅ 14 | ✅ 14 | — | — |
| **Version** | ❌ 0.3.1 | ❌ 0.3.0 | ✅ 0.3.2 | — | — | — | — | — |
| **GitHub URL** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **License** | ✅ Apache-2.0 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## Persona Walk Summaries

### P1: Skeptical HN Commenter — ✅ PASS
README has demo recording, integration test proof, honest "still early" framing. The shorter HN title should be used.

### P2: Framework Maintainer — ✅ PASS with caveat
Adapters conditionally import frameworks. `_require_framework` only fires when `graph`/`checkpointer` are provided. But `LANGGRAPH_TARGET_VERSION = "1.0.x"` is inaccurate — tested range is 0.2.x.

### P3: Security Auditor — ✅ PASS
Crypto is real. AES-256-GCM with per-op nonces, PBKDF2 600K, Ed25519. No pickle/eval. Compliance engine enforces this.

### P4: Competitor — ✅ PASS
Tier labels are honest and visible in README and website.

### P5: Copy Editor — 🟡 ISSUES FOUND
- Blog has wrong API paths (P0 #2)
- "We" vs "I" inconsistency (P2 #15)
- No buzzwords detected ✅
- No AI-sounding language ✅
- Tone is appropriately humble ✅

### P6: UX Designer — 🟡 MINOR ISSUES
- Website has duplicate code blocks (P1 #11)
- README has duplicate comparison tables (P1 #8)
- Otherwise well-structured with clear hierarchy

### P7: First-Time User — ❌ FAIL
`pip install stateweave && python examples/full_demo.py` crashes (P0 #1). `quickstart.py` works.

### P8: Journalist / Analyst — 🟡 ISSUES
- Test count inconsistent (P0 #4)
- Scanner count inconsistent (P0 #5)
- Version strings mismatched across surfaces (P1 #6, #7)

### P9: SMB Customer — ✅ PASS
`pip install stateweave && python examples/quickstart.py` works in < 60s. Clear "what next" path. Free/open-source is clear.

### P10: Mid-Market Customer — ✅ PASS
Tier table is honest. Docs exist. CONTRIBUTING.md exists. Test story is credible (once counts are updated).

### P11: Enterprise Customer — ✅ PASS
Apache-2.0 clear. SECURITY.md with disclosure process. CHANGELOG with semver. Encryption is real. State never leaves customer infra (clearly stated).

---

## Verdict

### 🟡 READY WITH CAVEATS

The 5 P0 items are all straightforward fixes (stale numbers, version strings, broken API examples, demo crash). None require architectural changes. Estimated time to fix all P0s: ~30 minutes.

**After fixing P0s**: 🟢 LAUNCH READY

### Priority Fix Order
1. Fix full_demo.py crash + stale version banner → P0 #1 + #3
2. Fix blog code examples → P0 #2
3. Update "440+ tests" → "1,300+ tests" everywhere → P0 #4
4. Update "10 scanners" → "12 scanners" everywhere → P0 #5
5. Fix version strings in README/website → P1 #6 + #7
