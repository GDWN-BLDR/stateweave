"""
StateWeave CLI — Command-line interface for state operations.
===============================================================
Provides export, import, diff, and version commands.

Usage:
    stateweave version
    stateweave export --framework langgraph --agent-id my-agent [--encrypt]
    stateweave import --framework mcp --payload state.json
    stateweave diff state_a.json state_b.json
"""

import argparse
import json
import logging
import sys

import stateweave
from stateweave.adapters import ADAPTER_REGISTRY
from stateweave.core.detect import detect_framework
from stateweave.core.diff import diff_payloads
from stateweave.core.encryption import EncryptionFacade
from stateweave.core.migration import MigrationEngine
from stateweave.core.serializer import StateWeaveSerializer

logger = logging.getLogger("stateweave.cli")

ADAPTERS = ADAPTER_REGISTRY


def cmd_version(args):
    """Print version information."""
    print(f"stateweave {stateweave.__version__}")
    print(f"Python {sys.version.split()[0]}")
    print(f"Adapters: {len(ADAPTERS)} frameworks ({', '.join(sorted(ADAPTERS.keys()))})")

    # Encryption availability
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401

        print("Encryption: AES-256-GCM ✓")
    except ImportError:
        print("Encryption: not available (pip install cryptography)")

    # Checkpoint store
    from stateweave.core.timetravel import CheckpointStore

    store = CheckpointStore()
    agents = store.list_agents()
    if agents:
        print(f"Checkpoint store: {len(agents)} agent(s) ({', '.join(agents[:5])})")
    else:
        print("Checkpoint store: empty")


def cmd_export(args):
    """Export agent state to a JSON file."""
    if args.framework not in ADAPTERS:
        print(f"Error: Unknown framework '{args.framework}'", file=sys.stderr)
        print(f"Available: {', '.join(ADAPTERS.keys())}", file=sys.stderr)
        sys.exit(1)

    adapter = ADAPTERS[args.framework]()
    serializer = StateWeaveSerializer(pretty=True)

    encryption = None
    if args.encrypt:
        passphrase = args.passphrase or input("Enter encryption passphrase: ")
        encryption = EncryptionFacade.from_passphrase(passphrase)

    engine = MigrationEngine(serializer=serializer, encryption=encryption)

    try:
        result = engine.export_state(
            adapter=adapter,
            agent_id=args.agent_id,
            encrypt=args.encrypt,
        )
    except Exception as e:
        print(f"Export failed: {e}", file=sys.stderr)
        sys.exit(1)

    if not result.success:
        print(f"Export failed: {result.error}", file=sys.stderr)
        sys.exit(1)

    payload_dict = serializer.to_dict(result.payload)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(payload_dict, f, indent=2, default=str)
        print(f"Exported to {args.output}")
    else:
        print(json.dumps(payload_dict, indent=2, default=str))

    # Print warnings
    if result.payload.non_portable_warnings:
        print(
            f"\n⚠️  {len(result.payload.non_portable_warnings)} non-portable warnings:",
            file=sys.stderr,
        )
        for w in result.payload.non_portable_warnings:
            print(f"  [{w.severity.value}] {w.field}: {w.reason}", file=sys.stderr)


def cmd_import(args):
    """Import agent state from a JSON file."""
    if args.framework not in ADAPTERS:
        print(f"Error: Unknown framework '{args.framework}'", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.payload, "r") as f:
            payload_dict = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {args.payload}", file=sys.stderr)
        sys.exit(1)

    adapter = ADAPTERS[args.framework]()
    serializer = StateWeaveSerializer()
    engine = MigrationEngine(serializer=serializer)

    payload = serializer.from_dict(payload_dict)

    kwargs = {}
    if args.agent_id:
        kwargs["agent_id"] = args.agent_id

    try:
        result = engine.import_state(adapter=adapter, payload=payload, **kwargs)
    except Exception as e:
        print(f"Import failed: {e}", file=sys.stderr)
        sys.exit(1)

    if result.success:
        print(f"✅ Successfully imported into {args.framework}")
        print(f"   Messages: {len(payload.cognitive_state.conversation_history)}")
        print(f"   Working memory keys: {len(payload.cognitive_state.working_memory)}")
    else:
        print(f"Import failed: {result.error}", file=sys.stderr)
        sys.exit(1)


def cmd_diff(args):
    """Diff two state files."""
    serializer = StateWeaveSerializer()

    try:
        with open(args.state_a, "r") as f:
            dict_a = json.load(f)
        with open(args.state_b, "r") as f:
            dict_b = json.load(f)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    payload_a = serializer.from_dict(dict_a)
    payload_b = serializer.from_dict(dict_b)

    diff = diff_payloads(payload_a, payload_b)
    print(diff.to_report())


def cmd_validate(args):
    """Validate a StateWeavePayload JSON file."""
    serializer = StateWeaveSerializer()

    try:
        with open(args.payload, "r") as f:
            payload_dict = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {args.payload}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    from stateweave.schema.validator import validate_payload

    is_valid, errors = validate_payload(payload_dict)

    if is_valid:
        payload = serializer.from_dict(payload_dict)
        print("✅ Valid StateWeavePayload")
        print(f"   Version: {payload.stateweave_version}")
        print(f"   Framework: {payload.source_framework}")
        print(f"   Agent: {payload.metadata.agent_id}")
        print(f"   Messages: {len(payload.cognitive_state.conversation_history)}")
        print(f"   Working memory keys: {len(payload.cognitive_state.working_memory)}")
        if payload.non_portable_warnings:
            print(f"   ⚠️  Warnings: {len(payload.non_portable_warnings)}")
    else:
        print("❌ Invalid payload:", file=sys.stderr)
        for err in errors:
            print(f"   • {err}", file=sys.stderr)
        sys.exit(1)


def cmd_schema(args):
    """Dump the Universal Schema as JSON Schema."""
    from stateweave.schema.validator import get_schema_json

    schema = get_schema_json()

    if args.output:
        with open(args.output, "w") as f:
            json.dump(schema, f, indent=2)
        print(f"Schema written to {args.output}")
    else:
        print(json.dumps(schema, indent=2))


def cmd_detect(args):
    """Auto-detect the source framework of a state file."""
    results = detect_framework(args.input_file, top_n=5)

    print("Framework Detection Results:")
    print("─" * 40)
    for framework, confidence in results:
        bar = "█" * int(confidence * 20) + "░" * (20 - int(confidence * 20))
        print(f"  {framework:<20} {bar} {confidence:.0%}")

    if results:
        best = results[0]
        print(f"\n✓ Best match: {best[0]} ({best[1]:.0%} confidence)")


def cmd_adapters(args):
    """List all available framework adapters."""
    print("Available Framework Adapters:")
    print("─" * 50)
    for name, cls in sorted(ADAPTERS.items()):
        print(f"  {name:<20} {cls.__name__}")
    print(f"\nTotal: {len(ADAPTERS)} adapters")


def cmd_generate_adapter(args):
    """Generate a scaffold for a new framework adapter."""
    from stateweave.core.generator import generate_adapter_scaffold

    result = generate_adapter_scaffold(
        args.framework_name,
        output_dir=args.output_dir,
    )

    print(f"✓ Generated adapter scaffold for '{args.framework_name}':")
    for path in result["files"]:
        print(f"  → {path}")


def cmd_scan(args):
    """Scan environment for installed agent frameworks."""
    from stateweave.core.environment import scan_environment

    scan = scan_environment()
    print(scan.to_report())


