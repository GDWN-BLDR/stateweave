#!/usr/bin/env python3
"""
StateWeave Differential Red Team — Regression Detection
==========================================================
Compares the current audit state against the previous run to detect:
- API surface expansion (new exported symbols, CLI flags, REST endpoints)
- Test count regression (fewer tests than last run)
- Failure novelty (new vs recurring vs fixed failures)
- Adapter count regression

Usage:
    python scripts/redteam_diff.py                 # diff vs last audit
    python scripts/redteam_diff.py --json          # JSON output
    python scripts/redteam_diff.py --baseline FILE # diff vs specific baseline

Reads: breakdown/audit_history.jsonl
"""

import argparse
import ast
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HISTORY_FILE = REPO_ROOT / "breakdown" / "audit_history.jsonl"
SNAPSHOT_FILE = REPO_ROOT / "breakdown" / "api_surface_snapshot.json"

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"
INFO = "ℹ️"

results = []


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


# ─── Snapshot: Current API Surface ───────────────────────────────

def capture_current_surface():
    """Capture the current public API surface."""
    surface = {
        "timestamp": datetime.utcnow().isoformat(),
        "exported_symbols": [],
        "cli_subcommands": [],
        "rest_endpoints": [],
        "adapter_count": 0,
        "test_count": 0,
    }

    # 1. Exported symbols from __init__.py
    init_file = REPO_ROOT / "stateweave" / "__init__.py"
    if init_file.exists():
        content = init_file.read_text()
        # Look for __all__ or direct imports
        all_match = re.search(r'__all__\s*=\s*\[([^\]]+)\]', content, re.DOTALL)
        if all_match:
            symbols = re.findall(r'"([^"]+)"|\'([^\']+)\'', all_match.group(1))
            surface["exported_symbols"] = [s[0] or s[1] for s in symbols]
        else:
            # Fall back to parsing import statements
            for m in re.finditer(r'from\s+\S+\s+import\s+(\w+)', content):
                surface["exported_symbols"].append(m.group(1))
            # Also catch direct assignments
            for m in re.finditer(r'^(\w+)\s*=', content, re.MULTILINE):
                name = m.group(1)
                if not name.startswith('_') or name == '__version__':
                    surface["exported_symbols"].append(name)

    # 2. CLI subcommands (parse cli.py for add_parser calls)
    cli_file = REPO_ROOT / "stateweave" / "cli.py"
    if cli_file.exists():
        content = cli_file.read_text()
        # Match add_parser("command_name") patterns
        for m in re.finditer(r'add_parser\(\s*["\'](\w+)["\']', content):
            surface["cli_subcommands"].append(m.group(1))

    # 3. REST endpoints
    rest_file = REPO_ROOT / "stateweave" / "rest_api.py"
    if rest_file.exists():
        content = rest_file.read_text()
        for m in re.finditer(r'self\.path\s*==\s*["\']([^"\']+)["\']', content):
            endpoint = m.group(1)
            if endpoint not in surface["rest_endpoints"]:
                surface["rest_endpoints"].append(endpoint)

    # 4. Adapter count
    adapter_dir = REPO_ROOT / "stateweave" / "adapters"
    if adapter_dir.exists():
        surface["adapter_count"] = len(list(adapter_dir.glob("*_adapter.py")))

    # 5. Test count
    test_count = 0
    for tf in (REPO_ROOT / "tests").rglob("*.py"):
        try:
            content = tf.read_text(errors="replace")
            test_count += len(re.findall(r"def test_", content))
        except Exception:
            pass
    surface["test_count"] = test_count

    return surface


def load_previous_surface():
    """Load the previous API surface snapshot."""
    if SNAPSHOT_FILE.exists():
        try:
            return json.loads(SNAPSHOT_FILE.read_text())
        except json.JSONDecodeError:
            return None
    return None


def save_surface(surface):
    """Save the current surface snapshot."""
    SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_FILE.write_text(json.dumps(surface, indent=2))


# ─── Diff: API Surface ──────────────────────────────────────────

def diff_api_surface(current, previous):
    if not args_global.json:
        print("\n━━ Differential: API Surface Changes ━━")

    if previous is None:
        info("No previous snapshot — this run establishes the baseline")
        return

    # Exported symbols
    curr_symbols = set(current.get("exported_symbols", []))
    prev_symbols = set(previous.get("exported_symbols", []))
    new_symbols = curr_symbols - prev_symbols
    removed_symbols = prev_symbols - curr_symbols

    if new_symbols:
        for s in sorted(new_symbols):
            warn(f"NEW exported symbol: {s}", "Attack surface expansion — review needed")
    if removed_symbols:
        for s in sorted(removed_symbols):
            info(f"REMOVED exported symbol: {s}")
    if not new_symbols and not removed_symbols:
        check("Exported symbols unchanged", True, f"{len(curr_symbols)} symbols")

    # CLI subcommands
    curr_cmds = set(current.get("cli_subcommands", []))
    prev_cmds = set(previous.get("cli_subcommands", []))
    new_cmds = curr_cmds - prev_cmds
    removed_cmds = prev_cmds - curr_cmds

    if new_cmds:
        for c in sorted(new_cmds):
            warn(f"NEW CLI subcommand: {c}", "New attack surface — needs adversarial testing")
    if removed_cmds:
        for c in sorted(removed_cmds):
            info(f"REMOVED CLI subcommand: {c}")
    if not new_cmds and not removed_cmds:
        check("CLI subcommands unchanged", True, f"{len(curr_cmds)} commands")

    # REST endpoints
    curr_eps = set(current.get("rest_endpoints", []))
    prev_eps = set(previous.get("rest_endpoints", []))
    new_eps = curr_eps - prev_eps

    if new_eps:
        for e in sorted(new_eps):
            warn(f"NEW REST endpoint: {e}", "New attack surface — needs adversarial testing")
    else:
        check("REST endpoints unchanged", True, f"{len(curr_eps)} endpoints")


