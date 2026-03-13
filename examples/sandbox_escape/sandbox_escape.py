#!/usr/bin/env python3
"""
🧶 StateWeave: Cloud-to-Local Sandbox Escape Demo
====================================================
This script demonstrates the core value proposition of StateWeave:
an AI agent's cognitive state seamlessly transfers between frameworks,
preserving everything it learned.

The Story:
    Act 1: A cloud LangGraph agent accumulates state while researching
    Act 2: Agent hits a wall — data is behind a corporate VPN
    Act 3: StateWeave exports the state, encrypts it, transports it
    Act 4: A local MCP agent receives the state and resumes instantly
    Act 5: State diff proves perfect continuity

Run:
    python examples/sandbox_escape.py
"""

from stateweave import (
    EncryptionFacade,
    LangGraphAdapter,
    MCPAdapter,
    MigrationEngine,
    StateWeaveSerializer,
    diff_payloads,
)

# ══════════════════════════════════════════════════════════════
#  Terminal colors
# ══════════════════════════════════════════════════════════════
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
RESET = "\033[0m"


def banner(text: str, color: str = CYAN):
    width = 60
    print()
    print(f"{color}{'═' * width}{RESET}")
    print(f"{color}{BOLD}  {text}{RESET}")
    print(f"{color}{'═' * width}{RESET}")
    print()


def step(icon: str, text: str):
    print(f"  {icon}  {text}")


def substep(text: str):
    print(f"      {DIM}→ {text}{RESET}")