def cmd_checkpoint(args):
    """Save a checkpoint of agent state."""
    from stateweave.core.timetravel import CheckpointStore

    serializer = StateWeaveSerializer()

    try:
        with open(args.payload, "r") as f:
            payload_dict = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {args.payload}", file=sys.stderr)
        sys.exit(1)

    payload = serializer.from_dict(payload_dict)
    store = CheckpointStore(
        store_dir=args.store_dir if hasattr(args, "store_dir") and args.store_dir else None
    )

    cp = store.checkpoint(
        payload=payload,
        agent_id=args.agent_id if hasattr(args, "agent_id") and args.agent_id else None,
        label=args.label if hasattr(args, "label") and args.label else None,
    )

    print(f"✓ Checkpoint v{cp.version} saved for '{cp.agent_id}'")
    print(f"  Hash: {cp.hash[:16]}...")
    print(f"  Messages: {cp.message_count}")
    print(f"  Working memory keys: {cp.working_memory_keys}")


def cmd_history(args):
    """Show checkpoint history for an agent."""
    from stateweave.core.timetravel import CheckpointStore

    store = CheckpointStore(
        store_dir=args.store_dir if hasattr(args, "store_dir") and args.store_dir else None
    )
    print(store.format_history(args.agent_id))


def cmd_rollback(args):
    """Restore a previous checkpoint."""
    from stateweave.core.timetravel import CheckpointStore

    store = CheckpointStore(
        store_dir=args.store_dir if hasattr(args, "store_dir") and args.store_dir else None
    )
    serializer = StateWeaveSerializer(pretty=True)

    try:
        payload = store.rollback(args.agent_id, args.version)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    payload_dict = serializer.to_dict(payload)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(payload_dict, f, indent=2, default=str)
        print(f"✓ Restored v{args.version} → {args.output}")
    else:
        print(json.dumps(payload_dict, indent=2, default=str))


def cmd_doctor(args):
    """Run diagnostic health checks."""
    from stateweave.core.doctor import run_doctor

    report = run_doctor()
    print(report.format())


def cmd_why(args):
    """Analyze an agent's checkpoint history to explain what happened.

    Produces an autopsy-style report showing what changed at each step,
    highlighting the most significant state transitions.
    """
    from stateweave.core.timetravel import CheckpointStore

    store = CheckpointStore(
        store_dir=args.store_dir if hasattr(args, "store_dir") and args.store_dir else None
    )

    # Load history
    history = store.history(args.agent_id)

    if not history.checkpoints:
        print(f"No checkpoints found for agent '{args.agent_id}'")
        print()
        agents = store.list_agents()
        if agents:
            print(f"Available agents: {', '.join(agents)}")
        else:
            print("No agents have been checkpointed yet.")
            print("Use: stateweave checkpoint state.json")
        sys.exit(1)

    print("🔍 StateWeave Autopsy")
    print("═" * 60)
    print(f"  Agent:       {args.agent_id}")
    print(f"  Checkpoints: {history.version_count}")
    print(f"  Branches:    {', '.join(history.branches.keys())}")

    latest = history.latest
    if latest:
        print(f"  Latest:      v{latest.version} ({latest.created_at[:19]})")
        print(f"  Messages:    {latest.message_count}")
        print(f"  Memory keys: {latest.working_memory_keys}")
    print()

    # Analyze consecutive diffs
    if history.version_count < 2:
        print("  Only 1 checkpoint — nothing to compare.")
        print("  Create more checkpoints to see state evolution.")
        print("═" * 60)
        return

    print("📊 State Evolution")
    print("─" * 60)

    sorted_cps = sorted(history.checkpoints, key=lambda c: c.version)
    significant_changes = []

    for i in range(1, len(sorted_cps)):
        prev_cp = sorted_cps[i - 1]
        curr_cp = sorted_cps[i]

        try:
            diff = store.diff_versions(args.agent_id, prev_cp.version, curr_cp.version)
        except (ValueError, Exception) as e:
            print(f"  v{prev_cp.version} → v{curr_cp.version}: ⚠ Could not diff ({e})")
            continue

        # Summarize changes
        change_icon = "📝" if diff.has_changes else "✅"
        delta_msgs = curr_cp.message_count - prev_cp.message_count
        delta_mem = curr_cp.working_memory_keys - prev_cp.working_memory_keys

        parts = []
        if delta_msgs:
            parts.append(f"msgs {'+' if delta_msgs > 0 else ''}{delta_msgs}")
        if delta_mem:
            parts.append(f"mem {'+' if delta_mem > 0 else ''}{delta_mem}")
        if diff.added_count:
            parts.append(f"+{diff.added_count} added")
        if diff.removed_count:
            parts.append(f"-{diff.removed_count} removed")
        if diff.modified_count:
            parts.append(f"~{diff.modified_count} modified")

        label = f" — {curr_cp.label}" if curr_cp.label else ""
        delta_str = f" ({', '.join(parts)})" if parts else ""

        print(f"  {change_icon} v{prev_cp.version} → v{curr_cp.version}{label}{delta_str}")

        # Show individual diff entries for detail
        if diff.has_changes and args.verbose:
            for entry in diff.entries[:10]:  # Cap at 10 per transition
                print(f"       {entry}")
            if len(diff.entries) > 10:
                print(f"       ... and {len(diff.entries) - 10} more changes")

        if diff.has_changes:
            significant_changes.append(
                {
                    "from_v": prev_cp.version,
                    "to_v": curr_cp.version,
                    "label": curr_cp.label,
                    "changes": len(diff.entries),
                    "added": diff.added_count,
                    "removed": diff.removed_count,
                    "modified": diff.modified_count,
                }
            )

    print()

    # Show diagnosis
    if significant_changes:
        biggest = max(significant_changes, key=lambda c: c["changes"])
        print("🩺 Diagnosis")
        print("─" * 60)
        print(
            f"  Biggest change: v{biggest['from_v']} → v{biggest['to_v']} ({biggest['changes']} changes)"
        )
        if biggest.get("label"):
            print(f"  Label: {biggest['label']}")
        print(
            f"  Breakdown: +{biggest['added']} added, -{biggest['removed']} removed, ~{biggest['modified']} modified"
        )
        print()
        print("  💡 Recommendations:")
        print(
            f"     • Run: stateweave diff <v{biggest['from_v']}.json> <v{biggest['to_v']}.json> for full details"
        )
        print(f"     • Run: stateweave rollback {args.agent_id} {biggest['from_v']} to revert")
    else:
        print("  ✅ No significant state changes detected.")

    print("═" * 60)


