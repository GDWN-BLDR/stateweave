"""
Unit Tests: Portability Analyzer
===================================
Non-portable element detection tests.
"""

from stateweave.core.portability import PortabilityAnalyzer
from stateweave.schema.v1 import NonPortableWarningSeverity


class TestPortabilityAnalyzer:
    def test_empty_state(self):
        analyzer = PortabilityAnalyzer()
        warnings = analyzer.analyze({})
        assert warnings == []

    def test_safe_state(self):
        analyzer = PortabilityAnalyzer()
        warnings = analyzer.analyze(
            {
                "task": "research",
                "count": 42,
                "items": ["a", "b"],
            }
        )
        assert warnings == []

    def test_detect_sensitive_api_key(self):
        analyzer = PortabilityAnalyzer()
        warnings = analyzer.analyze(
            {
                "api_key": "sk-12345",
                "config": {"openai_api_key": "sk-abcde"},
            }
        )
        critical = [w for w in warnings if w.severity == NonPortableWarningSeverity.CRITICAL]
        assert len(critical) >= 1

    def test_detect_sensitive_password(self):
        analyzer = PortabilityAnalyzer()
        warnings = analyzer.analyze(
            {
                "db_password": "secret123",
            }
        )
        assert any("password" in w.field.lower() for w in warnings)

    def test_detect_sensitive_token(self):
        analyzer = PortabilityAnalyzer()
        warnings = analyzer.analyze(
            {
                "access_token": "bearer_abc",
            }
        )
        assert any(w.severity == NonPortableWarningSeverity.CRITICAL for w in warnings)

    def test_langgraph_framework_fields(self):
        analyzer = PortabilityAnalyzer(source_framework="langgraph")
        warnings = analyzer.analyze(
            {
                "__channel_versions__": {"ch1": 1},
                "checkpoint_id": "abc-123",
                "user_data": "safe",
            }
        )
        lg_warnings = [
            w
            for w in warnings
            if "langgraph" in w.reason.lower()
            or "channel" in w.field.lower()
            or "checkpoint" in w.field.lower()
        ]
        assert len(lg_warnings) >= 1

    def test_mcp_framework_fields(self):
        analyzer = PortabilityAnalyzer(source_framework="mcp")
        warnings = analyzer.analyze(
            {
                "_meta": {"server": "test"},
                "oauth_token_cache": "encrypted",
            }
        )
        mcp_warnings = [
            w
            for w in warnings
            if "mcp" in str(w.reason).lower() or w.severity == NonPortableWarningSeverity.CRITICAL
        ]
        assert len(mcp_warnings) >= 1

    def test_nested_sensitive_detection(self):
        analyzer = PortabilityAnalyzer()
        warnings = analyzer.analyze(
            {
                "config": {
                    "database": {
                        "secret_key": "my-secret",
                    },
                },
            }
        )
        assert any("secret" in w.field.lower() for w in warnings)

    def test_recommendation_provided(self):
        analyzer = PortabilityAnalyzer()
        warnings = analyzer.analyze({"api_key": "value"})
        for w in warnings:
            if w.severity == NonPortableWarningSeverity.CRITICAL:
                assert w.recommendation is not None
