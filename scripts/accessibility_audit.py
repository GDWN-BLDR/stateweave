#!/usr/bin/env python3
"""
StateWeave Accessibility Audit
==================================
Headless browser audit of the StateWeave website for accessibility,
Core Web Vitals, mobile responsiveness, and link validation.

Usage:
    python scripts/accessibility_audit.py              # full audit
    python scripts/accessibility_audit.py --url URL    # custom URL
    python scripts/accessibility_audit.py --json       # JSON output

Requires:
    pip install playwright && playwright install chromium
    Falls back to urllib-only link validation if Playwright not available.

Exit codes:
    0 = all checks pass
    1 = issues found
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = REPO_ROOT / "breakdown" / "screenshots"
DEFAULT_URL = "https://stateweave.pantollventures.com"

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


# ─── Phase 1: Link Validation (no browser needed) ───────────────

def phase_link_validation(url):
    if not args_global.json:
        print("\n━━ Accessibility: Link Validation ━━")

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "stateweave-audit/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        check("Website reachable", False, str(e))
        return

    check("Website reachable", True)

    # Extract all links
    links = re.findall(r'href="(https?://[^"]+)"', html)
    internal_links = [l for l in links if "stateweave" in l or "pantollventures" in l]
    external_links = [l for l in links if l not in internal_links]

    broken = []
    checked = set()

    for link in internal_links[:20]:  # Cap at 20 to avoid abuse
        if link in checked:
            continue
        checked.add(link)
        try:
            req = urllib.request.Request(
                link, method="HEAD",
                headers={"User-Agent": "stateweave-audit/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status >= 400:
                    broken.append(f"{link} ({resp.status})")
        except Exception as e:
            broken.append(f"{link} ({e})")

    if broken:
        for b in broken:
            check(f"Broken link: {b}", False)
    else:
        check(f"All {len(checked)} internal links valid", True)

    # Check for common SEO elements
    check("Has <title> tag", "<title>" in html.lower())
    check("Has meta description", 'name="description"' in html.lower())
    check("Has og:image", 'og:image' in html)
    check("Has viewport meta", 'name="viewport"' in html.lower())

    # Check heading hierarchy
    h1_count = len(re.findall(r'<h1[^>]*>', html, re.I))
    check("Single <h1> tag", h1_count == 1, f"Found {h1_count}")


# ─── Phase 2: Playwright-Based Audits ────────────────────────────

def phase_browser_audit(url):
    """Run browser-based audits if Playwright is available."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        warn(
            "Playwright not installed — skipping browser-based audits",
            "Install with: pip install playwright && playwright install chromium"
        )
        return

    if not args_global.json:
        print("\n━━ Accessibility: Browser Audit (Playwright) ━━")

    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    viewports = [
        ("mobile", 375, 812),
        ("tablet", 768, 1024),
        ("desktop", 1440, 900),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for name, width, height in viewports:
            if not args_global.json:
                print(f"\n  ── Viewport: {name} ({width}×{height}) ──")

            context = browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=2 if name == "mobile" else 1,
            )
            page = context.new_page()

            try:
                response = page.goto(url, wait_until="networkidle", timeout=30000)
                check(f"{name}: page loads", response.status == 200, f"HTTP {response.status}")

                # Screenshot
                screenshot_path = SCREENSHOT_DIR / f"redteam_{name}.png"
                page.screenshot(path=str(screenshot_path), full_page=True)
                info(f"{name}: screenshot saved", str(screenshot_path))

                # Check for horizontal scroll (layout break)
                has_hscroll = page.evaluate("""
                    () => document.documentElement.scrollWidth > document.documentElement.clientWidth
                """)
                check(f"{name}: no horizontal scroll", not has_hscroll)

                # Core Web Vitals (LCP approximation)
                try:
                    lcp_ms = page.evaluate("""
                        () => {
                            return new Promise((resolve) => {
                                new PerformanceObserver((list) => {
                                    const entries = list.getEntries();
                                    resolve(entries[entries.length - 1]?.startTime || 0);
                                }).observe({type: 'largest-contentful-paint', buffered: true});
                                setTimeout(() => resolve(-1), 5000);
                            });
                        }
                    """)
                    if lcp_ms > 0:
                        check(
                            f"{name}: LCP < 2.5s",
                            lcp_ms < 2500,
                            f"{lcp_ms:.0f}ms"
                        )
                    else:
                        info(f"{name}: LCP measurement timed out")
                except Exception:
                    info(f"{name}: Could not measure LCP")

                # CLS approximation
                try:
                    cls_value = page.evaluate("""
                        () => {
                            return new Promise((resolve) => {
                                let clsValue = 0;
                                new PerformanceObserver((list) => {
                                    for (const entry of list.getEntries()) {
                                        if (!entry.hadRecentInput) {
                                            clsValue += entry.value;
                                        }
                                    }
                                }).observe({type: 'layout-shift', buffered: true});
                                setTimeout(() => resolve(clsValue), 3000);
                            });
                        }
                    """)
                    check(
                        f"{name}: CLS < 0.1",
                        cls_value < 0.1,
                        f"{cls_value:.3f}"
                    )
                except Exception:
                    info(f"{name}: Could not measure CLS")

                # Axe-core accessibility audit
                try:
                    # Inject axe-core
                    axe_source = """
                    (function(){if(window.axe)return;var s=document.createElement('script');
                    s.src='https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js';
                    s.onload=function(){window.__axeLoaded=true;};document.head.appendChild(s);})()
                    """
                    page.evaluate(axe_source)
                    page.wait_for_function("window.__axeLoaded === true", timeout=10000)

                    axe_results = page.evaluate("""
                        () => axe.run().then(results => ({
                            violations: results.violations.map(v => ({
                                id: v.id,
                                impact: v.impact,
                                description: v.description,
                                nodes: v.nodes.length,
                            })),
                            passes: results.passes.length,
                        }))
                    """)

                    violations = axe_results.get("violations", [])
                    critical = [v for v in violations if v["impact"] in ("critical", "serious")]
                    moderate = [v for v in violations if v["impact"] == "moderate"]

                    if critical:
                        for v in critical:
                            check(
                                f"{name}: a11y {v['impact']}: {v['id']}",
                                False,
                                f"{v['description']} ({v['nodes']} elements)"
                            )
                    else:
                        check(f"{name}: no critical a11y violations", True)

                    if moderate:
                        for v in moderate[:3]:  # Cap at 3
                            warn(f"{name}: a11y moderate: {v['id']}", v['description'][:60])

                    info(f"{name}: {axe_results.get('passes', 0)} a11y rules passed")

                except Exception as e:
                    warn(f"{name}: axe-core audit failed", str(e)[:100])

            except Exception as e:
                check(f"{name}: page loads", False, str(e)[:100])
            finally:
                context.close()

        browser.close()


# ─── Main ────────────────────────────────────────────────────────

def run_accessibility_audit(url=None, json_output=False):
    """Run the audit programmatically. Returns results list."""
    global args_global

    class Args:
        pass

    args_global = Args()
    args_global.json = json_output
    args_global.url = url or DEFAULT_URL

    phase_link_validation(args_global.url)
    phase_browser_audit(args_global.url)

    return results


def main():
    global args_global
    parser = argparse.ArgumentParser(description="StateWeave Accessibility Audit")
    parser.add_argument("--url", default=DEFAULT_URL, help="Website URL to audit")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args_global = parser.parse_args()

    if not args_global.json:
        print("╔══════════════════════════════════════════════════════════╗")
        print("║        StateWeave Accessibility Audit                   ║")
        print("╚══════════════════════════════════════════════════════════╝")

    phase_link_validation(args_global.url)
    phase_browser_audit(args_global.url)

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
        if fails:
            print("  VERDICT: 🔴 ACCESSIBILITY ISSUES FOUND")
        elif warns:
            print("  VERDICT: 🟡 REVIEW WARNINGS")
        else:
            print("  VERDICT: 🟢 ACCESSIBLE")
        print("═" * 60)

    return 1 if fails > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