def cmd_quickstart(args):
    """Run an instant demo of StateWeave — no code required.

    Creates a sample agent, checkpoints it, modifies state,
    checkpoints again, then shows the diff and analysis.
    """
    import tempfile

    from stateweave.core.timetravel import CheckpointStore
    from stateweave.schema.v1 import Message

    fw = args.framework if hasattr(args, "framework") and args.framework else "langgraph"
    if fw not in ADAPTERS:
        print(f"Error: Unknown framework '{fw}'", file=sys.stderr)
        print(f"Available: {', '.join(sorted(ADAPTERS.keys()))}", file=sys.stderr)
        sys.exit(1)

    adapter = ADAPTERS[fw]()
    agent_id = "quickstart-agent"

    print("🧶 StateWeave Quickstart")
    print("═" * 60)
    print(f"  Framework: {fw}")
    print()

    # Step 1: Create sample payload
    print("━━ Step 1: Create sample agent state ━━")
    payload = adapter.create_sample_payload(agent_id=agent_id, num_messages=3)
    print(f"  ✓ Agent: {payload.metadata.agent_id}")
    print(f"  ✓ Messages: {len(payload.cognitive_state.conversation_history)}")
    print(f"  ✓ Working memory: {list(payload.cognitive_state.working_memory.keys())}")
    print()

    # Step 2: Checkpoint
    print("━━ Step 2: Checkpoint (like git commit) ━━")
    with tempfile.TemporaryDirectory() as tmp_dir:
        store = CheckpointStore(store_dir=tmp_dir)
        cp1 = store.checkpoint(payload, agent_id=agent_id, label="initial state")
        print(f"  ✓ v{cp1.version} saved (hash: {cp1.hash[:16]}...)")
        print()

        # Step 3: Modify state
        print("━━ Step 3: Simulate agent work ━━")
        payload.cognitive_state.conversation_history.append(
            Message(role="human", content="Show me a chart of the trends")
        )
        payload.cognitive_state.conversation_history.append(
            Message(
                role="assistant",
                content="Here's the trend analysis. Electronics grew 15% QoQ.",
            )
        )
        payload.cognitive_state.working_memory["chart_generated"] = True
        payload.cognitive_state.working_memory["confidence"] = 0.95
        print("  ✓ Added 2 messages, updated working memory")
        print(f"  ✓ Messages now: {len(payload.cognitive_state.conversation_history)}")
        print()

        # Step 4: Checkpoint again
        print("━━ Step 4: Checkpoint again ━━")
        cp2 = store.checkpoint(payload, agent_id=agent_id, label="after analysis")
        print(f"  ✓ v{cp2.version} saved (hash: {cp2.hash[:16]}...)")
        print()

        # Step 5: Diff
        print("━━ Step 5: Diff the two versions ━━")
        diff = store.diff_versions(agent_id, 1, 2)
        print(
            f"  Changes: {len(diff.entries)} "
            f"(+{diff.added_count} added, ~{diff.modified_count} modified)"
        )
        for entry in diff.entries[:5]:
            print(f"    {entry}")
        print()

        # Step 6: Rollback
        print("━━ Step 6: Rollback to v1 ━━")
        restored = store.rollback(agent_id, version=1)
        print(f"  ✓ Restored v1: {len(restored.cognitive_state.conversation_history)} messages")
        print(f"  ✓ Working memory: {list(restored.cognitive_state.working_memory.keys())}")
        print()

    print("═" * 60)
    print("  ✅ Quickstart complete!")
    print()
    print("  Next steps:")
    print("    stateweave doctor          — check your environment")
    print("    stateweave adapters         — list all 10 framework adapters")
    print("    stateweave why <agent-id>   — analyze checkpoint history")
    print("═" * 60)


def cmd_init(args):
    """Initialize StateWeave in the current project.

    Creates a .stateweave/ directory with config.toml containing
    sensible defaults for framework, encryption, and checkpointing.
    """
    from pathlib import Path

    project_dir = Path(args.directory or ".")
    sw_dir = project_dir / ".stateweave"
    config_path = sw_dir / "config.toml"

    if config_path.exists():
        print("⚠ StateWeave already initialized in this project.")
        print(f"  Config: {config_path.resolve()}")
        return

    sw_dir.mkdir(parents=True, exist_ok=True)

    framework = args.framework if hasattr(args, "framework") and args.framework else "langgraph"

    config_content = f"""# StateWeave Configuration
# Generated by stateweave init
# Docs: https://stateweave.pantollventures.com

[project]
default_framework = "{framework}"
checkpoint_dir = ".stateweave/checkpoints"

[encryption]
enabled = false
algorithm = "AES-256-GCM"
# Uncomment to enable encryption:
# passphrase_env = "STATEWEAVE_PASSPHRASE"

[signing]
enabled = false
algorithm = "Ed25519"

[export]
strip_credentials = true
add_non_portable_warnings = true
include_audit_trail = true
"""

    config_path.write_text(config_content)

    # Create checkpoints dir
    (sw_dir / "checkpoints").mkdir(exist_ok=True)

    # Add .stateweave/checkpoints to .gitignore if not already there
    gitignore_path = project_dir / ".gitignore"
    gitignore_entry = ".stateweave/checkpoints/"
    if gitignore_path.exists():
        existing = gitignore_path.read_text()
        if gitignore_entry not in existing:
            with open(gitignore_path, "a") as f:
                f.write(f"\n# StateWeave checkpoint data\n{gitignore_entry}\n")
            print(f"  ✓ Added {gitignore_entry} to .gitignore")
    else:
        gitignore_path.write_text(f"# StateWeave checkpoint data\n{gitignore_entry}\n")
        print(f"  ✓ Created .gitignore with {gitignore_entry}")

    print("🧶 StateWeave initialized!")
    print(f"  ✓ Config: {config_path.resolve()}")
    print(f"  ✓ Checkpoint dir: {(sw_dir / 'checkpoints').resolve()}")
    print(f"  ✓ Default framework: {framework}")
    print()
    print("  Next steps:")
    print("    stateweave quickstart       — try it in 30 seconds")
    print("    stateweave doctor           — check your environment")
    print("    stateweave export -f langgraph -a my-agent  — export state")


def cmd_replay(args):
    """Step-by-step replay of an agent's checkpoint history.

    Like a debugger for agent cognition — shows what changed at each step,
    tracks confidence drift, and alerts on anomalies.
    """
    from stateweave.core.replay import ReplayEngine
    from stateweave.core.timetravel import CheckpointStore

    store_dir = args.store_dir if hasattr(args, "store_dir") and args.store_dir else None
    store = CheckpointStore(store_dir=store_dir)
    engine = ReplayEngine(store)

    from_v = getattr(args, "from_version", None)
    to_v = getattr(args, "to_version", None)

    result = engine.replay(args.agent_id, from_version=from_v, to_version=to_v)

    if not result.steps:
        print(f"⚠ No checkpoints found for '{args.agent_id}'")
        return

    print()
    print(f"⏪ Replaying: {result.agent_id} ({result.total_versions} checkpoints)")
    print("═" * 60)

    for i, step in enumerate(result.steps):
        conf_str = ""
        if step.confidence is not None:
            if i > 0 and result.steps[i - 1].confidence is not None:
                prev_conf = result.steps[i - 1].confidence
                if step.confidence < prev_conf:
                    conf_str = f" │ 🎯 {step.confidence:.2f} ↓"
                elif step.confidence > prev_conf:
                    conf_str = f" │ 🎯 {step.confidence:.2f} ↑"
                else:
                    conf_str = f" │ 🎯 {step.confidence:.2f}"
            else:
                conf_str = f" │ 🎯 {step.confidence:.2f}"

        print()
        print(
            f"  [v{step.version}] {step.label or 'unnamed'}"
            f"    📝 {step.message_count} msgs"
            f" │ 🧠 {step.working_memory_keys} keys"
            f"{conf_str}"
        )
        print("  " + "─" * 56)

        # Changes (skip for first step unless verbose)
        if i == 0:
            if step.message_count > 0:
                print(
                    f"    Initial state: {step.message_count} messages, {step.working_memory_keys} memory keys"
                )
        else:
            if step.messages_added:
                print(f"    + {step.messages_added} message(s) added")
            if step.messages_removed:
                print(f"    - {step.messages_removed} message(s) removed")
            for key in step.memory_added[:5]:
                print(f"    + mem: {key}")
            if len(step.memory_added) > 5:
                print(f"    + ... and {len(step.memory_added) - 5} more keys")
            for key in step.memory_removed[:5]:
                print(f"    - mem: {key}")
            for key, (old, new) in list(step.memory_changed.items())[:5]:
                old_s = str(old)[:30]
                new_s = str(new)[:30]
                print(f"    ~ mem: {key} {old_s} → {new_s}")
            if len(step.memory_changed) > 5:
                print(f"    ~ ... and {len(step.memory_changed) - 5} more changes")

        # Alerts
        for alert in step.alerts:
            print(f"    🔴 ALERT: {alert}")

    # Summary
    print()
    print("─" * 60)
    biggest = result.biggest_change_step
    if biggest and biggest.total_changes > 0:
        print(
            f"  Biggest change: v{biggest.version}"
            f" ({biggest.total_changes} changes)"
            f" {biggest.label or ''}"
        )

    # Confidence trend
    confs = [c for c in result.confidence_trend if c is not None]
    if len(confs) >= 2:
        trend = "📈" if confs[-1] > confs[0] else "📉" if confs[-1] < confs[0] else "➡️"
        print(f"  Confidence trend: {confs[0]:.2f} → {confs[-1]:.2f} {trend}")

    print("═" * 60)


