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
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
