#!/usr/bin/env python3
"""
StateWeave Red Team Audit v2 — automated surface scanner.

Runs deterministic checks against every public surface, auto-generates
the cross-surface consistency matrix, tracks audit history, runs a
time-to-value test, and outputs structured persona scorecards.

Usage:
    python3 scripts/redteam_audit.py                    # full audit
    python3 scripts/redteam_audit.py --quick             # skip time-to-value test
    python3 scripts/redteam_audit.py --json              # JSON output for CI
    python3 scripts/redteam_audit.py --personas          # also run persona scorecards

Exit codes:
    0  = all checks pass
    1  = failures found (details in output)
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
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
PUBLIC_DIRS = [
    "stateweave/",
    "docs/",
    "examples/",
    "content/",
    "blog/",
]
PUBLIC_EXTENSIONS = (".py", ".md", ".txt", ".yml", ".yaml", ".toml", ".html", ".json")
HISTORY_FILE = REPO_ROOT / "breakdown" / "audit_history.jsonl"

# ─── Helpers ────────────────────────────────────────────
PASS = "✅"
FAIL = "❌"
WARN = "⚠️"
INFO = "ℹ️"

results = []
extracted_data = {}  # For consistency matrix


def check(name, passed, detail=""):
    status = PASS if passed else FAIL
    results.append({"status": "pass" if passed else "fail", "name": name, "detail": detail})
    print(f"  {status}  {name}" + (f" — {detail}" if detail else ""))
    return passed


def warn(name, detail=""):
    results.append({"status": "warn", "name": name, "detail": detail})
    print(f"  {WARN}  {name}" + (f" — {detail}" if detail else ""))


def info(name, detail=""):
    results.append({"status": "info", "name": name, "detail": detail})
    print(f"  {INFO}  {name}" + (f" — {detail}" if detail else ""))


def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "redteam-audit/2.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"_error": str(e)}


def fetch_text(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "redteam-audit/2.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"_error: {e}"


def fetch_headers(url):
    try:
        req = urllib.request.Request(
            url, method="HEAD", headers={"User-Agent": "redteam-audit/2.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return dict(resp.headers), resp.status
    except Exception:
        return {}, 0


def count_pattern_in_files(pattern, directory, extensions):
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


def clean_for_matching(text):
    """Strip backticks and HTML code tags for tagline matching."""
    return re.sub(r"`|</?code>", "", text).lower()


def extract_number(text, pattern):
    """Extract a number from text matching a regex pattern."""
    m = re.search(pattern, text)
    return m.group(1) if m else None


# ─── Phase 1: Stale Copy Sweep ──────────────────────────
def phase_stale_copy():
    print("\n━━ Phase 1: Stale Copy Sweep ━━")
    all_hits = []
    for phrase in STALE_PHRASES:
        for pub_dir in PUBLIC_DIRS:
            full_dir = REPO_ROOT / pub_dir
            if full_dir.exists():
                hits = count_pattern_in_files(re.escape(phrase), str(full_dir), PUBLIC_EXTENSIONS)
                all_hits.extend([(phrase, h) for h in hits])

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

    readme = (REPO_ROOT / "README.md").read_text(errors="replace")
    check("README contains canonical tagline", CANONICAL_TAGLINE in clean_for_matching(readme))

    llms = (REPO_ROOT / "llms.txt").read_text(errors="replace")
    check("llms.txt contains canonical tagline", CANONICAL_TAGLINE in clean_for_matching(llms))


# ─── Phase 2: Number Claims ─────────────────────────────
def phase_number_claims():
    print("\n━━ Phase 2: Number Claims Verification ━━")

    adapters = list((REPO_ROOT / "stateweave" / "adapters").glob("*_adapter.py"))
    adapter_count = len(adapters)
    extracted_data["adapters_code"] = adapter_count
    check(
        f"Adapter count matches claim ({adapter_count} vs {EXPECTED_FRAMEWORK_COUNT})",
        adapter_count == EXPECTED_FRAMEWORK_COUNT,
        f"Found: {', '.join(sorted(a.stem for a in adapters))}",
    )

    test_count = 0
    for tf in (REPO_ROOT / "tests").rglob("*.py"):
        try:
            content = tf.read_text(errors="replace")
            test_count += len(re.findall(r"def test_", content))
        except Exception:
            pass
    extracted_data["tests_code"] = test_count
    check(f"Test count ({test_count}) supports '440+' claim", test_count >= 440)

    cli_count = 0
    cli_files = []
    for p in [REPO_ROOT / "stateweave" / "cli", REPO_ROOT / "stateweave" / "cli.py"]:
        if p.is_dir():
            cli_files.extend(p.glob("*.py"))
        elif p.is_file():
            cli_files.append(p)
    for cf in cli_files:
        try:
            content = cf.read_text(errors="replace")
            cli_count += len(
                re.findall(
                    r"@\w+\.command|@click\.command|add_command|add_parser|def (\w+)\(.*ctx",
                    content,
                )
            )
        except Exception:
            pass
    extracted_data["cli_code"] = cli_count
    if cli_count > 0:
        check(f"CLI commands found: {cli_count}", cli_count >= 10)
    else:
        warn("CLI command count could not be determined")


# ─── Phase 3: PyPI ───────────────────────────────────────
def phase_pypi():
    print("\n━━ Phase 3: PyPI ━━")
    data = fetch_json(f"https://pypi.org/pypi/{PYPI_PACKAGE}/json")
    if "_error" in data:
        check("PyPI API reachable", False, data["_error"])
        return

    i = data["info"]
    pypi_version = i.get("version", "")
    pypi_summary = i.get("summary", "")
    extracted_data["version_pypi"] = pypi_version
    extracted_data["tagline_pypi"] = pypi_summary

    check("PyPI version is set", bool(pypi_version), pypi_version)
    check("PyPI summary contains tagline", CANONICAL_TAGLINE in pypi_summary.lower(), pypi_summary)
    check("PyPI license is Apache-2.0", "apache" in (i.get("license") or "").lower())
    check(
        "PyPI has homepage URL",
        bool(i.get("home_page") or i.get("project_urls", {}).get("Homepage")),
    )

    pyproject = REPO_ROOT / "pyproject.toml"
    if pyproject.exists():
        content = pyproject.read_text()
        m = re.search(r'version\s*=\s*"([^"]+)"', content)
        if m:
            local_version = m.group(1)
            extracted_data["version_local"] = local_version
            if local_version != pypi_version:
                warn(
                    f"Local version ({local_version}) ≠ PyPI ({pypi_version})",
                    "expected if unreleased",
                )
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
    extracted_data["tagline_github"] = desc
    extracted_data["url_github"] = data.get("homepage", "")

    check("GitHub description contains tagline", CANONICAL_TAGLINE in desc.lower(), desc[:80])
    check("GitHub homepage URL set", bool(data.get("homepage")), data.get("homepage", "not set"))
    check(
        "GitHub topics set",
        len(data.get("topics", [])) >= 5,
        f"{len(data.get('topics', []))} topics",
    )
    check(
        "GitHub license set",
        bool(data.get("license")),
        data.get("license", {}).get("spdx_id", "none"),
    )
    info(
        f"Stars: {data.get('stargazers_count', 0)}, Forks: {data.get('forks_count', 0)}, Open Issues: {data.get('open_issues_count', 0)}"
    )


# ─── Phase 5: Website ────────────────────────────────────
def phase_website():
    print("\n━━ Phase 5: Website ━━")
    html = fetch_text(WEBSITE_URL)
    if html.startswith("_error"):
        check("Website reachable", False, html)
        return

    check("Website reachable", True)

    title_match = re.search(r"<title>([^<]+)</title>", html)
    title = title_match.group(1) if title_match else ""
    extracted_data["tagline_website"] = title
    check("Title contains tagline", CANONICAL_TAGLINE in title.lower(), title)

    og_image_match = re.search(r'og:image"\s+content="([^"]+)"', html)
    if og_image_match:
        og_url = og_image_match.group(1)
        headers, status = fetch_headers(og_url)
        check("og:image URL returns 200", status == 200, og_url)
        content_type = headers.get("Content-Type", headers.get("content-type", ""))
        check("og:image is an image", "image/" in content_type, content_type)
    else:
        check("og:image meta tag exists", False)

    og_desc_match = re.search(r'og:description"\s+content="([^"]+)"', html)
    if og_desc_match:
        check("og:description set", True, og_desc_match.group(1)[:60])
    else:
        check("og:description meta tag exists", False)

    check(
        "Demo embedded on website", "demo.webp" in html or "demo.mp4" in html or "demo.gif" in html
    )

    # Extract framework count from website table (exclude 'Custom' — it's extensible, not a framework)
    fw_rows = re.findall(r"<td>([^<]+)</td>\s*<td[^>]*>✓", html)
    real_frameworks = [f for f in set(fw_rows) if f.lower() != "custom"]
    extracted_data["frameworks_website"] = len(real_frameworks)

    llms_text = fetch_text(f"{WEBSITE_URL}/llms.txt")
    if llms_text.startswith("_error"):
        check("llms.txt served", False)
    else:
        check("llms.txt served", True)
        check("llms.txt contains tagline", CANONICAL_TAGLINE in clean_for_matching(llms_text))
        extracted_data["tagline_llms_web"] = llms_text.split("\n")[0][:100] if llms_text else ""


# ─── Phase 6: GTM Content ────────────────────────────────
def phase_gtm():
    print("\n━━ Phase 6: GTM Content ━━")
    content_dir = REPO_ROOT / "content"
    if not content_dir.exists():
        warn("No content/ directory found")
        return

    gtm_surfaces = {}
    for f in sorted(content_dir.glob("*.md")):
        content = f.read_text(errors="replace")
        stale_found = [p for p in STALE_PHRASES if p.lower() in content.lower()]
        check(
            f"{f.name}: no stale phrases",
            not stale_found,
            "; ".join(stale_found) if stale_found else "",
        )

        urls = re.findall(r"(?:https?://)?github\.com/GDWN-BLDR[^\s\)\"'>]*", content)
        check(f"{f.name}: has GitHub links", len(urls) > 0)

        # Extract numbers for consistency matrix
        fw_match = re.search(r"(\d+)\s*(?:framework|adapter)", content, re.I)
        test_match = re.search(r"(\d+)\+?\s*(?:test)", content, re.I)
        surface_key = f.stem
        content_clean = clean_for_matching(content)
        gtm_surfaces[surface_key] = {
            "frameworks": int(fw_match.group(1)) if fw_match else None,
            "tests": int(test_match.group(1)) if test_match else None,
            "has_tagline": CANONICAL_TAGLINE in content_clean,
        }

    extracted_data["gtm"] = gtm_surfaces

    blog_dir = REPO_ROOT / "blog"
    if blog_dir.exists():
        for f in sorted(blog_dir.glob("*.md")):
            content = f.read_text(errors="replace")
            stale_found = [p for p in STALE_PHRASES if p.lower() in content.lower()]
            check(f"blog/{f.name}: no stale phrases", not stale_found)


# ─── Phase 7: Code Hygiene ───────────────────────────────
def phase_code_hygiene():
    print("\n━━ Phase 7: Code Hygiene ━━")

    danger_hits = count_pattern_in_files(
        r"\bpickle\.\b|\beval\(|\byaml\.load\(",
        str(REPO_ROOT / "stateweave"),
        (".py",),
    )
    real_danger = [h for h in danger_hits if "scanner" not in h and "compliance" not in h]
    check(
        "No pickle/eval/yaml.load in source",
        len(real_danger) == 0,
        "; ".join(real_danger) if real_danger else "",
    )

    secret_hits = count_pattern_in_files(
        r"(sk-[a-zA-Z0-9]{20,}|AKIA[A-Z0-9]{16}|ghp_[a-zA-Z0-9]{36})",
        str(REPO_ROOT),
        PUBLIC_EXTENSIONS,
    )
    check(
        "No hardcoded API keys/secrets",
        len(secret_hits) == 0,
        "; ".join(secret_hits) if secret_hits else "",
    )

    init_file = REPO_ROOT / "stateweave" / "__init__.py"
    if init_file.exists():
        content = init_file.read_text()
        check("__init__.py has __version__", "__version__" in content)

    # Check for sensitive directories leaked into git despite .gitignore
    sensitive_dirs = [
        "board/",
        "breakdown/",
        "research/",
        "content/",
        ".agent/",
        ".agents/",
        ".stateweave/",
        "website/",
        "blog/",
    ]
    try:
        tracked = subprocess.run(
            ["git", "ls-files", "--cached"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=10,
        )
        if tracked.returncode == 0:
            leaked = []
            for sd in sensitive_dirs:
                leaked_files = [f for f in tracked.stdout.splitlines() if f.startswith(sd)]
                if leaked_files:
                    leaked.append(f"{sd} ({len(leaked_files)} files)")
            check(
                "No sensitive dirs tracked in git",
                len(leaked) == 0,
                "; ".join(leaked) if leaked else "board/, breakdown/, .agent/, website/ all clean",
            )
    except Exception:
        warn("Could not check git tracked files")


# ─── Phase 8: Asset Integrity ────────────────────────────
def phase_assets():
    print("\n━━ Phase 8: Asset Integrity ━━")
    demo_gif = REPO_ROOT / "assets" / "demo.gif"
    demo_webp = REPO_ROOT / "assets" / "demo.webp"
    demo = demo_gif if demo_gif.exists() else demo_webp
    check(
        "Demo asset exists",
        demo.exists(),
        f"{demo.name} — {demo.stat().st_size:,} bytes" if demo.exists() else "missing",
    )

    og = REPO_ROOT / "examples" / "full_demo.py"
    check("Full demo script exists (examples/full_demo.py)", og.exists())

    readme = (REPO_ROOT / "README.md").read_text(errors="replace")
    check(
        "README references demo asset", "assets/demo.gif" in readme or "assets/demo.webp" in readme
    )
    check("README references full_demo.py", "full_demo.py" in readme)


# ─── Phase 9: Time-to-Value Test ─────────────────────────
def phase_time_to_value():
    print("\n━━ Phase 9: Time-to-Value Test ━━")

    # Check Python version first — stateweave requires >=3.10
    py_version = sys.version_info
    if py_version < (3, 10):
        warn(
            f"System Python is {py_version.major}.{py_version.minor} (need ≥3.10)",
            "TTV test skipped — run on Python 3.10+ or in CI",
        )
        extracted_data["ttv_seconds"] = None
        extracted_data["ttv_skipped"] = f"Python {py_version.major}.{py_version.minor}"
        return

    venv_dir = tempfile.mkdtemp(prefix="stateweave_ttv_")
    try:
        # Create fresh venv
        t0 = time.time()
        subprocess.run(
            [sys.executable, "-m", "venv", venv_dir],
            check=True,
            capture_output=True,
            timeout=30,
        )
        venv_python = os.path.join(venv_dir, "bin", "python")
        t_venv = time.time() - t0

        # Install from PyPI (upgrade pip first — venv pip may be too old)
        t0 = time.time()
        subprocess.run(
            [venv_python, "-m", "pip", "install", "--quiet", "--upgrade", "pip"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        result = subprocess.run(
            [venv_python, "-m", "pip", "install", "--quiet", PYPI_PACKAGE],
            capture_output=True,
            text=True,
            timeout=120,
        )
        t_install = time.time() - t0
        install_ok = result.returncode == 0
        check(
            f"pip install {PYPI_PACKAGE} succeeds",
            install_ok,
            result.stderr.strip()[-100:] if not install_ok else f"{t_install:.1f}s",
        )

        if install_ok:
            # Run demo
            demo_script = REPO_ROOT / "examples" / "full_demo.py"
            if demo_script.exists():
                t0 = time.time()
                result = subprocess.run(
                    [venv_python, str(demo_script)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(REPO_ROOT),
                )
                t_demo = time.time() - t0
                demo_ok = result.returncode == 0
                check(
                    "full_demo.py runs successfully",
                    demo_ok,
                    f"{t_demo:.1f}s" if demo_ok else result.stderr.strip()[-200:],
                )

                if demo_ok:
                    # Verify output contains expected markers
                    output = result.stdout
                    markers = ["Export from LangGraph", "Import into MCP", "7/7 steps passed"]
                    for marker in markers:
                        check(f"Demo output contains '{marker}'", marker in output)

                total_time = t_venv + t_install + t_demo
                extracted_data["ttv_seconds"] = round(total_time, 1)
                check(
                    f"Total time-to-value: {total_time:.1f}s",
                    total_time < 90,
                    "Target: < 90 seconds from zero to working demo",
                )
            else:
                check("Demo script exists for TTV test", False)
    except subprocess.TimeoutExpired:
        check("Time-to-value test completed within timeout", False, "Timed out")
    except Exception as e:
        check("Time-to-value test ran without errors", False, str(e)[:100])
    finally:
        shutil.rmtree(venv_dir, ignore_errors=True)


# ─── Phase 10: Consistency Matrix ────────────────────────
def phase_consistency_matrix():
    print("\n━━ Phase 10: Cross-Surface Consistency Matrix ━━")

    # Extract from README
    readme = (REPO_ROOT / "README.md").read_text(errors="replace")
    readme_clean = clean_for_matching(readme)
    readme_fw = extract_number(readme, r"(\d+)\s*(?:framework|adapter)")
    readme_tests = extract_number(readme, r"(\d+)\+?\s*(?:test)")

    # Extract from llms.txt
    llms = (REPO_ROOT / "llms.txt").read_text(errors="replace")
    llms_fw = extract_number(llms, r"(\d+)\s*(?:framework|adapter)")

    # Build matrix
    matrix = {
        "tagline": {},
        "framework_count": {},
        "test_count": {},
        "version": {},
    }

    # Tagline presence — only required on PRIMARY surfaces, not GTM
    # (GTM content uses varied messaging by design)
    matrix["tagline"]["README"] = CANONICAL_TAGLINE in readme_clean
    matrix["tagline"]["llms.txt"] = CANONICAL_TAGLINE in clean_for_matching(llms)
    matrix["tagline"]["PyPI"] = CANONICAL_TAGLINE in extracted_data.get("tagline_pypi", "").lower()
    matrix["tagline"]["GitHub"] = (
        CANONICAL_TAGLINE in extracted_data.get("tagline_github", "").lower()
    )
    matrix["tagline"]["Website"] = (
        CANONICAL_TAGLINE in extracted_data.get("tagline_website", "").lower()
    )

    # Framework count
    matrix["framework_count"]["Code"] = extracted_data.get("adapters_code")
    matrix["framework_count"]["README"] = int(readme_fw) if readme_fw else None
    matrix["framework_count"]["llms.txt"] = int(llms_fw) if llms_fw else None
    matrix["framework_count"]["Website"] = extracted_data.get("frameworks_website")
    for k, v in extracted_data.get("gtm", {}).items():
        if v.get("frameworks"):
            matrix["framework_count"][k] = v["frameworks"]

    # Test count
    matrix["test_count"]["Code"] = extracted_data.get("tests_code")
    matrix["test_count"]["README"] = int(readme_tests) if readme_tests else None
    for k, v in extracted_data.get("gtm", {}).items():
        if v.get("tests"):
            matrix["test_count"][k] = v["tests"]

    # Version
    matrix["version"]["pyproject.toml"] = extracted_data.get("version_local")
    matrix["version"]["PyPI"] = extracted_data.get("version_pypi")

    extracted_data["consistency_matrix"] = matrix

    # Print the matrix
    print()
    print("  ┌─────────────────┬─────────────────────────────────────────────────┐")
    print("  │ Claim           │ Surfaces                                        │")
    print("  ├─────────────────┼─────────────────────────────────────────────────┤")

    mismatches = 0
    for claim_name, surfaces in matrix.items():
        values = {k: v for k, v in surfaces.items() if v is not None}
        if not values:
            continue

        # Check if all values match (for booleans, all True; for numbers, all same)
        if claim_name == "tagline":
            all_match = all(values.values())
            display_parts = [f"{k}:{'✅' if v else '❌'}" for k, v in values.items()]
        elif claim_name == "test_count":
            # Test counts use "440+" style claims: code is source of truth,
            # marketing counts are floors the code count must meet/exceed
            code_val = values.get("Code")
            all_match = True
            if code_val is not None:
                for k, v in values.items():
                    if k != "Code" and code_val < v:
                        all_match = False  # Code has fewer tests than marketing claims
            display_parts = [f"{k}={v}" for k, v in values.items()]
        else:
            unique_vals = set(values.values())
            all_match = len(unique_vals) <= 1
            display_parts = [f"{k}={v}" for k, v in values.items()]

        display = ", ".join(display_parts)
        if len(display) > 47:
            display = display[:44] + "..."
        print(f"  │ {claim_name:<15} │ {display:<47} │")

        if not all_match:
            mismatches += 1

    print("  └─────────────────┴─────────────────────────────────────────────────┘")
    print()

    check(
        "All consistency matrix claims match",
        mismatches == 0,
        f"{mismatches} mismatch(es)" if mismatches else "all surfaces consistent",
    )


# ─── Phase 11: Persona Scorecards ────────────────────────
def phase_persona_scorecards():
    print("\n━━ Phase 11: Persona Scorecards ━━")
    print("  (Auto-scored from available data; human review supplements these)")
    print()

    scorecards = []

    # Persona 1: Skeptical HN Commenter
    p1_scores = {}
    p1_scores["demo_proof"] = (
        5
        if (REPO_ROOT / "assets" / "demo.gif").exists()
        or (REPO_ROOT / "assets" / "demo.webp").exists()
        else 1
    )
    p1_scores["test_badge"] = 5 if extracted_data.get("tests_code", 0) >= 400 else 2
    p1_scores["honest_framing"] = 5  # Earned if no stale copy and tagline is canonical
    if any(r["status"] == "fail" and "Stale" in r["name"] for r in results):
        p1_scores["honest_framing"] = 2
    elif not any(
        r["status"] == "pass" and "canonical tagline" in r["name"].lower() for r in results
    ):
        p1_scores["honest_framing"] = 3
    p1_avg = sum(p1_scores.values()) / len(p1_scores)
    scorecards.append(
        {
            "persona": "Skeptical HN Commenter",
            "scores": p1_scores,
            "average": round(p1_avg, 1),
        }
    )
    print(f"  1. Skeptical HN Commenter      {p1_avg:.1f}/5  {p1_scores}")

    # Persona 3: Security Auditor
    p3_scores = {}
    p3_scores["no_dangerous_calls"] = (
        5 if not any(r["status"] == "fail" and "pickle" in r["name"] for r in results) else 1
    )
    p3_scores["no_secrets"] = (
        5
        if not any(r["status"] == "fail" and "secret" in r["name"].lower() for r in results)
        else 1
    )
    enc_file = REPO_ROOT / "stateweave" / "encryption.py"
    if enc_file.exists():
        enc = enc_file.read_text()
        p3_scores["real_aes256"] = 5 if "AES" in enc and "GCM" in enc else 2
        p3_scores["pbkdf2_iterations"] = 5 if re.search(r"iterations\s*=\s*[6-9]\d{5}", enc) else 3
    p3_avg = sum(p3_scores.values()) / len(p3_scores)
    scorecards.append(
        {
            "persona": "Security Auditor",
            "scores": p3_scores,
            "average": round(p3_avg, 1),
        }
    )
    print(f"  3. Security Auditor             {p3_avg:.1f}/5  {p3_scores}")

    # Persona 4: Competitor
    p4_scores = {}
    # Tier transparency — check that AdapterTier is defined and used in base.py
    p4_scores["tier_transparency"] = (
        5
        if (REPO_ROOT / "stateweave" / "adapters" / "base.py").read_text().count("AdapterTier") >= 2
        else 4
    )
    p4_scores["claim_accuracy"] = (
        5 if extracted_data.get("adapters_code") == EXPECTED_FRAMEWORK_COUNT else 2
    )
    p4_avg = sum(p4_scores.values()) / len(p4_scores)
    scorecards.append(
        {
            "persona": "Competitor",
            "scores": p4_scores,
            "average": round(p4_avg, 1),
        }
    )
    print(f"  4. Competitor                   {p4_avg:.1f}/5  {p4_scores}")

    # Persona 7: First-Time User
    p7_scores = {}
    ttv = extracted_data.get("ttv_seconds")
    ttv_skipped = extracted_data.get("ttv_skipped")
    if ttv is not None:
        p7_scores["install_works"] = 5
        p7_scores["demo_runs"] = (
            5
            if not any(r["status"] == "fail" and "full_demo.py runs" in r["name"] for r in results)
            else 1
        )
        p7_scores["time_under_90s"] = 5 if ttv < 90 else (3 if ttv < 120 else 1)
        p7_avg = sum(p7_scores.values()) / len(p7_scores)
        scorecards.append(
            {
                "persona": "First-Time User",
                "scores": p7_scores,
                "average": round(p7_avg, 1),
            }
        )
        print(f"  7. First-Time User              {p7_avg:.1f}/5  {p7_scores}")
    elif ttv_skipped:
        print(f"  7. First-Time User              N/A   (skipped: {ttv_skipped})")
    else:
        p7_scores = {"install_works": 0, "demo_runs": 0, "time_under_90s": 0}
        p7_avg = 0.0
        scorecards.append(
            {
                "persona": "First-Time User",
                "scores": p7_scores,
                "average": 0.0,
            }
        )
        print(f"  7. First-Time User              {p7_avg:.1f}/5  {p7_scores}")

    # Persona 8: Journalist
    p8_scores = {}
    # Use the same consistency logic as the matrix check (which already handles test_count approximation)
    matrix_passed = not any(
        r["status"] == "fail" and "consistency matrix" in r["name"].lower() for r in results
    )
    p8_scores["numbers_consistent"] = 5 if matrix_passed else 3
    p8_avg = sum(p8_scores.values()) / len(p8_scores)
    scorecards.append(
        {
            "persona": "Journalist / Analyst",
            "scores": p8_scores,
            "average": round(p8_avg, 1),
        }
    )
    print(f"  8. Journalist / Analyst         {p8_avg:.1f}/5  {p8_scores}")

    # Persona 9: SMB Customer
    p9_scores = {}
    ttv_skipped = extracted_data.get("ttv_skipped")
    if ttv_skipped:
        # Don't penalize when TTV can't run due to Python version
        p9_scores["time_to_value"] = None
    else:
        p9_scores["time_to_value"] = 5 if (ttv and ttv < 60) else (3 if (ttv and ttv < 120) else 1)
    p9_scores["open_source_clear"] = (
        5 if any(r["status"] == "pass" and "license" in r["name"].lower() for r in results) else 2
    )
    scored_vals = [v for v in p9_scores.values() if v is not None]
    p9_avg = sum(scored_vals) / max(len(scored_vals), 1)
    scorecards.append(
        {
            "persona": "SMB Customer",
            "scores": {k: v for k, v in p9_scores.items() if v is not None},
            "average": round(p9_avg, 1),
        }
    )
    print(f"  9. SMB Customer                 {p9_avg:.1f}/5  {p9_scores}")

    # Persona 10: Mid-Market
    p10_scores = {}
    p10_scores["test_credibility"] = 5 if extracted_data.get("tests_code", 0) >= 400 else 2
    docs_dir = REPO_ROOT / "docs"
    p10_scores["docs_exist"] = (
        5 if docs_dir.exists() and len(list(docs_dir.rglob("*.md"))) > 3 else 2
    )
    p10_scores["contributing_exists"] = 5 if (REPO_ROOT / "CONTRIBUTING.md").exists() else 1
    p10_avg = sum(p10_scores.values()) / len(p10_scores)
    scorecards.append(
        {
            "persona": "Mid-Market Customer",
            "scores": p10_scores,
            "average": round(p10_avg, 1),
        }
    )
    print(f"  10. Mid-Market Customer         {p10_avg:.1f}/5  {p10_scores}")

    # Persona 11: Enterprise
    p11_scores = {}
    p11_scores["license_clear"] = 5 if (REPO_ROOT / "LICENSE").exists() else 1
    p11_scores["security_policy"] = 5 if (REPO_ROOT / "SECURITY.md").exists() else 1
    p11_scores["changelog"] = 5 if (REPO_ROOT / "CHANGELOG.md").exists() else 1
    p11_scores["semver"] = (
        5 if re.match(r"\d+\.\d+\.\d+", extracted_data.get("version_local", "")) else 2
    )
    # Check if real encryption exists (AES-256-GCM in core/encryption.py)
    enc_file = REPO_ROOT / "stateweave" / "core" / "encryption.py"
    if enc_file.exists():
        enc_src = enc_file.read_text()
        has_aes = "AESGCM" in enc_src
        has_pbkdf2 = "PBKDF2" in enc_src
        has_proper_iterations = "600_000" in enc_src or "600000" in enc_src
        p11_scores["encryption_real"] = (
            5 if (has_aes and has_pbkdf2 and has_proper_iterations) else 3
        )
    else:
        p11_scores["encryption_real"] = 1
    p11_avg = sum(p11_scores.values()) / len(p11_scores)
    scorecards.append(
        {
            "persona": "Enterprise Customer",
            "scores": p11_scores,
            "average": round(p11_avg, 1),
        }
    )
    print(f"  11. Enterprise Customer         {p11_avg:.1f}/5  {p11_scores}")

    extracted_data["persona_scorecards"] = scorecards

    print()
    overall = sum(s["average"] for s in scorecards) / len(scorecards)
    print(f"  Overall persona score: {overall:.1f}/5")
    check("All personas score ≥ 3.0/5", all(s["average"] >= 3.0 for s in scorecards))


# ─── Scorecard ───────────────────────────────────────────
def print_scorecard():
    print("\n" + "═" * 60)
    print("SCORECARD")
    print("═" * 60)
    passes = sum(1 for r in results if r["status"] == "pass")
    fails = sum(1 for r in results if r["status"] == "fail")
    warns = sum(1 for r in results if r["status"] == "warn")
    total = passes + fails

    print(f"  {PASS} Passed: {passes}/{total}")
    print(f"  {FAIL} Failed: {fails}/{total}")
    if warns:
        print(f"  {WARN} Warnings: {warns}")
    print()

    if fails > 0:
        print("FAILURES:")
        for r in results:
            if r["status"] == "fail":
                print(f"  {FAIL} {r['name']}" + (f" — {r['detail']}" if r["detail"] else ""))
        print()
        print("VERDICT: 🔴 NOT READY — fix failures above")
        return 1
    elif warns > 0:
        print("VERDICT: 🟡 READY WITH CAVEATS — review warnings")
        return 0
    else:
        print("VERDICT: 🟢 LAUNCH READY")
        return 0


# ─── History ─────────────────────────────────────────────
def save_history():
    """Append this run's results to breakdown/audit_history.jsonl."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": sum(1 for r in results if r["status"] == "pass"),
        "failed": sum(1 for r in results if r["status"] == "fail"),
        "warnings": sum(1 for r in results if r["status"] == "warn"),
        "total": sum(1 for r in results if r["status"] in ("pass", "fail")),
        "ttv_seconds": extracted_data.get("ttv_seconds"),
        "adapters": extracted_data.get("adapters_code"),
        "tests": extracted_data.get("tests_code"),
        "cli_commands": extracted_data.get("cli_code"),
        "version": extracted_data.get("version_local"),
        "persona_scores": {
            s["persona"]: s["average"] for s in extracted_data.get("persona_scorecards", [])
        },
        "failures": [r["name"] for r in results if r["status"] == "fail"],
    }

    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")

    # Show trend if previous runs exist
    try:
        lines = HISTORY_FILE.read_text().strip().split("\n")
        if len(lines) >= 2:
            prev = json.loads(lines[-2])
            curr = record
            print("\n━━ Trend (vs previous run) ━━")
            delta_pass = curr["passed"] - prev["passed"]
            delta_fail = curr["failed"] - prev["failed"]
            arrow_p = "↑" if delta_pass > 0 else ("↓" if delta_pass < 0 else "→")
            arrow_f = "↑" if delta_fail > 0 else ("↓" if delta_fail < 0 else "→")
            print(f"  Passed: {prev['passed']} {arrow_p} {curr['passed']}")
            print(f"  Failed: {prev['failed']} {arrow_f} {curr['failed']}")
            if curr.get("ttv_seconds") and prev.get("ttv_seconds"):
                delta_ttv = curr["ttv_seconds"] - prev["ttv_seconds"]
                arrow_t = "↑" if delta_ttv > 0 else ("↓" if delta_ttv < 0 else "→")
                print(f"  TTV:    {prev['ttv_seconds']}s {arrow_t} {curr['ttv_seconds']}s")
    except Exception:
        pass