def cmd_status(args):
    """Show health dashboard for all agents in the project.

    Like `git status` but for agent state — shows all tracked agents,
    their checkpoint count, message count, and health status.
    """
    from datetime import datetime

    from stateweave.core.timetravel import CheckpointStore

    store_dir = args.store_dir if hasattr(args, "store_dir") and args.store_dir else None
    store = CheckpointStore(store_dir=store_dir)

    # Find all agents
    root = store._root
    if not root.exists():
        print("⚠ No .stateweave/checkpoints/ directory found.")
        print("  Run: stateweave init")
        return

    agent_dirs = [d for d in root.iterdir() if d.is_dir() and (d / "manifest.json").exists()]

    if not agent_dirs:
        print("⚠ No agents tracked yet.")
        print("  Run: stateweave quickstart")
        return

    print()
    print("🧶 StateWeave Status")
    print("═" * 70)
    print(f"  Project: {root.resolve()}")
    print(f"  Agents:  {len(agent_dirs)} tracked")
    print()

    # Header
    print(
        f"  {'Agent':<22}│ {'v':>3} │ {'Msgs':>4} │ {'Memory':>7} │ {'Health':>8} │ Last Checkpoint"
    )
    print(
        "  "
        + "─" * 22
        + "┼"
        + "─" * 5
        + "┼"
        + "─" * 6
        + "┼"
        + "─" * 9
        + "┼"
        + "─" * 10
        + "┼"
        + "─" * 17
    )

    alerts = []
    now = datetime.utcnow()

    for agent_dir in sorted(agent_dirs):
        agent_id = agent_dir.name
        try:
            history = store.history(agent_id)
        except Exception:
            continue

        if not history.checkpoints:
            continue

        latest = history.latest
        if latest is None:
            continue

        # Calculate time ago
        try:
            cp_time = datetime.fromisoformat(latest.created_at)
            delta = now - cp_time
            if delta.total_seconds() < 60:
                time_ago = f"{int(delta.total_seconds())}s ago"
            elif delta.total_seconds() < 3600:
                time_ago = f"{int(delta.total_seconds() / 60)}m ago"
            elif delta.total_seconds() < 86400:
                time_ago = f"{int(delta.total_seconds() / 3600)}h ago"
            else:
                time_ago = f"{int(delta.total_seconds() / 86400)}d ago"
        except Exception:
            time_ago = latest.created_at[:16]
            delta = None

        # Health assessment
        health = "✅ OK"
        health_issues = []

        # Check for confidence drift
        if len(history.checkpoints) >= 2:
            try:
                latest_payload = store._load_payload(agent_id, latest.version)
                if latest_payload:
                    wm = latest_payload.cognitive_state.working_memory
                    conf = None
                    for key in ("confidence", "confidence_score", "agent_confidence"):
                        if key in wm:
                            try:
                                conf = float(wm[key])
                            except (ValueError, TypeError):
                                pass
                            break
                    if conf is not None and conf < 0.5:
                        health = "⚠ DRIFT"
                        health_issues.append(f"{agent_id}: confidence at {conf:.2f}")
                    if "hallucination_risk" in wm:
                        health = "🔴 RISK"
                        health_issues.append(f"{agent_id}: hallucination risk detected")
            except Exception:
                pass

        # Check for staleness
        if delta and delta.total_seconds() > 7200:  # 2 hours
            if health == "✅ OK":
                health = "⚠ STALE"
            health_issues.append(f"{agent_id}: no checkpoint in {time_ago}")

        name_display = agent_id[:22]
        print(
            f"  {name_display:<22}│ {latest.version:>3} "
            f"│ {latest.message_count:>4} "
            f"│ {latest.working_memory_keys:>4} keys"
            f" │ {health:<8}"
            f" │ {time_ago}"
        )

        alerts.extend(health_issues)

    if alerts:
        print()
        for alert in alerts:
            print(f"  ⚠ {alert}")

    print("═" * 70)


