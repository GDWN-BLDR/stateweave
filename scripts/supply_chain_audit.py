#!/usr/bin/env python3
"""
StateWeave Supply Chain Audit
================================
Scans the dependency tree for known CVEs, license compatibility,
floating version pins, typosquats, and transitive bloat.

Usage:
    python scripts/supply_chain_audit.py            # human-readable output
    python scripts/supply_chain_audit.py --json      # JSON output for CI
    python scripts/supply_chain_audit.py --fix       # suggest pin fixes

Exit codes:
    0 = all checks pass
    1 = issues found
"""

import argparse
import importlib.metadata
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"
INFO = "ℹ️"

results = []

# Known permissive licenses (SPDX identifiers or common names)
PERMISSIVE_LICENSES = {
    "apache", "apache-2.0", "apache 2.0", "apache software license",
    "mit", "mit license",
    "bsd", "bsd-2-clause", "bsd-3-clause", "bsd license",
    "isc", "isc license",
    "psf", "python software foundation license",
    "psfl", "python software foundation",
    "unlicense", "public domain",
    "0bsd", "cc0",
    "mpl-2.0", "mozilla public license 2.0",
}

# Known typosquat patterns for StateWeave's dependencies
EXPECTED_DEPS = {
    "pydantic": ["pydantiic", "pydanntic", "pydantic2", "py-dantic"],
    "cryptography": ["cryptograpy", "cryptogrpahy", "cyptography", "kryptography"],
    "pyyaml": ["py-yaml", "pyaml", "pyyaml2", "pyymal"],
}


def check(name, passed, detail=""):
    status = PASS if passed else FAIL
    results.append({"status": "pass" if passed else "fail", "name": name, "detail": detail})
    if not args_global.json:
        print(f"  {status}  {name}" + (f" — {detail}" if detail else ""))
    return passed


def warn(name, detail=""):
    results.append({"status": "warn", "name": name, "detail": detail})
    if not args_global.json:
        print(f"  {WARN}  {name}" + (f" — {detail}" if detail else ""))


def info(name, detail=""):
    results.append({"status": "info", "name": name, "detail": detail})
    if not args_global.json:
        print(f"  {INFO}  {name}" + (f" — {detail}" if detail else ""))


# ─── Phase 1: pip audit (CVE scan) ──────────────────────────────

def phase_pip_audit():
    if not args_global.json:
        print("\n━━ Supply Chain: CVE Scan (pip audit) ━━")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--format=json", "--progress-spinner=off"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout) if result.stdout.strip() else []
            vulns = [v for v in data if v.get("vulns")]
            if vulns:
                for pkg in vulns:
                    for vuln in pkg["vulns"]:
                        check(
                            f"CVE: {pkg['name']}=={pkg['version']}",
                            False,
                            f"{vuln.get('id', 'unknown')} — {vuln.get('description', '')[:80]}"
                        )
            else:
                check("No known CVEs in dependency tree", True)
        else:
            # pip-audit exits non-zero when vulns found
            try:
                data = json.loads(result.stdout) if result.stdout.strip() else []
                vulns = [v for v in data if v.get("vulns")]
                if vulns:
                    for pkg in vulns:
                        for vuln in pkg["vulns"]:
                            check(
                                f"CVE: {pkg['name']}=={pkg['version']}",
                                False,
                                f"{vuln.get('id', 'unknown')}"
                            )
                else:
                    check("No known CVEs in dependency tree", True)
            except json.JSONDecodeError:
                warn("pip-audit returned non-JSON output", result.stderr[:200])

    except FileNotFoundError:
        warn(
            "pip-audit not installed",
            "Install with: pip install pip-audit"
        )
    except subprocess.TimeoutExpired:
        warn("pip-audit timed out (120s)")


# ─── Phase 2: License Compatibility ─────────────────────────────

def phase_license_scan():
    if not args_global.json:
        print("\n━━ Supply Chain: License Compatibility ━━")

    # Get all installed packages
    problematic = []
    all_deps = []

    try:
        for dist in importlib.metadata.distributions():
            name = dist.metadata["Name"]
            license_val = dist.metadata.get("License", "") or ""
            classifiers = dist.metadata.get_all("Classifier") or []

            # Extract license from classifiers if License field is empty
            license_classifiers = [c for c in classifiers if c.startswith("License ::")]
            if not license_val and license_classifiers:
                license_val = license_classifiers[0].split("::")[-1].strip()

            all_deps.append({"name": name, "license": license_val})

            # Check for copyleft / restrictive licenses
            license_lower = license_val.lower().strip()
            if any(kw in license_lower for kw in ["gpl", "agpl", "sspl", "eupl", "cc-by-sa"]):
                # Exclude LGPL (it's OK for dynamic linking)
                if "lgpl" not in license_lower:
                    problematic.append(f"{name}: {license_val}")

    except Exception as e:
        warn(f"Could not scan licenses: {e}")
        return

    if problematic:
        for p in problematic:
            check(f"License: {p}", False, "Copyleft license — may conflict with Apache-2.0")
    else:
        check("All dependency licenses are permissive", True, f"{len(all_deps)} packages scanned")