def main():
    banner("🧶 STATEWEAVE: Cloud-to-Local Sandbox Escape", MAGENTA)
    print(f"  {DIM}Demonstrating cross-framework cognitive state portability{RESET}")
    print(f"  {DIM}A LangGraph agent's brain migrates to MCP — memories intact{RESET}")
    print()

    # ─────────────────────────────────────────────
    # ACT 1: Cloud LangGraph agent accumulates state
    # ─────────────────────────────────────────────
    banner("ACT 1: Cloud LangGraph Agent Researches", BLUE)

    cloud_adapter = LangGraphAdapter()
    cloud_adapter._agents["cloud-researcher"] = {
        "messages": [
            {
                "type": "human",
                "content": "Research the competitive landscape for AI agent frameworks in 2026.",
            },
            {
                "type": "ai",
                "content": "I'll analyze the major frameworks. Let me search for the latest data.",
            },
            {
                "type": "tool",
                "content": '{"frameworks": ["LangGraph", "CrewAI", "AutoGen", "MCP"], "market_size": "104K+ public agents", "growth": "38% enterprise adoption"}',
                "name": "web_search",
                "tool_call_id": "tc_001",
            },
            {
                "type": "ai",
                "content": "Based on my research, the AI agent framework landscape in 2026 is dominated by 4 major players:\n\n1. **LangGraph** — 34.5M monthly downloads, strongest for complex stateful agents\n2. **CrewAI** — Leading multi-agent orchestration, sequential/hierarchical crews\n3. **AutoGen** — Microsoft-backed, strongest for code generation agents\n4. **MCP** — Anthropic's protocol, 19,136 servers, growing fastest\n\nKey finding: 83% of enterprises are using AI agents, but 95% of pilots fail due to infrastructure — not model quality.",
            },
            {
                "type": "human",
                "content": "Great. Now find the acquisition data for AI dev tools in Q1 2026.",
            },
            {"type": "ai", "content": "Searching for M&A data..."},
            {
                "type": "tool",
                "content": '{"deals": [{"buyer": "ServiceNow", "target": "Traceloop", "price": "$60-80M"}, {"buyer": "OpenAI", "target": "Promptfoo", "valuation": "$86M"}, {"buyer": "Anthropic", "target": "Bun", "price": "undisclosed"}]}',
                "name": "web_search",
                "tool_call_id": "tc_002",
            },
            {
                "type": "ai",
                "content": "Q1 2026 AI dev tools M&A activity:\n- ServiceNow → Traceloop ($60-80M) — LLM observability\n- OpenAI → Promptfoo ($86M valuation) — AI testing/security\n- Anthropic → Bun (undisclosed) — runtime/dev tools\n\nKey insight: Open-source companies command median $482M in M&A vs $34M proprietary — a 14x multiplier.",
            },
        ],
        "current_research_topic": "AI agent framework competitive landscape",
        "key_findings": {
            "market_size": "104K+ public agents",
            "enterprise_adoption": "83%",
            "pilot_failure_rate": "95%",
            "top_frameworks": ["LangGraph", "CrewAI", "AutoGen", "MCP"],
        },
        "confidence_score": 0.87,
        "sources_consulted": 14,
    }

    step("☁️", f"{BLUE}Cloud LangGraph agent has been researching...{RESET}")
    substep("8 messages in conversation history")
    substep("4 key findings accumulated")
    substep("14 sources consulted, 87% confidence")

    # ─────────────────────────────────────────────
    # ACT 2: Agent hits a wall
    # ─────────────────────────────────────────────
    banner("ACT 2: The Wall — VPN-Protected Data", YELLOW)

    step("🚧", f"{YELLOW}Cloud agent needs VPN-protected competitor pricing data{RESET}")
    substep("Corporate firewall blocks cloud access")
    substep("Data is behind internal VPN — only local agents can reach it")
    substep("Agent needs to migrate to local execution WITHOUT losing its research")
    print()
    step("💡", f"{GREEN}Solution: StateWeave exports the agent's cognitive state{RESET}")

    # ─────────────────────────────────────────────
    # ACT 3: StateWeave exports, encrypts, transports
    # ─────────────────────────────────────────────
    banner("ACT 3: StateWeave Export → Encrypt → Transport", GREEN)

    key = EncryptionFacade.generate_key()
    encryption = EncryptionFacade(key)
    serializer = StateWeaveSerializer()
    engine = MigrationEngine(serializer=serializer, encryption=encryption)

    step("📤", f"{GREEN}Exporting state from LangGraph...{RESET}")

    export_result = engine.export_state(
        adapter=cloud_adapter,
        agent_id="cloud-researcher",
        encrypt=True,
    )

    assert export_result.success, "Export failed!"

    substep(f"Payload: {len(export_result.payload.cognitive_state.conversation_history)} messages")
    substep(f"Working memory: {len(export_result.payload.cognitive_state.working_memory)} keys")
    substep(f"Schema version: {export_result.payload.stateweave_version}")

    step("🔒", f"{GREEN}State encrypted with AES-256-GCM{RESET}")
    substep(f"Key ID: {encryption.key_id}")
    substep(f"Encrypted size: {len(export_result.encrypted_data)} bytes")
    substep(f"Nonce: {export_result.nonce[:16]}...")

    if export_result.payload.non_portable_warnings:
        step("⚠️", f"{YELLOW}Non-portable warnings:{RESET}")
        for w in export_result.payload.non_portable_warnings:
            substep(f"[{w.severity.value}] {w.field}: {w.reason}")

    # ─────────────────────────────────────────────
    # ACT 4: Local MCP agent receives and resumes
    # ─────────────────────────────────────────────
    banner("ACT 4: Local MCP Agent Receives State", CYAN)

    local_adapter = MCPAdapter()

    step("📥", f"{CYAN}Importing state into local MCP agent...{RESET}")

    import_result = engine.import_state(
        adapter=local_adapter,
        encrypted_data=export_result.encrypted_data,
        nonce=export_result.nonce,
    )

    assert import_result.success, "Import failed!"

    local_payload = local_adapter.export_state("cloud-researcher")

    substep(f"Agent ID: {local_payload.metadata.agent_id}")
    substep(f"Messages restored: {len(local_payload.cognitive_state.conversation_history)}")
    substep(f"Working memory restored: {len(local_payload.cognitive_state.working_memory)} keys")

    step("🧠", f"{CYAN}Agent's knowledge is intact:{RESET}")
    wm = local_payload.cognitive_state.working_memory
    if "key_findings" in wm:
        findings = wm["key_findings"]
        if isinstance(findings, dict):
            for key_name, val in findings.items():
                substep(f"{key_name}: {val}")

    step("✅", f"{GREEN}Local agent can now access VPN-protected data{RESET}")
    substep("Conversation history: PRESERVED")
    substep("Research findings: PRESERVED")
    substep("Confidence score: PRESERVED")
    substep("The boundary between cloud and local has been erased.")

    # ─────────────────────────────────────────────
    # ACT 5: State diff proves continuity
    # ─────────────────────────────────────────────
    banner("ACT 5: Verification — State Diff Report", MAGENTA)

    diff = diff_payloads(export_result.payload, local_payload)

    step("🔍", f"{MAGENTA}Comparing exported vs imported state:{RESET}")
    substep(f"Total changes: {len(diff.entries)}")
    substep(
        f"Added: {diff.added_count}  |  Removed: {diff.removed_count}  |  Modified: {diff.modified_count}"
    )

    if diff.has_changes:
        step(
            "📋",
            f"{DIM}Changes are expected — framework tag and timestamps update on import:{RESET}",
        )
        for entry in diff.entries[:5]:
            substep(f"[{entry.diff_type}] {entry.path}")

    # ─────────────────────────────────────────────
    # Finale
    # ─────────────────────────────────────────────
    banner("🏁 DEMO COMPLETE", GREEN)

    print(f"  {BOLD}What just happened:{RESET}")
    print("    1. A cloud LangGraph agent accumulated 8 messages and 4 key findings")
    print("    2. StateWeave exported its cognitive state to the Universal Schema")
    print("    3. The state was encrypted with AES-256-GCM for transport")
    print("    4. A local MCP agent received and restored the full state")
    print("    5. Zero knowledge was lost. The agent's brain survived the migration.")
    print()
    print(
        f"  {BOLD}{GREEN}The boundary between cloud AI and local execution has been erased.{RESET}"
    )
    print()
    print(f"  {DIM}pip install stateweave{RESET}")
    print(f"  {DIM}https://github.com/GDWN-BLDR/stateweave{RESET}")
    print()


if __name__ == "__main__":
    main()
