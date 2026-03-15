#!/usr/bin/env python3
"""
StateWeave Red Team Audit — automated surface scanner.

Runs deterministic checks against every public surface.
Anything that CAN be automated IS automated here, so the
human red-team personas only spend time on judgment calls.

Usage:
    python scripts/redteam_audit.py [--fix]

Exit codes:
    0  = all checks pass
    1  = failures found (details in output)
"""

import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

# ─── Config ─────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
GITHUB_REPO = "GDWN-BLDR/stateweave"
PYPI_PACKAGE = "stateweave"
WEBSITE_URL = "https://stateweave.pantollventures.com"
CANONICAL_TAGLINE = "git for agent brains"
STALE_PHRASES = [
    "cognitive state serializer",
    "cognitive state portability",
    "Cross-Framework Agent State Portability",
    "Cross-framework cognitive state",
]
EXPECTED_FRAMEWORK_COUNT = 10
EXPECTED_ADAPTER_GLOB = "stateweave/adapters/*_adapter.py"
PUBLIC_DIRS = [
    "stateweave/",
    "docs/",
    "examples/",
    "content/",
    "blog/",
]
PUBLIC_EXTENSIONS = (".py", ".md", ".txt", ".yml", ".yaml", ".toml", ".html", ".json")

# ─── Helpers ────────────────────────────────────────────
PASS = "✅"
FAIL = "❌"
WARN = "⚠️"
INFO = "ℹ️"

results = []


def check(name, passed, detail=""):
    status = PASS if passed else FAIL
    results.append((status, name, detail))
    print(f"  {status}  {name}" + (f" — {detail}" if detail else ""))
    return passed


def warn(name, detail=""):
    results.append((WARN, name, detail))
    print(f"  {WARN}  {name}" + (f" — {detail}" if detail else ""))


def info(name, detail=""):
    results.append((INFO, name, detail))
    print(f"  {INFO}  {name}" + (f" — {detail}" if detail else ""))


def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "redteam-audit/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"_error": str(e)}