def cmd_compare(args):
    """Compare two checkpoints side-by-side.

    Supports comparing different versions of the same agent or
    checkpoints of different agents. Like git diff but for agent brains.

    Usage:
        stateweave compare agent:v3 agent:v5
        stateweave compare agent-a:latest agent-b:latest
    """
    from stateweave.core.diff import diff_payloads
    from stateweave.core.timetravel import CheckpointStore

    store_dir = args.store_dir if hasattr(args, "store_dir") and args.store_dir else None
    store = CheckpointStore(store_dir=store_dir)

    def parse_ref(ref):
        """Parse 'agent:version' format."""
        if ":" in ref:
            parts = ref.split(":", 1)
            agent_id = parts[0]
            version_str = parts[1]
            if version_str == "latest":
                history = store.history(agent_id)
                if history.latest:
                    return agent_id, history.latest.version
                raise ValueError(f"No checkpoints for '{agent_id}'")
            return agent_id, int(version_str.lstrip("v"))
        raise ValueError(f"Invalid ref '{ref}'. Use format: agent-id:v1 or agent-id:latest")

    try:
        left_agent, left_v = parse_ref(args.left)
        right_agent, right_v = parse_ref(args.right)
    except ValueError as e:
        print(f"⚠ {e}")
        return

    # Load payloads
    try:
        left_payload = store._load_payload(left_agent, left_v)
        right_payload = store._load_payload(right_agent, right_v)
    except Exception as e:
        print(f"⚠ Could not load checkpoints: {e}")
        return

    if left_payload is None or right_payload is None:
        print("⚠ One or both checkpoints not found.")
        return

    # Get metadata
    left_history = store.history(left_agent)
    right_history = store.history(right_agent)
    left_meta = left_history.get_version(left_v)
    right_meta = right_history.get_version(right_v)

    left_label = f"v{left_v}" + (f" ({left_meta.label})" if left_meta and left_meta.label else "")
    right_label = f"v{right_v}" + (
        f" ({right_meta.label})" if right_meta and right_meta.label else ""
    )

    print()
    print("📊 Side-by-Side Comparison")
    print("═" * 60)
    print()

    # Header
    col_w = 20
    print(f"  {'':20}│ {left_label:<{col_w}} │ {right_label:<{col_w}}")
    print("  " + "─" * 20 + "┼" + "─" * (col_w + 2) + "┼" + "─" * (col_w + 2))

    # Basic stats
    left_msgs = len(left_payload.cognitive_state.conversation_history)
    right_msgs = len(right_payload.cognitive_state.conversation_history)
    left_wm = len(left_payload.cognitive_state.working_memory)
    right_wm = len(right_payload.cognitive_state.working_memory)

    rows = [
        ("Messages", str(left_msgs), str(right_msgs)),
        ("Working Memory", f"{left_wm} keys", f"{right_wm} keys"),
        ("Framework", left_payload.source_framework, right_payload.source_framework),
    ]

    # Confidence
    left_conf = None
    right_conf = None
    for key in ("confidence", "confidence_score", "agent_confidence"):
        if key in left_payload.cognitive_state.working_memory:
            try:
                left_conf = float(left_payload.cognitive_state.working_memory[key])
            except (ValueError, TypeError):
                pass
        if key in right_payload.cognitive_state.working_memory:
            try:
                right_conf = float(right_payload.cognitive_state.working_memory[key])
            except (ValueError, TypeError):
                pass

    if left_conf is not None or right_conf is not None:
        left_c = f"{left_conf:.2f}" if left_conf is not None else "n/a"
        right_c = f"{right_conf:.2f}" if right_conf is not None else "n/a"
        if left_conf is not None and left_conf < 0.5:
            left_c += " 🔴"
        elif left_conf is not None:
            left_c += " ✅"
        if right_conf is not None and right_conf < 0.5:
            right_c += " 🔴"
        elif right_conf is not None:
            right_c += " ✅"
        rows.append(("Confidence", left_c, right_c))

    for label, left_val, right_val in rows:
        print(f"  {label:<20}│ {left_val:<{col_w}} │ {right_val:<{col_w}}")

    # Diff
    diff = diff_payloads(left_payload, right_payload)
    print()
    print("  Key Differences:")

    if not diff.has_changes:
        print("    ✅ States are identical")
    else:
        if diff.added_count:
            print(f"    + {diff.added_count} added")
        if diff.removed_count:
            print(f"    - {diff.removed_count} removed")
        if diff.modified_count:
            print(f"    ~ {diff.modified_count} modified")

        # Show key working memory diffs
        left_wm_dict = left_payload.cognitive_state.working_memory
        right_wm_dict = right_payload.cognitive_state.working_memory

        added_keys = set(right_wm_dict.keys()) - set(left_wm_dict.keys())
        removed_keys = set(left_wm_dict.keys()) - set(right_wm_dict.keys())
        changed_keys = {
            k
            for k in set(left_wm_dict.keys()) & set(right_wm_dict.keys())
            if left_wm_dict[k] != right_wm_dict[k]
        }

        print()
        for key in sorted(added_keys)[:5]:
            val = str(right_wm_dict[key])[:40]
            print(f"    + {right_label} has: {key}={val}")
        for key in sorted(removed_keys)[:5]:
            val = str(left_wm_dict[key])[:40]
            print(f"    - {left_label} has: {key}={val}")
        for key in sorted(changed_keys)[:5]:
            old_v = str(left_wm_dict[key])[:20]
            new_v = str(right_wm_dict[key])[:20]
            print(f"    ~ {key}: {old_v} → {new_v}")

    print()
    print("═" * 60)


def cmd_log(args):
    """Beautiful one-line checkpoint history — like `git log --oneline`.

    Shows every checkpoint with version, timestamp, label, message count,
    confidence, and a visual summary.
    """
    from datetime import datetime

    from stateweave.core.timetravel import CheckpointStore

    store_dir = args.store_dir if hasattr(args, "store_dir") and args.store_dir else None
    store = CheckpointStore(store_dir=store_dir)

    agent_id = args.agent_id
    history = store.history(agent_id)

    if not history.checkpoints:
        print(f"⚠ No checkpoints for '{agent_id}'")
        return

    sorted_cps = sorted(history.checkpoints, key=lambda c: c.version, reverse=True)
    limit = getattr(args, "limit", 20) or 20

    print()
    print(f"📜 {agent_id} — {len(sorted_cps)} checkpoint(s)")
    print()

    now = datetime.utcnow()

    for cp in sorted_cps[:limit]:
        # Time ago
        try:
            cp_time = datetime.fromisoformat(cp.created_at)
            delta = now - cp_time
            if delta.total_seconds() < 60:
                t = f"{int(delta.total_seconds())}s"
            elif delta.total_seconds() < 3600:
                t = f"{int(delta.total_seconds() / 60)}m"
            elif delta.total_seconds() < 86400:
                t = f"{int(delta.total_seconds() / 3600)}h"
            else:
                t = f"{int(delta.total_seconds() / 86400)}d"
        except Exception:
            t = "?"

        # Confidence from payload
        conf_str = ""
        try:
            payload = store._load_payload(agent_id, cp.version)
            if payload:
                wm = payload.cognitive_state.working_memory
                for key in ("confidence", "confidence_score", "agent_confidence"):
                    if key in wm:
                        try:
                            conf = float(wm[key])
                            bar_len = int(conf * 10)
                            bar = "█" * bar_len + "░" * (10 - bar_len)
                            icon = "🟢" if conf >= 0.7 else "🟡" if conf >= 0.4 else "🔴"
                            conf_str = f" {icon} {bar} {conf:.0%}"
                        except (ValueError, TypeError):
                            pass
                        break
        except Exception:
            pass

        # Hash (short)
        short_hash = cp.hash[:7] if cp.hash else "0000000"
        label = cp.label or "unlabeled"

        print(
            f"  {short_hash} v{cp.version:<3}"
            f"  {label:<20}"
            f"  📝{cp.message_count:>2} 🧠{cp.working_memory_keys:>2}"
            f"{conf_str}"
            f"  ({t} ago)"
        )

    if len(sorted_cps) > limit:
        print(f"\n  ... and {len(sorted_cps) - limit} more (use --limit)")

    print()


def cmd_blame(args):
    """Show which checkpoint introduced a specific working memory key.

    Like `git blame` — traces when a piece of agent knowledge first appeared,
    was last changed, and shows its value history.
    """
    from stateweave.core.timetravel import CheckpointStore

    store_dir = args.store_dir if hasattr(args, "store_dir") and args.store_dir else None
    store = CheckpointStore(store_dir=store_dir)

    agent_id = args.agent_id
    key = args.key
    history = store.history(agent_id)

    if not history.checkpoints:
        print(f"⚠ No checkpoints for '{agent_id}'")
        return

    sorted_cps = sorted(history.checkpoints, key=lambda c: c.version)

    print()
    print(f"🔍 Blame: {agent_id} → {key}")
    print("═" * 60)

    introduced_at = None
    last_changed_at = None
    prev_value = None
    value_history = []

    for cp in sorted_cps:
        try:
            payload = store._load_payload(agent_id, cp.version)
            if payload is None:
                continue
        except Exception:
            continue

        wm = payload.cognitive_state.working_memory
        current_value = wm.get(key)

        if current_value is not None:
            if introduced_at is None:
                introduced_at = cp.version
                value_history.append((cp.version, cp.label, current_value))

            if prev_value is not None and current_value != prev_value:
                last_changed_at = cp.version
                value_history.append((cp.version, cp.label, current_value))

            prev_value = current_value
        elif prev_value is not None:
            # Key was removed
            value_history.append((cp.version, cp.label, "[REMOVED]"))
            prev_value = None

    if introduced_at is None:
        print(f"  Key '{key}' not found in any checkpoint")
        return

    print(f"  Key:          {key}")
    print(f"  Introduced:   v{introduced_at}")
    if last_changed_at:
        print(f"  Last changed: v{last_changed_at}")
    print(f"  Current:      {str(prev_value)[:60]}")
    print()

    if len(value_history) > 1:
        print("  History:")
        for v, label, val in value_history:
            val_str = str(val)[:50]
            label_str = f" ({label})" if label else ""
            print(f"    v{v}{label_str}: {val_str}")

    print("═" * 60)