# ─── Diff: Test Regression ───────────────────────────────────────

def diff_test_count(current, previous):
    if not args_global.json:
        print("\n━━ Differential: Test Regression ━━")

    if previous is None:
        info(f"Current test count: {current['test_count']} (no baseline)")
        return

    curr_count = current["test_count"]
    prev_count = previous.get("test_count", 0)
    delta = curr_count - prev_count

    if delta < 0:
        check(
            f"Test count regression: {prev_count} → {curr_count} ({delta})",
            False,
            f"{abs(delta)} tests removed since last snapshot"
        )
    elif delta > 0:
        check(
            f"Test count increased: {prev_count} → {curr_count} (+{delta})",
            True,
        )
    else:
        check(f"Test count stable: {curr_count}", True)


# ─── Diff: Adapter Regression ────────────────────────────────────

def diff_adapter_count(current, previous):
    if not args_global.json:
        print("\n━━ Differential: Adapter Count ━━")

    if previous is None:
        info(f"Current adapter count: {current['adapter_count']} (no baseline)")
        return

    curr = current["adapter_count"]
    prev = previous.get("adapter_count", 0)

    if curr < prev:
        check(
            f"Adapter count regression: {prev} → {curr}",
            False,
            f"{prev - curr} adapter(s) removed"
        )
    else:
        check(f"Adapter count stable: {curr}", True)


# ─── Diff: Failure Novelty ───────────────────────────────────────

def diff_failure_novelty():
    if not args_global.json:
        print("\n━━ Differential: Failure Novelty ━━")

    if not HISTORY_FILE.exists():
        info("No audit history found — skipping failure novelty analysis")
        return

    try:
        lines = HISTORY_FILE.read_text().strip().split("\n")
        if len(lines) < 2:
            info("Only 1 audit run in history — need ≥2 to compare")
            return

        current_run = json.loads(lines[-1])
        previous_run = json.loads(lines[-2])

        curr_failures = set(current_run.get("failures", []))
        prev_failures = set(previous_run.get("failures", []))

        new_failures = curr_failures - prev_failures
        fixed_failures = prev_failures - curr_failures
        recurring = curr_failures & prev_failures

        if new_failures:
            for f in sorted(new_failures):
                check(f"NEW failure: {f}", False, "Did not exist in previous run")
        if fixed_failures:
            for f in sorted(fixed_failures):
                check(f"FIXED: {f}", True, "Was failing, now passing")
        if recurring:
            for f in sorted(recurring):
                warn(f"RECURRING failure: {f}", "Still failing from previous run")

        if not new_failures and not recurring:
            check("No new or recurring failures", True)

        info(
            f"Trend: {len(new_failures)} new, {len(fixed_failures)} fixed, "
            f"{len(recurring)} recurring"
        )

    except (json.JSONDecodeError, IndexError, KeyError) as e:
        warn(f"Could not parse audit history: {e}")


# ─── Main ────────────────────────────────────────────────────────

def run_diff():
    """Run the full differential analysis. Returns results for integration."""
    global args_global

    # Create a mock args if called programmatically
    class MockArgs:
        json = False
        baseline = None

    if not hasattr(sys.modules[__name__], 'args_global') or args_global is None:
        args_global = MockArgs()

    current = capture_current_surface()
    previous = load_previous_surface()

    diff_api_surface(current, previous)
    diff_test_count(current, previous)
    diff_adapter_count(current, previous)
    diff_failure_novelty()

    # Save current as the new baseline
    save_surface(current)

    return results


def main():
    global args_global
    parser = argparse.ArgumentParser(description="StateWeave Differential Red Team")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--baseline", type=str, help="Path to baseline snapshot file")
    args_global = parser.parse_args()

    if not args_global.json:
        print("╔══════════════════════════════════════════════════════════╗")
        print("║        StateWeave Differential Red Team                 ║")
        print("╚══════════════════════════════════════════════════════════╝")

    run_diff()

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
            print("  VERDICT: 🔴 REGRESSIONS DETECTED")
        elif warns > 0:
            print("  VERDICT: 🟡 REVIEW CHANGES")
        else:
            print("  VERDICT: 🟢 NO REGRESSIONS")
        print("═" * 60)

    return 1 if fails > 0 else 0


args_global = None

if __name__ == "__main__":
    sys.exit(main())