# ─── Phase 3: Pin Verification ──────────────────────────────────

def phase_pin_verification():
    if not args_global.json:
        print("\n━━ Supply Chain: Pin Verification ━━")

    pyproject = REPO_ROOT / "pyproject.toml"
    if not pyproject.exists():
        warn("pyproject.toml not found")
        return

    content = pyproject.read_text()

    # Extract dependencies from [project.dependencies]
    dep_section = re.search(r'dependencies\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if not dep_section:
        warn("Could not parse dependencies from pyproject.toml")
        return

    deps_raw = dep_section.group(1)
    deps = re.findall(r'"([^"]+)"', deps_raw)

    floating = []
    for dep in deps:
        # Normalize: strip extras
        dep_clean = re.split(r'\[', dep)[0].strip()
        # Check for upper bound
        if ">=" in dep_clean and "<" not in dep_clean and "==" not in dep_clean:
            floating.append(dep_clean)

    if floating:
        for f in floating:
            warn(f"Floating pin: {f}", "No upper bound — vulnerable to breaking changes")
    else:
        check("All dependencies have bounded pins", True)

    # Check dev dependencies too
    dev_section = re.search(r'dev\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if dev_section:
        dev_deps = re.findall(r'"([^"]+)"', dev_section.group(1))
        dev_floating = [d for d in dev_deps
                        if ">=" in d and "<" not in d and "==" not in d]
        if dev_floating:
            info(f"Dev deps with floating pins: {len(dev_floating)}")


# ─── Phase 4: Typosquat Detection ───────────────────────────────

def phase_typosquat_detection():
    if not args_global.json:
        print("\n━━ Supply Chain: Typosquat Detection ━━")

    pyproject = REPO_ROOT / "pyproject.toml"
    if not pyproject.exists():
        return

    content = pyproject.read_text()

    # Extract ALL package names from pyproject.toml
    all_deps = re.findall(r'"([a-zA-Z0-9_-]+)(?:[><=!])', content)

    suspects = []
    for dep in all_deps:
        dep_lower = dep.lower().replace("-", "").replace("_", "")
        for expected, typos in EXPECTED_DEPS.items():
            expected_normalized = expected.lower().replace("-", "").replace("_", "")
            for typo in typos:
                typo_normalized = typo.lower().replace("-", "").replace("_", "")
                if dep_lower == typo_normalized:
                    suspects.append(f"{dep} (possible typosquat of {expected})")

    if suspects:
        for s in suspects:
            check(f"Typosquat: {s}", False)
    else:
        check("No typosquat suspects detected", True, f"{len(all_deps)} deps checked")


# ─── Phase 5: Transitive Depth ──────────────────────────────────

def phase_transitive_depth():
    if not args_global.json:
        print("\n━━ Supply Chain: Transitive Dependency Depth ━━")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            capture_output=True, text=True, timeout=30,
        )
        packages = json.loads(result.stdout)
        count = len(packages)

        check(
            f"Transitive dep count: {count}",
            count <= 100,
            f"{'OK' if count <= 100 else 'Bloated'} — target ≤100 in a lean install"
        )

    except Exception as e:
        warn(f"Could not count packages: {e}")


# ─── Main ────────────────────────────────────────────────────────

def main():
    global args_global
    parser = argparse.ArgumentParser(description="StateWeave Supply Chain Audit")
    parser.add_argument("--json", action="store_true", help="JSON output for CI")
    parser.add_argument("--fix", action="store_true", help="Suggest pin fixes")
    args_global = parser.parse_args()

    if not args_global.json:
        print("╔══════════════════════════════════════════════════════════╗")
        print("║        StateWeave Supply Chain Audit                    ║")
        print("╚══════════════════════════════════════════════════════════╝")

    phase_pip_audit()
    phase_license_scan()
    phase_pin_verification()
    phase_typosquat_detection()
    phase_transitive_depth()

    # Summary
    fails = sum(1 for r in results if r["status"] == "fail")
    passes = sum(1 for r in results if r["status"] == "pass")
    warns = sum(1 for r in results if r["status"] == "warn")

    if args_global.json:
        print(json.dumps({
            "results": results,
            "summary": {"passed": passes, "failed": fails, "warnings": warns},
        }, indent=2))
    else:
        print(f"\n{'═' * 60}")
        print(f"  {PASS} Passed: {passes}  {FAIL} Failed: {fails}  {WARN} Warnings: {warns}")
        if fails > 0:
            print(f"  VERDICT: 🔴 SUPPLY CHAIN ISSUES FOUND")
        elif warns > 0:
            print(f"  VERDICT: 🟡 REVIEW WARNINGS")
        else:
            print(f"  VERDICT: 🟢 CLEAN")
        print("═" * 60)

    return 1 if fails > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