def cmd_stash(args):
    """Save current agent state to a named stash — like `git stash`.

    Saves a labeled snapshot that can be restored later with `stateweave pop`.
    """
    import json

    from stateweave.core.timetravel import CheckpointStore

    store_dir = args.store_dir if hasattr(args, "store_dir") and args.store_dir else None
    store = CheckpointStore(store_dir=store_dir)

    agent_id = args.agent_id
    stash_name = getattr(args, "name", None) or "default"
    history = store.history(agent_id)

    if not history.checkpoints or history.latest is None:
        print(f"⚠ No checkpoints for '{agent_id}'")
        return

    # Save stash reference
    stash_dir = store._root / ".stash"
    stash_dir.mkdir(parents=True, exist_ok=True)

    stash_file = stash_dir / f"{agent_id}_{stash_name}.json"
    stash_data = {
        "agent_id": agent_id,
        "stash_name": stash_name,
        "version": history.latest.version,
        "label": history.latest.label,
        "message_count": history.latest.message_count,
        "working_memory_keys": history.latest.working_memory_keys,
    }

    stash_file.write_text(json.dumps(stash_data, indent=2))

    print(f"📦 Stashed '{agent_id}' at v{history.latest.version} as '{stash_name}'")
    print(f"   Messages: {history.latest.message_count}")
    print(f"   Memory:   {history.latest.working_memory_keys} keys")
    print(f"   Restore:  stateweave pop {agent_id} --name {stash_name}")


def cmd_pop(args):
    """Restore a stashed agent state — like `git stash pop`.

    Restores the state saved by `stateweave stash`, rolling back to that version.
    """
    import json

    from stateweave.core.timetravel import CheckpointStore

    store_dir = args.store_dir if hasattr(args, "store_dir") and args.store_dir else None
    store = CheckpointStore(store_dir=store_dir)

    agent_id = args.agent_id
    stash_name = getattr(args, "name", None) or "default"

    stash_dir = store._root / ".stash"
    stash_file = stash_dir / f"{agent_id}_{stash_name}.json"

    if not stash_file.exists():
        print(f"⚠ No stash '{stash_name}' for '{agent_id}'")

        # List available stashes
        if stash_dir.exists():
            stashes = list(stash_dir.glob(f"{agent_id}_*.json"))
            if stashes:
                print("  Available stashes:")
                for s in stashes:
                    name = s.stem.replace(f"{agent_id}_", "")
                    print(f"    - {name}")
        return

    stash_data = json.loads(stash_file.read_text())
    version = stash_data["version"]

    try:
        restored = store.rollback(agent_id, version=version)
    except Exception as e:
        print(f"⚠ Could not restore: {e}")
        return

    print(f"📦 Popped '{stash_name}' → restored {agent_id} to v{version}")
    print(f"   Messages: {len(restored.cognitive_state.conversation_history)}")
    print(f"   Memory:   {len(restored.cognitive_state.working_memory)} keys")

    # Clean up stash file
    stash_file.unlink()
    print(f"   Stash '{stash_name}' removed")


def cmd_watch(args):
    """Live agent state dashboard — refreshes every N seconds.

    Like htop for agent brains. Shows all tracked agents with real-time
    health updates, message counts, and confidence tracking.
    """
    import signal
    import time
    from datetime import datetime

    from stateweave.core.timetravel import CheckpointStore

    store_dir = args.store_dir if hasattr(args, "store_dir") and args.store_dir else None
    store = CheckpointStore(store_dir=store_dir)
    interval = getattr(args, "interval", 2)

    # Handle Ctrl+C gracefully
    running = [True]

    def handle_sigint(sig, frame):
        running[0] = False

    signal.signal(signal.SIGINT, handle_sigint)

    print(f"🧶 StateWeave Watch (refreshing every {interval}s, Ctrl+C to quit)")
    print()

    while running[0]:
        # Find all agents
        root = store._root
        if not root.exists():
            print("⚠ No .stateweave/checkpoints/ directory found.")
            break

        agent_dirs = [d for d in root.iterdir() if d.is_dir() and (d / "manifest.json").exists()]

        now = datetime.utcnow()
        lines = []
        lines.append(f"  🧶 StateWeave Watch — {now.strftime('%H:%M:%S')} UTC")
        lines.append("  " + "═" * 60)

        if not agent_dirs:
            lines.append("  No agents tracked. Run: stateweave quickstart")
        else:
            lines.append(
                f"  {'Agent':<20}│ {'v':>3} │ {'Msgs':>4}"
                f" │ {'Memory':>7} │ {'Confidence':>10} │ Health"
            )
            lines.append(
                "  "
                + "─" * 20
                + "┼"
                + "─" * 5
                + "┼"
                + "─" * 6
                + "┼"
                + "─" * 9
                + "┼"
                + "─" * 12
                + "┼"
                + "─" * 10
            )

            for agent_dir in sorted(agent_dirs):
                agent_id = agent_dir.name
                try:
                    history = store.history(agent_id)
                except Exception:
                    continue

                if not history.checkpoints:
                    continue

                latest = history.latest
                if latest is None:
                    continue

                # Get confidence
                conf_str = "  n/a"
                health = "✅"
                try:
                    payload = store._load_payload(agent_id, latest.version)
                    if payload:
                        wm = payload.cognitive_state.working_memory
                        for key in ("confidence", "confidence_score", "agent_confidence"):
                            if key in wm:
                                try:
                                    conf = float(wm[key])
                                    if conf < 0.3:
                                        conf_str = f"{conf:.2f} 🔴"
                                        health = "🔴 RISK"
                                    elif conf < 0.5:
                                        conf_str = f"{conf:.2f} ⚠"
                                        health = "⚠ DRIFT"
                                    else:
                                        conf_str = f"{conf:.2f} ✅"
                                except (ValueError, TypeError):
                                    pass
                                break

                        if "hallucination_risk" in wm:
                            health = "🔴 HALLU"
                except Exception:
                    pass

                name_display = agent_id[:20]
                lines.append(
                    f"  {name_display:<20}│ {latest.version:>3}"
                    f" │ {latest.message_count:>4}"
                    f" │ {latest.working_memory_keys:>4} keys"
                    f" │ {conf_str:>10}"
                    f" │ {health}"
                )

        lines.append("  " + "═" * 60)
        lines.append(f"  {len(agent_dirs)} agent(s) tracked")

        # Clear and print
        print("\033[H\033[J", end="")  # Clear screen
        for line in lines:
            print(line)

        try:
            time.sleep(interval)
        except (KeyboardInterrupt, SystemExit):
            break

    print("\n  👋 Watch stopped.")