def fetch_text(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "redteam-audit/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"_error: {e}"


def fetch_headers(url):
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "redteam-audit/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return dict(resp.headers), resp.status
    except Exception as e:
        return {}, 0


def count_pattern_in_files(pattern, directory, extensions):
    """Count files containing pattern."""
    hits = []
    for root, _, files in os.walk(directory):
        if ".git" in root or "__pycache__" in root or "research/" in root:
            continue
        for f in files:
            if any(f.endswith(ext) for ext in extensions):
                fpath = os.path.join(root, f)
                try:
                    content = open(fpath, encoding="utf-8", errors="replace").read()
                    if re.search(pattern, content, re.IGNORECASE):
                        hits.append(os.path.relpath(fpath, REPO_ROOT))
                except Exception:
                    pass
    return hits


# ─── Phase 1: Stale Copy Sweep ──────────────────────────
def phase_stale_copy():
    print("\n━━ Phase 1: Stale Copy Sweep ━━")
    all_hits = []
    for phrase in STALE_PHRASES:
        for pub_dir in PUBLIC_DIRS:
            full_dir = REPO_ROOT / pub_dir
            if full_dir.exists():
                hits = count_pattern_in_files(
                    re.escape(phrase), str(full_dir), PUBLIC_EXTENSIONS
                )
                all_hits.extend([(phrase, h) for h in hits])

    # Also check root-level files
    for f in REPO_ROOT.glob("*"):
        if f.is_file() and f.suffix in PUBLIC_EXTENSIONS:
            try:
                content = f.read_text(errors="replace")
                for phrase in STALE_PHRASES:
                    if phrase.lower() in content.lower():
                        all_hits.append((phrase, f.name))
            except Exception:
                pass

    if all_hits:
        for phrase, path in all_hits:
            check(f"Stale: '{phrase}' in {path}", False)
    else:
        check("No stale taglines in public files", True)

    # Verify canonical tagline exists in key places
    # Strip backticks and HTML code tags for matching (README uses `git` not git)
    readme = (REPO_ROOT / "README.md").read_text(errors="replace")
    readme_clean = re.sub(r'`|</?code>', '', readme).lower()
    check("README contains canonical tagline", CANONICAL_TAGLINE in readme_clean)

    llms = (REPO_ROOT / "llms.txt").read_text(errors="replace")
    llms_clean = re.sub(r'`|</?code>', '', llms).lower()
    check("llms.txt contains canonical tagline", CANONICAL_TAGLINE in llms_clean)


# ─── Phase 2: Number Claims ─────────────────────────────
def phase_number_claims():
    print("\n━━ Phase 2: Number Claims Verification ━━")

    # Count adapters
    adapters = list((REPO_ROOT / "stateweave" / "adapters").glob("*_adapter.py"))
    adapter_count = len(adapters)
    check(
        f"Adapter count matches claim ({adapter_count} vs {EXPECTED_FRAMEWORK_COUNT})",
        adapter_count == EXPECTED_FRAMEWORK_COUNT,
        f"Found: {', '.join(a.stem for a in adapters)}",
    )

    # Count test functions
    test_count = 0
    for tf in (REPO_ROOT / "tests").rglob("*.py"):
        try:
            content = tf.read_text(errors="replace")
            test_count += len(re.findall(r"def test_", content))
        except Exception:
            pass
    check(f"Test count ({test_count}) supports '440+' claim", test_count >= 440)

    # Count CLI commands — check both cli/ directory and single cli.py
    cli_count = 0
    cli_files = []
    cli_dir = REPO_ROOT / "stateweave" / "cli"
    cli_single = REPO_ROOT / "stateweave" / "cli.py"
    if cli_dir.exists() and cli_dir.is_dir():
        cli_files = list(cli_dir.glob("*.py"))
    if cli_single.exists():
        cli_files.append(cli_single)
    for cf in cli_files:
        try:
            content = cf.read_text(errors="replace")
            # Match click/typer decorators and add_command calls
            cli_count += len(re.findall(
                r'@\w+\.command|@click\.command|add_command|add_parser|def (\w+)\(.*ctx',
                content
            ))
        except Exception:
            pass
    if cli_count > 0:
        check(f"CLI commands found: {cli_count}", cli_count >= 10)
    else:
        warn("CLI command count could not be determined — check stateweave/cli.py")


# ─── Phase 3: PyPI ───────────────────────────────────────
def phase_pypi():
    print("\n━━ Phase 3: PyPI ━━")
    data = fetch_json(f"https://pypi.org/pypi/{PYPI_PACKAGE}/json")
    if "_error" in data:
        check("PyPI API reachable", False, data["_error"])
        return

    info_data = data["info"]
    check("PyPI version is set", bool(info_data.get("version")), info_data.get("version", ""))
    check(
        "PyPI summary contains tagline",
        CANONICAL_TAGLINE in (info_data.get("summary") or "").lower(),
        info_data.get("summary", ""),
    )
    check("PyPI license is Apache-2.0", "apache" in (info_data.get("license") or "").lower())
    check("PyPI has homepage URL", bool(info_data.get("home_page") or info_data.get("project_urls", {}).get("Homepage")))

    pypi_version = info_data.get("version", "")
    # Check pyproject.toml version matches
    pyproject = REPO_ROOT / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        match = re.search(r'version\s*=\s*"([^"]+)"', content)
        if match:
            local_version = match.group(1)
            if local_version != pypi_version:
                warn(f"Local version ({local_version}) ≠ PyPI ({pypi_version})", "may be expected if unreleased")
            else:
                check("Local version matches PyPI", True, local_version)


# ─── Phase 4: GitHub ─────────────────────────────────────
def phase_github():
    print("\n━━ Phase 4: GitHub ━━")
    data = fetch_json(f"https://api.github.com/repos/{GITHUB_REPO}")
    if "_error" in data:
        check("GitHub API reachable", False, data["_error"])
        return

    desc = data.get("description", "")
    check("GitHub description contains tagline", CANONICAL_TAGLINE in desc.lower(), desc[:80])
    check("GitHub homepage URL set", bool(data.get("homepage")), data.get("homepage", "not set"))
    check("GitHub topics set", len(data.get("topics", [])) >= 5, f"{len(data.get('topics', []))} topics")
    check("GitHub license set", bool(data.get("license")), data.get("license", {}).get("spdx_id", "none"))

    # Check CI status via latest commit
    info(f"Stars: {data.get('stargazers_count', 0)}, Forks: {data.get('forks_count', 0)}")


# ─── Phase 5: Website ────────────────────────────────────
def phase_website():
    print("\n━━ Phase 5: Website ━━")

    # Check main page
    html = fetch_text(WEBSITE_URL)
    if html.startswith("_error"):
        check("Website reachable", False, html)
        return

    check("Website reachable", True)

    # Title tag
    title_match = re.search(r"<title>([^<]+)</title>", html)
    title = title_match.group(1) if title_match else ""
    check("Title contains tagline", CANONICAL_TAGLINE in title.lower(), title)

    # og:image
    og_image_match = re.search(r'og:image"\s+content="([^"]+)"', html)
    if og_image_match:
        og_url = og_image_match.group(1)
        headers, status = fetch_headers(og_url)
        check("og:image URL returns 200", status == 200, og_url)
        content_type = headers.get("Content-Type", headers.get("content-type", ""))
        check("og:image is an image", "image/" in content_type, content_type)
    else:
        check("og:image meta tag exists", False)

    # og:description
    og_desc_match = re.search(r'og:description"\s+content="([^"]+)"', html)
    if og_desc_match:
        check("og:description set", True, og_desc_match.group(1)[:60])
    else:
        check("og:description meta tag exists", False)

    # Demo image
    check("Demo embedded on website", "demo.webp" in html or "demo.mp4" in html or "demo.gif" in html)

    # llms.txt
    llms_text = fetch_text(f"{WEBSITE_URL}/llms.txt")
    if llms_text.startswith("_error"):
        check("llms.txt served", False)
    else:
        check("llms.txt served", True)
        llms_text_clean = re.sub(r'`|</?code>', '', llms_text).lower()
        check("llms.txt contains tagline", CANONICAL_TAGLINE in llms_text_clean)


# ─── Phase 6: GTM Content ────────────────────────────────
def phase_gtm():
    print("\n━━ Phase 6: GTM Content ━━")
    content_dir = REPO_ROOT / "content"
    if not content_dir.exists():
        warn("No content/ directory found")
        return

    for f in sorted(content_dir.glob("*.md")):
        content = f.read_text(errors="replace")
        # Check for stale phrases
        stale_found = [p for p in STALE_PHRASES if p.lower() in content.lower()]
        check(f"{f.name}: no stale phrases", not stale_found, "; ".join(stale_found) if stale_found else "")

        # Check links
        # Match both https:// and bare github.com links
        urls = re.findall(r"(?:https?://)?github\.com/GDWN-BLDR[^\s\)\"'>]*", content)
        github_urls = urls
        check(f"{f.name}: has GitHub links", len(github_urls) > 0)

    # Blog post
    blog_dir = REPO_ROOT / "blog"
    if blog_dir.exists():
        for f in sorted(blog_dir.glob("*.md")):
            content = f.read_text(errors="replace")
            stale_found = [p for p in STALE_PHRASES if p.lower() in content.lower()]
            check(f"blog/{f.name}: no stale phrases", not stale_found)


# ─── Phase 7: Code Hygiene ───────────────────────────────
def phase_code_hygiene():
    print("\n━━ Phase 7: Code Hygiene ━━")

    # No pickle/eval
    danger_hits = count_pattern_in_files(
        r"\bpickle\.\b|\beval\(|\byaml\.load\(",
        str(REPO_ROOT / "stateweave"),
        (".py",),
    )
    # Filter out safe references (comments, strings mentioning "no pickle")
    real_danger = [h for h in danger_hits if "scanner" not in h and "compliance" not in h]
    check("No pickle/eval/yaml.load in source", len(real_danger) == 0,
          "; ".join(real_danger) if real_danger else "")

    # No hardcoded secrets
    secret_hits = count_pattern_in_files(
        r"(sk-[a-zA-Z0-9]{20,}|AKIA[A-Z0-9]{16}|ghp_[a-zA-Z0-9]{36})",
        str(REPO_ROOT),
        PUBLIC_EXTENSIONS,
    )
    check("No hardcoded API keys/secrets", len(secret_hits) == 0,
          "; ".join(secret_hits) if secret_hits else "")

    # __init__.py has current version
    init_file = REPO_ROOT / "stateweave" / "__init__.py"
    if init_file.exists():
        content = init_file.read_text()
        check("__init__.py has __version__", "__version__" in content)


# ─── Phase 8: Asset Integrity ────────────────────────────
def phase_assets():
    print("\n━━ Phase 8: Asset Integrity ━━")
    demo = REPO_ROOT / "assets" / "demo.webp"
    check("Demo asset exists (assets/demo.webp)", demo.exists(),
          f"{demo.stat().st_size:,} bytes" if demo.exists() else "missing")

    og = REPO_ROOT / "examples" / "full_demo.py"
    check("Full demo script exists (examples/full_demo.py)", og.exists())

    readme = (REPO_ROOT / "README.md").read_text(errors="replace")
    check("README references demo asset", "assets/demo.webp" in readme)
    check("README references full_demo.py", "full_demo.py" in readme)


# ─── Scorecard ───────────────────────────────────────────
def print_scorecard():
    print("\n" + "═" * 60)
    print("SCORECARD")
    print("═" * 60)
    passes = sum(1 for s, _, _ in results if s == PASS)
    fails = sum(1 for s, _, _ in results if s == FAIL)
    warns = sum(1 for s, _, _ in results if s == WARN)
    total = passes + fails

    print(f"  {PASS} Passed: {passes}/{total}")
    print(f"  {FAIL} Failed: {fails}/{total}")
    if warns:
        print(f"  {WARN} Warnings: {warns}")
    print()

    if fails > 0:
        print("FAILURES:")
        for s, name, detail in results:
            if s == FAIL:
                print(f"  {FAIL} {name}" + (f" — {detail}" if detail else ""))
        print()
        print("VERDICT: 🔴 NOT READY — fix failures above")
        return 1
    elif warns > 0:
        print("VERDICT: 🟡 READY WITH CAVEATS — review warnings")
        return 0
    else:
        print("VERDICT: 🟢 LAUNCH READY")
        return 0


# ─── Main ────────────────────────────────────────────────
def main():
    print("╔══════════════════════════════════════════════════════════╗")
    print("║         StateWeave Red Team Audit — Automated           ║")
    print("╚══════════════════════════════════════════════════════════╝")

    phase_stale_copy()
    phase_number_claims()
    phase_pypi()
    phase_github()
    phase_website()
    phase_gtm()
    phase_code_hygiene()
    phase_assets()

    return print_scorecard()


if __name__ == "__main__":
    sys.exit(main())
