#!/usr/bin/env python3
"""
STATEWEAVE Universal Compliance Engine (UCE)
=============================================
[BOARD 2026-03-13] Total Compliance Architecture

The single binary that enforces ALL compliance dimensions.
Plugin-based architecture with auto-discovered scanners.

Usage:
    python scripts/uce.py                    # Full run, stdout report
    python scripts/uce.py --mode=CI          # CI mode, exit 1 on BLOCK failure
    python scripts/uce.py --json             # JSON scorecard output
    python scripts/uce.py --scanner=NAME     # Run single scanner
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

# Resolve project root (parent of scripts/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

from stateweave.compliance.registry import discover_scanners, get_enabled_scanners, load_rules
from stateweave.compliance.scanner_base import Mode, ScanResult


def run_scanners(project_root: str, args) -> dict:
    """Run all enabled scanners and produce a scorecard."""
    print("=" * 60)
    print("🧶  STATEWEAVE Universal Compliance Engine (UCE v1.0)")
    print("=" * 60)

    # Load rules
    rules = load_rules(project_root)
    global_mode = rules.get("global", {}).get("mode", "STRICT")
    print(f"  📜 Mode: {global_mode}")

    # Discover scanners
    scanners = discover_scanners(project_root)
    print(f"  🔌 Discovered: {len(scanners)} scanner(s)")

    # Filter to enabled + optionally single scanner
    enabled = get_enabled_scanners(scanners, rules)
    if args.scanner:
        enabled = [(s, c) for s, c in enabled if s.name == args.scanner]
        if not enabled:
            print(f"  ❌ Scanner '{args.scanner}' not found or not enabled")
            return {"passed": False, "scanners": []}

    print(f"  ✅ Enabled: {len(enabled)} scanner(s)")
    print()

    # Run each scanner
    results = []
    block_failures = 0
    warn_count = 0
    start_time = time.time()

    for scanner, config in enabled:
        try:
            result = scanner.scan(config, project_root)
            results.append(result)

            # Count failures by mode
            if not result.passed:
                if result.mode == Mode.BLOCK:
                    block_failures += 1
                else:
                    warn_count += 1

            # Print result
            icon = "✅" if result.passed else ("❌" if result.mode == Mode.BLOCK else "⚠️")
            mode_tag = f"[{result.mode.value}]"
            print(f"  {icon} {result.scanner_name:<35} {mode_tag}")

            if not result.passed:
                for v in result.violations[:5]:
                    loc = f"{v.file}"
                    if v.line:
                        loc += f":{v.line}"
                    print(f"     └─ {loc}: {v.message}")
                if len(result.violations) > 5:
                    print(f"     └─ ... and {len(result.violations) - 5} more violations")

        except Exception as e:
            print(f"  💥 {scanner.name}: CRASH — {e}")
            results.append(
                ScanResult(
                    scanner_name=scanner.name,
                    passed=False,
                    mode=Mode.BLOCK,
                    violations=[],
                    stats={"error": str(e)},
                )
            )
            block_failures += 1

    elapsed = time.time() - start_time

    # Build scorecard
    total = len(results)
    passed = sum(1 for r in results if r.passed)

    scorecard = {
        "timestamp": datetime.now().isoformat(),
        "engine_version": "1.0",
        "global_mode": global_mode,
        "total_scanners": total,
        "passed": passed,
        "block_failures": block_failures,
        "warnings": warn_count,
        "elapsed_seconds": round(elapsed, 2),
        "overall_pass": block_failures == 0 and warn_count == 0,
        "scanners": [r.to_dict() for r in results],
    }

    # Print summary
    print()
    print("=" * 60)
    print(f"📊 UCE SCORECARD: {passed}/{total} scanners PASSED")
    if warn_count:
        print(f"   ⚠️  {warn_count} WARN-mode issue(s)")
    print(f"   ⏱️  Completed in {elapsed:.1f}s")
    print()

    if block_failures > 0:
        print(f"❌ COMPLIANCE FAILURE — {block_failures} BLOCK-mode scanner(s) failed")
        print("   Deployment is FORBIDDEN until violations are resolved.")
    elif warn_count > 0:
        print(f"⚠️  COMPLIANCE WARNING — {warn_count} WARN-mode scanner(s) have violations")
        print("   [BOARD 2026-03-13] WARN violations should be addressed at next session.")
    else:
        print("✅ ALL SCANNERS PASSED — Deployment permitted")

    return scorecard


def main():
    parser = argparse.ArgumentParser(description="STATEWEAVE Universal Compliance Engine")
    parser.add_argument(
        "--mode",
        choices=["CI", "local"],
        default="local",
        help="CI mode exits with non-zero on BLOCK failure",
    )
    parser.add_argument("--json", action="store_true", help="Output JSON scorecard")
    parser.add_argument("--scanner", type=str, default=None, help="Run a single scanner by name")
    args = parser.parse_args()

    scorecard = run_scanners(PROJECT_ROOT, args)

    # JSON output
    if args.json:
        print("\n--- JSON SCORECARD ---")
        print(json.dumps(scorecard, indent=2))

    # Exit code
    if args.mode == "CI" or True:  # Always enforce exit codes
        if not scorecard.get("overall_pass", False):
            sys.exit(1)
        sys.exit(0)


if __name__ == "__main__":
    main()