def cmd_ci(args):
    """CI integration — verify agent behavior hasn't regressed.

    Compares the current agent state against a baseline checkpoint.
    Exits with non-zero status if significant regression is detected.
    Use in CI pipelines to catch agent behavior regressions.

    Usage:
        stateweave ci my-agent --baseline 1 --current latest
        stateweave ci my-agent  # defaults: baseline=1, current=latest
    """
    import sys as sys_mod

    from stateweave.core.diff import diff_payloads
    from stateweave.core.timetravel import CheckpointStore

    store_dir = args.store_dir if hasattr(args, "store_dir") and args.store_dir else None
    store = CheckpointStore(store_dir=store_dir)

    agent_id = args.agent_id
    history = store.history(agent_id)

    if not history.checkpoints:
        print(f"⚠ No checkpoints for '{agent_id}'")
        sys_mod.exit(1)

    # Resolve versions
    baseline_v = getattr(args, "baseline", 1) or 1
    current_v = getattr(args, "current", None)
    if current_v is None or current_v == "latest":
        if history.latest:
            current_v = history.latest.version
        else:
            print("⚠ No latest checkpoint found")
            sys_mod.exit(1)
    else:
        current_v = int(current_v)

    # Load payloads
    baseline = store._load_payload(agent_id, baseline_v)
    current = store._load_payload(agent_id, current_v)

    if not baseline or not current:
        print(f"⚠ Could not load checkpoints v{baseline_v} and/or v{current_v}")
        sys_mod.exit(1)

    # Compare
    diff = diff_payloads(baseline, current)

    print()
    print("🧶 StateWeave CI — Agent Behavior Verification")
    print("═" * 60)
    print(f"  Agent:    {agent_id}")
    print(f"  Baseline: v{baseline_v}")
    print(f"  Current:  v{current_v}")
    print()

    # Check for regression indicators
    regressions = []

    # 1. Confidence regression
    baseline_wm = baseline.cognitive_state.working_memory
    current_wm = current.cognitive_state.working_memory

    baseline_conf = None
    current_conf = None
    for key in ("confidence", "confidence_score", "agent_confidence"):
        if key in baseline_wm:
            try:
                baseline_conf = float(baseline_wm[key])
            except (ValueError, TypeError):
                pass
        if key in current_wm:
            try:
                current_conf = float(current_wm[key])
            except (ValueError, TypeError):
                pass

    if baseline_conf is not None and current_conf is not None:
        if current_conf < baseline_conf - 0.2:
            regressions.append(f"Confidence regressed: {baseline_conf:.2f} → {current_conf:.2f}")

    # 2. Message loss
    baseline_msgs = len(baseline.cognitive_state.conversation_history)
    current_msgs = len(current.cognitive_state.conversation_history)
    if current_msgs < baseline_msgs:
        regressions.append(f"Message loss: {baseline_msgs} → {current_msgs}")

    # 3. Hallucination risk
    if "hallucination_risk" in current_wm:
        risk_val = str(current_wm["hallucination_risk"]).upper()
        if risk_val in ("HIGH", "CRITICAL", "TRUE"):
            regressions.append(f"Hallucination risk: {risk_val}")

    # 4. Working memory key loss (significant)
    baseline_keys = set(baseline_wm.keys())
    current_keys = set(current_wm.keys())
    lost_keys = baseline_keys - current_keys
    if len(lost_keys) > 3:
        regressions.append(f"Lost {len(lost_keys)} working memory keys")

    # Report
    max_tolerance = getattr(args, "max_changes", None)
    total_changes = len(diff.entries)

    print("  📊 Diff Summary")
    print("  ─" * 30)
    print(f"    Added:    +{diff.added_count}")
    print(f"    Removed:  -{diff.removed_count}")
    print(f"    Modified: ~{diff.modified_count}")
    print(f"    Total:    {total_changes} changes")
    print()

    if confidence_str := (
        f"  {baseline_conf:.2f} → {current_conf:.2f}"
        if baseline_conf is not None and current_conf is not None
        else "  n/a"
    ):
        print(f"  Confidence: {confidence_str}")

    if regressions:
        print()
        print("  🔴 REGRESSIONS DETECTED:")
        for r in regressions:
            print(f"    ✗ {r}")
        print()
        print("  ❌ CI FAILED — agent behavior has regressed")
        print("═" * 60)
        sys_mod.exit(1)
    elif max_tolerance is not None and total_changes > max_tolerance:
        print()
        print(f"  ⚠ {total_changes} changes exceeds tolerance ({max_tolerance})")
        print()
        print("  ❌ CI FAILED — too many state changes")
        print("═" * 60)
        sys_mod.exit(1)
    else:
        print()
        print("  ✅ CI PASSED — no regressions detected")
        print("═" * 60)
        sys_mod.exit(0)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="stateweave",
        description="🧶 StateWeave — git for agent brains",
        epilog=(
            "Examples:\n"
            "  stateweave quickstart\n"
            "  stateweave version\n"
            "  stateweave export -f langgraph -a my-agent -o state.json\n"
            "  stateweave import -f mcp --payload state.json\n"
            "  stateweave diff before.json after.json\n"
            "  stateweave why my-agent\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # version
    subparsers.add_parser("version", help="Show version information")

    # schema
    schema_parser = subparsers.add_parser("schema", help="Dump the Universal Schema as JSON Schema")
    schema_parser.add_argument("--output", "-o", help="Output file (default: stdout)")

    # validate
    validate_parser = subparsers.add_parser(
        "validate", help="Validate a StateWeavePayload JSON file"
    )
    validate_parser.add_argument("payload", help="Path to StateWeavePayload JSON file")

    # export
    fw_help = f"Source framework ({', '.join(sorted(ADAPTERS.keys()))})"
    export_parser = subparsers.add_parser("export", help="Export agent state")
    export_parser.add_argument(
        "--framework",
        "-f",
        required=True,
        choices=sorted(ADAPTERS.keys()),
        help=fw_help,
    )
    export_parser.add_argument("--agent-id", "-a", required=True, help="Agent identifier")
    export_parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    export_parser.add_argument("--encrypt", "-e", action="store_true", help="Encrypt output")
    export_parser.add_argument("--passphrase", "-p", help="Encryption passphrase")

    # import
    import_parser = subparsers.add_parser("import", help="Import agent state")
    import_parser.add_argument(
        "--framework",
        "-f",
        required=True,
        choices=sorted(ADAPTERS.keys()),
        help=f"Target framework ({', '.join(sorted(ADAPTERS.keys()))})",
    )
    import_parser.add_argument("--payload", required=True, help="StateWeavePayload JSON file")
    import_parser.add_argument("--agent-id", "-a", help="Override target agent ID")

    # diff
    diff_parser = subparsers.add_parser("diff", help="Diff two states")
    diff_parser.add_argument("state_a", help="First state JSON file")
    diff_parser.add_argument("state_b", help="Second state JSON file")

    # detect
    detect_parser = subparsers.add_parser(
        "detect", help="Auto-detect the source framework of a state file"
    )
    detect_parser.add_argument("input_file", help="State file to analyze")

    # adapters
    subparsers.add_parser("adapters", help="List all available framework adapters")

    # generate-adapter
    gen_parser = subparsers.add_parser(
        "generate-adapter", help="Generate scaffold for a new framework adapter"
    )
    gen_parser.add_argument("framework_name", help="Name of the new framework")
    gen_parser.add_argument("--output-dir", default=".", help="Output directory")

    # scan
    subparsers.add_parser("scan", help="Scan environment for installed agent frameworks")

    # checkpoint
    cp_parser = subparsers.add_parser("checkpoint", help="Save a checkpoint of agent state")
    cp_parser.add_argument("payload", help="StateWeavePayload JSON file to checkpoint")
    cp_parser.add_argument("--agent-id", "-a", help="Override agent ID")
    cp_parser.add_argument("--label", "-l", help="Human-readable label for this checkpoint")
    cp_parser.add_argument("--store-dir", help="Checkpoint store directory")

    # history
    hist_parser = subparsers.add_parser("history", help="Show checkpoint history for an agent")
    hist_parser.add_argument("agent_id", help="Agent identifier")
    hist_parser.add_argument("--store-dir", help="Checkpoint store directory")

    # rollback
    rb_parser = subparsers.add_parser("rollback", help="Restore a previous checkpoint")
    rb_parser.add_argument("agent_id", help="Agent identifier")
    rb_parser.add_argument("version", type=int, help="Version number to restore")
    rb_parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    rb_parser.add_argument("--store-dir", help="Checkpoint store directory")

    # doctor
    subparsers.add_parser("doctor", help="Run diagnostic health checks")

    # why
    why_parser = subparsers.add_parser(
        "why",
        help="Analyze an agent's checkpoint history — autopsy-style failure report",
    )
    why_parser.add_argument("agent_id", help="Agent identifier to analyze")
    why_parser.add_argument("--store-dir", help="Checkpoint store directory")
    why_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed diff entries for each transition",
    )

    # quickstart
    qs_parser = subparsers.add_parser(
        "quickstart",
        help="Run an instant demo — no code required",
    )
    qs_parser.add_argument(
        "--framework",
        "-f",
        default="langgraph",
        choices=sorted(ADAPTERS.keys()),
        help="Framework to demo (default: langgraph)",
    )

    # init
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize StateWeave in the current project",
    )
    init_parser.add_argument(
        "--framework",
        "-f",
        default="langgraph",
        choices=sorted(ADAPTERS.keys()),
        help="Default framework (default: langgraph)",
    )
    init_parser.add_argument(
        "--directory",
        "-d",
        default=".",
        help="Project directory (default: current)",
    )

    # replay
    replay_parser = subparsers.add_parser(
        "replay",
        help="Step-by-step replay of agent checkpoint history",
    )
    replay_parser.add_argument("agent_id", help="Agent to replay")
    replay_parser.add_argument(
        "--from",
        dest="from_version",
        type=int,
        default=None,
        help="Start from this version",
    )
    replay_parser.add_argument(
        "--to",
        dest="to_version",
        type=int,
        default=None,
        help="End at this version",
    )
    replay_parser.add_argument(
        "--store-dir",
        default=None,
        help="Checkpoint store directory",
    )

    # status
    status_parser = subparsers.add_parser(
        "status",
        help="Show health dashboard for all tracked agents",
    )
    status_parser.add_argument(
        "--store-dir",
        default=None,
        help="Checkpoint store directory",
    )

    # compare
    compare_parser = subparsers.add_parser(
        "compare",
        help="Compare two checkpoints side-by-side (e.g. agent:v3 agent:v5)",
    )
    compare_parser.add_argument("left", help="Left ref (agent-id:v1 or agent-id:latest)")
    compare_parser.add_argument("right", help="Right ref (agent-id:v5 or agent-id:latest)")
    compare_parser.add_argument(
        "--store-dir",
        default=None,
        help="Checkpoint store directory",
    )

    # watch
    watch_parser = subparsers.add_parser(
        "watch",
        help="Live agent state dashboard (like htop for agent brains)",
    )
    watch_parser.add_argument(
        "--interval",
        "-n",
        type=int,
        default=2,
        help="Refresh interval in seconds (default: 2)",
    )
    watch_parser.add_argument(
        "--store-dir",
        default=None,
        help="Checkpoint store directory",
    )

    # ci
    ci_parser = subparsers.add_parser(
        "ci",
        help="CI integration — verify agent behavior hasn't regressed",
    )
    ci_parser.add_argument("agent_id", help="Agent to verify")
    ci_parser.add_argument(
        "--baseline",
        type=int,
        default=1,
        help="Baseline version (default: 1)",
    )
    ci_parser.add_argument(
        "--current",
        default="latest",
        help="Current version to compare (default: latest)",
    )
    ci_parser.add_argument(
        "--max-changes",
        type=int,
        default=None,
        help="Max allowed state changes before failing",
    )
    ci_parser.add_argument(
        "--store-dir",
        default=None,
        help="Checkpoint store directory",
    )

    # log
    log_parser = subparsers.add_parser(
        "log",
        help="Beautiful one-line checkpoint history (like git log --oneline)",
    )
    log_parser.add_argument("agent_id", help="Agent to show history for")
    log_parser.add_argument(
        "--limit", "-n", type=int, default=20, help="Max entries to show (default: 20)"
    )
    log_parser.add_argument("--store-dir", default=None, help="Checkpoint store directory")

    # blame
    blame_parser = subparsers.add_parser(
        "blame",
        help="Show which checkpoint introduced a memory key (like git blame)",
    )
    blame_parser.add_argument("agent_id", help="Agent to inspect")
    blame_parser.add_argument("key", help="Working memory key to trace")
    blame_parser.add_argument("--store-dir", default=None, help="Checkpoint store directory")

    # stash
    stash_parser = subparsers.add_parser(
        "stash",
        help="Save current agent state to a named stash (like git stash)",
    )
    stash_parser.add_argument("agent_id", help="Agent to stash")
    stash_parser.add_argument("--name", default="default", help="Stash name (default: default)")
    stash_parser.add_argument("--store-dir", default=None, help="Checkpoint store directory")

    # pop
    pop_parser = subparsers.add_parser(
        "pop",
        help="Restore a stashed agent state (like git stash pop)",
    )
    pop_parser.add_argument("agent_id", help="Agent to restore")
    pop_parser.add_argument("--name", default="default", help="Stash name (default: default)")
    pop_parser.add_argument("--store-dir", default=None, help="Checkpoint store directory")

    args = parser.parse_args()

    if args.command == "version":
        cmd_version(args)
    elif args.command == "schema":
        cmd_schema(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "import":
        cmd_import(args)
    elif args.command == "diff":
        cmd_diff(args)
    elif args.command == "detect":
        cmd_detect(args)
    elif args.command == "adapters":
        cmd_adapters(args)
    elif args.command == "generate-adapter":
        cmd_generate_adapter(args)
    elif args.command == "scan":
        cmd_scan(args)
    elif args.command == "checkpoint":
        cmd_checkpoint(args)
    elif args.command == "history":
        cmd_history(args)
    elif args.command == "rollback":
        cmd_rollback(args)
    elif args.command == "doctor":
        cmd_doctor(args)
    elif args.command == "why":
        cmd_why(args)
    elif args.command == "quickstart":
        cmd_quickstart(args)
    elif args.command == "init":
        cmd_init(args)
    elif args.command == "replay":
        cmd_replay(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "compare":
        cmd_compare(args)
    elif args.command == "watch":
        cmd_watch(args)
    elif args.command == "ci":
        cmd_ci(args)
    elif args.command == "log":
        cmd_log(args)
    elif args.command == "blame":
        cmd_blame(args)
    elif args.command == "stash":
        cmd_stash(args)
    elif args.command == "pop":
        cmd_pop(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
