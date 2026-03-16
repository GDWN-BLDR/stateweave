"""
Shareable Migration Reports — HTML, Markdown, and JSON reports.
================================================================
Generate rich, shareable reports from migration operations that include
diff visualizations, non-portable warnings, data fidelity scores,
and complete audit trails.

This is Flywheel Feature #4 — every migration report shared on
GitHub/Slack is free marketing for StateWeave.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from stateweave.schema.v1 import (
    NonPortableWarning,
    NonPortableWarningSeverity,
    StateWeavePayload,
)

logger = logging.getLogger("stateweave.core.reports")


class MigrationReport:
    """A shareable report from a state migration operation.

    Tracks source and target state, diff results, warnings, and
    computes a data fidelity score.
    """

    def __init__(
        self,
        source_payload: StateWeavePayload,
        target_payload: Optional[StateWeavePayload] = None,
        diff_result: Optional[Dict[str, Any]] = None,
        operation: str = "migrate",
    ):
        self.source = source_payload
        self.target = target_payload
        self.diff = diff_result
        self.operation = operation
        self.timestamp = datetime.utcnow()
        self._warnings: List[NonPortableWarning] = list(source_payload.non_portable_warnings)
        if target_payload:
            self._warnings.extend(target_payload.non_portable_warnings)

    @property
    def fidelity_score(self) -> float:
        """Compute data fidelity score (0.0 to 1.0).

        Score is based on the ratio of preserved fields vs total fields,
        penalized by non-portable warnings.
        """
        source_cs = self.source.cognitive_state
        total_fields = 0
        populated_fields = 0

        for field_name in [
            "conversation_history",
            "working_memory",
            "goal_tree",
            "tool_results_cache",
            "trust_parameters",
            "long_term_memory",
            "episodic_memory",
        ]:
            value = getattr(source_cs, field_name)
            if value:
                total_fields += 1
                # Check if target has the same field populated
                if self.target:
                    target_value = getattr(self.target.cognitive_state, field_name)
                    if target_value:
                        populated_fields += 1
                else:
                    populated_fields += 1

        if total_fields == 0:
            return 1.0

        base_score = populated_fields / total_fields

        # Penalty for warnings
        critical_count = sum(
            1 for w in self._warnings if w.severity == NonPortableWarningSeverity.CRITICAL
        )
        warn_count = sum(1 for w in self._warnings if w.severity == NonPortableWarningSeverity.WARN)

        penalty = (critical_count * 0.1) + (warn_count * 0.03)
        return max(0.0, round(base_score - penalty, 2))

    def to_json(self) -> str:
        """Generate JSON report."""
        report = {
            "stateweave_migration_report": {
                "version": "1.0",
                "timestamp": self.timestamp.isoformat(),
                "operation": self.operation,
                "source": {
                    "framework": self.source.source_framework,
                    "agent_id": self.source.metadata.agent_id,
                    "exported_at": self.source.exported_at.isoformat(),
                },
                "target": None,
                "fidelity_score": self.fidelity_score,
                "warnings": [
                    {
                        "field": w.field,
                        "reason": w.reason,
                        "severity": w.severity.value,
                        "data_loss": w.data_loss,
                        "recommendation": w.recommendation,
                    }
                    for w in self._warnings
                ],
                "audit_trail": [
                    {
                        "timestamp": entry.timestamp.isoformat(),
                        "action": entry.action.value,
                        "framework": entry.framework,
                        "success": entry.success,
                    }
                    for entry in self.source.audit_trail
                ],
                "diff": self.diff,
            }
        }

        if self.target:
            report["stateweave_migration_report"]["target"] = {
                "framework": self.target.source_framework,
                "agent_id": self.target.metadata.agent_id,
            }

        return json.dumps(report, indent=2, default=str)

    def to_markdown(self) -> str:
        """Generate Markdown report (for GitHub issues, docs)."""
        lines = [
            "# StateWeave Migration Report",
            "",
            f"**Timestamp**: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Operation**: {self.operation}",
            f"**Fidelity Score**: {self.fidelity_score:.0%}",
            "",
            "## Source",
            f"- **Framework**: {self.source.source_framework}",
            f"- **Agent**: {self.source.metadata.agent_id}",
            f"- **Exported**: {self.source.exported_at.strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        if self.target:
            lines.extend(
                [
                    "",
                    "## Target",
                    f"- **Framework**: {self.target.source_framework}",
                    f"- **Agent**: {self.target.metadata.agent_id}",
                ]
            )

        # Cognitive state summary
        cs = self.source.cognitive_state
        lines.extend(
            [
                "",
                "## State Summary",
                "| Field | Count |",
                "|-------|-------|",
                f"| Conversation History | {len(cs.conversation_history)} messages |",
                f"| Working Memory | {len(cs.working_memory)} keys |",
                f"| Goal Tree | {len(cs.goal_tree)} nodes |",
                f"| Tool Results | {len(cs.tool_results_cache)} cached |",
                f"| Trust Parameters | {len(cs.trust_parameters)} params |",
                f"| Long-term Memory | {len(cs.long_term_memory)} entries |",
                f"| Episodic Memory | {len(cs.episodic_memory)} episodes |",
            ]
        )

        # Warnings
        if self._warnings:
            lines.extend(
                [
                    "",
                    "## Non-Portable Warnings",
                    "",
                    "| Severity | Field | Reason | Data Loss |",
                    "|----------|-------|--------|-----------|",
                ]
            )
            for w in self._warnings:
                icon = {"CRITICAL": "🔴", "WARN": "🟡", "INFO": "🔵"}.get(w.severity.value, "⚪")
                lines.append(
                    f"| {icon} {w.severity.value} | `{w.field}` | "
                    f"{w.reason} | {'Yes' if w.data_loss else 'No'} |"
                )

        # Audit trail
        if self.source.audit_trail:
            lines.extend(
                [
                    "",
                    "## Audit Trail",
                    "",
                ]
            )
            for entry in self.source.audit_trail:
                status = "✓" if entry.success else "✗"
                lines.append(
                    f"- {status} **{entry.action.value}** "
                    f"({entry.framework}) — "
                    f"{entry.timestamp.strftime('%H:%M:%S')}"
                )

        lines.extend(
            [
                "",
                "---",
                f"*Generated by [StateWeave](https://stateweave.pantollventures.com) v{self.source.stateweave_version}*",
            ]
        )

        return "\n".join(lines)

    def to_html(self) -> str:
        """Generate standalone HTML report."""
        score = self.fidelity_score
        score_color = "#22c55e" if score >= 0.9 else "#eab308" if score >= 0.7 else "#ef4444"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>StateWeave Migration Report</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: 'Inter', -apple-system, sans-serif;
      background: #000; color: #ededed;
      padding: 2rem; max-width: 800px; margin: 0 auto;
    }}
    h1 {{ font-size: 1.5rem; margin-bottom: 1rem; }}
    h2 {{ font-size: 1.1rem; color: #a78bfa; margin: 1.5rem 0 0.5rem; }}
    .score {{ font-size: 2rem; font-weight: 800; color: {score_color}; }}
    .meta {{ color: #888; font-size: 0.85rem; margin-bottom: 1.5rem; }}
    table {{ width: 100%; border-collapse: collapse; margin: 0.5rem 0; }}
    th {{ text-align: left; color: #888; font-size: 0.8rem; padding: 0.4rem; border-bottom: 1px solid #333; }}
    td {{ padding: 0.4rem; border-bottom: 1px solid #1a1a1a; font-size: 0.85rem; }}
    code {{ background: #1a1a1a; padding: 0.15rem 0.4rem; border-radius: 3px; font-size: 0.8rem; }}
    .footer {{ color: #555; font-size: 0.75rem; margin-top: 2rem; text-align: center; }}
    a {{ color: #a78bfa; text-decoration: none; }}
  </style>
</head>
<body>
  <h1>StateWeave Migration Report</h1>
  <p class="meta">
    {self.source.source_framework} → {self.target.source_framework if self.target else "export"} ·
    {self.timestamp.strftime("%Y-%m-%d %H:%M UTC")}
  </p>
  <p>Fidelity Score: <span class="score">{score:.0%}</span></p>

  <h2>Source</h2>
  <p>Framework: <strong>{self.source.source_framework}</strong> ·
  Agent: <code>{self.source.metadata.agent_id}</code></p>

  {
            f'''<h2>Target</h2>
  <p>Framework: <strong>{self.target.source_framework}</strong> ·
  Agent: <code>{self.target.metadata.agent_id}</code></p>'''
            if self.target
            else ""
        }

  <h2>State Summary</h2>
  <table>
    <tr><th>Field</th><th>Count</th></tr>
    <tr><td>Conversation History</td><td>{
            len(self.source.cognitive_state.conversation_history)
        } messages</td></tr>
    <tr><td>Working Memory</td><td>{len(self.source.cognitive_state.working_memory)} keys</td></tr>
    <tr><td>Goal Tree</td><td>{len(self.source.cognitive_state.goal_tree)} nodes</td></tr>
    <tr><td>Tool Results</td><td>{
            len(self.source.cognitive_state.tool_results_cache)
        } cached</td></tr>
    <tr><td>Long-term Memory</td><td>{
            len(self.source.cognitive_state.long_term_memory)
        } entries</td></tr>
    <tr><td>Episodic Memory</td><td>{
            len(self.source.cognitive_state.episodic_memory)
        } episodes</td></tr>
  </table>

  {self._render_warnings_html()}

  <div class="footer">
    Generated by <a href="https://stateweave.pantollventures.com">StateWeave</a> v{
            self.source.stateweave_version
        }
  </div>
</body>
</html>"""

    def _render_warnings_html(self) -> str:
        """Render warnings as HTML table."""
        if not self._warnings:
            return ""

        rows = ""
        for w in self._warnings:
            icon = {"CRITICAL": "🔴", "WARN": "🟡", "INFO": "🔵"}.get(w.severity.value, "⚪")
            rows += f"""<tr>
  <td>{icon} {w.severity.value}</td>
  <td><code>{w.field}</code></td>
  <td>{w.reason}</td>
  <td>{"Yes" if w.data_loss else "No"}</td>
</tr>"""

        return f"""
  <h2>Non-Portable Warnings</h2>
  <table>
    <tr><th>Severity</th><th>Field</th><th>Reason</th><th>Data Loss</th></tr>
    {rows}
  </table>"""