# ─── JSON Output ─────────────────────────────────────────
def print_json():
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "extracted_data": {k: v for k, v in extracted_data.items() if k != "consistency_matrix"},
        "consistency_matrix": extracted_data.get("consistency_matrix", {}),
        "scorecard": {
            "passed": sum(1 for r in results if r["status"] == "pass"),
            "failed": sum(1 for r in results if r["status"] == "fail"),
            "warnings": sum(1 for r in results if r["status"] == "warn"),
        },
    }
    print(json.dumps(output, indent=2, default=str))


# ─── Main ────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="StateWeave Red Team Audit v2")
    parser.add_argument("--quick", action="store_true", help="Skip time-to-value test")
    parser.add_argument("--json", action="store_true", help="Output JSON (for CI)")
    parser.add_argument("--personas", action="store_true", help="Include persona scorecards")
    parser.add_argument("--no-history", action="store_true", help="Don't save to history")
    args = parser.parse_args()

    if not args.json:
        print("╔══════════════════════════════════════════════════════════╗")
        print("║       StateWeave Red Team Audit v2 — Automated         ║")
        print("╚══════════════════════════════════════════════════════════╝")

    # Core phases (always run)
    phase_stale_copy()
    phase_number_claims()
    phase_pypi()
    phase_github()
    phase_website()
    phase_gtm()
    phase_code_hygiene()
    phase_assets()

    # Time-to-value (skip with --quick)
    if not args.quick:
        phase_time_to_value()
    else:
        info("Time-to-value test skipped (--quick)")

    # Consistency matrix (always)
    phase_consistency_matrix()

    # Persona scorecards (always in full mode, or with --personas)
    if not args.quick or args.personas:
        phase_persona_scorecards()

    # Output
    if args.json:
        print_json()
    exit_code = print_scorecard()

    # Save history
    if not args.no_history:
        save_history()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
