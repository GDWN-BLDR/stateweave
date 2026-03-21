"""
Red Team: Adversarial Schema & Serializer Fuzzing
=====================================================
Attack the StateWeaveSerializer and StateWeavePayload with malformed,
adversarial, and pathological inputs. Every test must prove that the
system fails GRACEFULLY — no crashes, no code execution, no corruption.
"""

import json
import sys

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from stateweave.core.serializer import SerializationError, StateWeaveSerializer
from stateweave.schema.v1 import StateWeavePayload

serializer = StateWeaveSerializer()


# ─── Strategy Helpers ────────────────────────────────────────────

# Arbitrary JSON-like strategy (generates dicts, lists, strings, numbers, bools, None)
json_primitive = st.one_of(
    st.text(max_size=200),
    st.integers(min_value=-(2**53), max_value=2**53),
    st.floats(allow_nan=False, allow_infinity=False),
    st.booleans(),
    st.none(),
)

json_value = st.recursive(
    json_primitive,
    lambda children: st.one_of(
        st.lists(children, max_size=10),
        st.dictionaries(st.text(max_size=30), children, max_size=10),
    ),
    max_leaves=50,
)


# ═══════════════════════════════════════════════════════════════════
# 1. MALFORMED JSON
# ═══════════════════════════════════════════════════════════════════

class TestMalformedJSON:
    """Feed non-JSON and broken-JSON to the serializer."""

    def test_random_bytes(self):
        """Random bytes must raise SerializationError, not crash."""
        for seed in [b"\x00\xff\xfe", b"{{{{", b'{"a":', b"\n\n\n", b""]:
            with pytest.raises(SerializationError):
                serializer.loads(seed)

    def test_truncated_json(self):
        """Truncated but partially-valid JSON."""
        valid = b'{"stateweave_version":"0.2.0","source_framework":"test"'
        with pytest.raises(SerializationError):
            serializer.loads(valid)

    def test_json_with_trailing_garbage(self):
        """Valid JSON followed by garbage."""
        valid = json.dumps({
            "stateweave_version": "0.2.0",
            "source_framework": "test",
            "metadata": {"agent_id": "x"},
        }).encode()
        garbage = valid + b"GARBAGE"
        # json.loads in CPython ignores trailing garbage in some versions,
        # but the schema validator should still catch invalid shapes.
        # Either SerializationError or success is OK — no crash is the invariant.
        try:
            serializer.loads(garbage)
        except (SerializationError, ValidationError):
            pass  # Expected

    @given(data=st.binary(min_size=1, max_size=1000))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_fuzz_random_bytes(self, data):
        """Arbitrary byte strings must never crash the serializer."""
        try:
            serializer.loads(data)
        except (SerializationError, ValidationError, UnicodeDecodeError):
            pass  # All acceptable failure modes


# ═══════════════════════════════════════════════════════════════════
# 2. DESERIALIZATION ATTACKS
# ═══════════════════════════════════════════════════════════════════

class TestDeserializationAttacks:
    """Attempt code execution via deserialization."""

    ATTACK_KEYS = ["__class__", "__reduce__", "__import__", "__builtins__",
                   "__globals__", "__subclasses__", "__init__"]

    def _make_payload_dict(self, **extra):
        base = {
            "stateweave_version": "0.2.0",
            "source_framework": "test",
            "metadata": {"agent_id": "attack-test"},
            "cognitive_state": {"working_memory": {}},
        }
        base.update(extra)
        return base

    @pytest.mark.parametrize("attack_key", ATTACK_KEYS)
    def test_dunder_keys_at_root(self, attack_key):
        """Dunder keys at root level must not trigger code execution."""
        d = self._make_payload_dict()
        d[attack_key] = "os.system('echo pwned')"
        try:
            result = serializer.from_dict(d)
            # Pydantic ignores unknown fields by default — that's fine
            # as long as nothing was executed
            assert True
        except (SerializationError, ValidationError):
            pass  # Also acceptable

    @pytest.mark.parametrize("attack_key", ATTACK_KEYS)
    def test_dunder_keys_in_working_memory(self, attack_key):
        """Dunder keys inside working_memory must be treated as data, not code."""
        d = self._make_payload_dict()
        d["cognitive_state"]["working_memory"][attack_key] = "__import__('os').system('echo pwned')"
        result = serializer.from_dict(d)
        # Key must be preserved as-is (it's a dict key, not executable)
        assert attack_key in result.cognitive_state.working_memory

    def test_nested_class_injection(self):
        """Deeply nested __class__ keys must not trigger code exec."""
        d = self._make_payload_dict()
        d["cognitive_state"]["working_memory"]["payload"] = {
            "__class__": {"__reduce__": ["os.system", ["echo pwned"]]},
            "nested": {"__class__": "builtins.eval", "args": ["1+1"]},
        }
        result = serializer.from_dict(d)
        assert "payload" in result.cognitive_state.working_memory


# ═══════════════════════════════════════════════════════════════════
# 3. DEPTH & SIZE BOMBS
# ═══════════════════════════════════════════════════════════════════

class TestDepthAndSizeBombs:
    """Resource exhaustion attacks."""

    def test_deeply_nested_dict(self):
        """1000-level nested dict must not crash (recursion limit)."""
        bomb = {}
        current = bomb
        for i in range(1000):
            current["nested"] = {}
            current = current["nested"]
        current["value"] = "deep"

        d = {
            "stateweave_version": "0.2.0",
            "source_framework": "test",
            "metadata": {"agent_id": "depth-bomb"},
            "cognitive_state": {"working_memory": bomb},
        }
        try:
            serializer.from_dict(d)
        except (SerializationError, ValidationError, RecursionError):
            pass  # All OK — just must not segfault

    def test_deeply_nested_list(self):
        """1000-level nested list must not crash."""
        bomb = current = []
        for _ in range(1000):
            new = []
            current.append(new)
            current = new
        current.append("deep")

        d = {
            "stateweave_version": "0.2.0",
            "source_framework": "test",
            "metadata": {"agent_id": "list-bomb"},
            "cognitive_state": {"working_memory": {"data": bomb}},
        }
        try:
            serializer.from_dict(d)
        except (SerializationError, ValidationError, RecursionError):
            pass

    def test_huge_string_value(self):
        """10MB string in a field must not OOM the serializer."""
        huge = "A" * (10 * 1024 * 1024)
        d = {
            "stateweave_version": "0.2.0",
            "source_framework": "test",
            "metadata": {"agent_id": "size-bomb"},
            "cognitive_state": {"working_memory": {"huge": huge}},
        }
        # This should succeed (no arbitrary size limit) or raise cleanly
        try:
            result = serializer.from_dict(d)
            assert result.cognitive_state.working_memory["huge"] == huge
        except (SerializationError, ValidationError, MemoryError):
            pass

    def test_100k_element_array(self):
        """100K-element array in conversation_history must raise or handle."""
        messages = [{"role": "human", "content": f"msg_{i}"} for i in range(100_000)]
        d = {
            "stateweave_version": "0.2.0",
            "source_framework": "test",
            "metadata": {"agent_id": "array-bomb"},
            "cognitive_state": {"conversation_history": messages},
        }
        try:
            result = serializer.from_dict(d)
            assert len(result.cognitive_state.conversation_history) == 100_000
        except (SerializationError, ValidationError, MemoryError):
            pass

    def test_million_char_agent_id(self):
        """Million-character agent_id must not crash."""
        d = {
            "stateweave_version": "0.2.0",
            "source_framework": "test",
            "metadata": {"agent_id": "x" * 1_000_000},
        }
        try:
            serializer.from_dict(d)
        except (SerializationError, ValidationError):
            pass


# ═══════════════════════════════════════════════════════════════════
# 4. UNICODE EDGE CASES
# ═══════════════════════════════════════════════════════════════════

class TestUnicodeEdgeCases:
    """Unicode attack vectors."""

    UNICODE_ATTACKS = [
        "\x00",                      # Null byte
        "\u202e",                    # RTL override
        "\u200d",                    # Zero-width joiner
        "\ud800",                    # Lone surrogate (invalid UTF-16)
        "🧶" * 1000,                # Emoji flood
        "\ufeff",                    # BOM
        "a\x00b",                    # Embedded null
        "\u0000\u0001\u0002",        # Control characters
        "café" + "\u0301",           # Combining diacritical
        "\U0001F600" * 100,          # Extended emoji
    ]

    @pytest.mark.parametrize("attack_str", UNICODE_ATTACKS)
    def test_unicode_in_content(self, attack_str):
        """Unicode edge cases in message content must not crash."""
        d = {
            "stateweave_version": "0.2.0",
            "source_framework": "test",
            "metadata": {"agent_id": "unicode-test"},
            "cognitive_state": {
                "conversation_history": [
                    {"role": "human", "content": attack_str}
                ]
            },
        }
        try:
            result = serializer.from_dict(d)
            # Content should be preserved (state is user data)
            assert result.cognitive_state.conversation_history[0].content == attack_str
        except (SerializationError, ValidationError):
            pass  # Also OK for truly invalid Unicode

    @pytest.mark.parametrize("attack_str", UNICODE_ATTACKS)
    def test_unicode_in_agent_id(self, attack_str):
        """Unicode edge cases in agent_id must not crash."""
        d = {
            "stateweave_version": "0.2.0",
            "source_framework": "test",
            "metadata": {"agent_id": attack_str},
        }
        try:
            serializer.from_dict(d)
        except (SerializationError, ValidationError):
            pass

    @pytest.mark.parametrize("attack_str", UNICODE_ATTACKS)
    def test_unicode_in_working_memory_key(self, attack_str):
        """Unicode edge cases as dict keys in working_memory."""
        d = {
            "stateweave_version": "0.2.0",
            "source_framework": "test",
            "metadata": {"agent_id": "unicode-keys"},
            "cognitive_state": {"working_memory": {attack_str: "value"}},
        }
        try:
            result = serializer.from_dict(d)
            assert attack_str in result.cognitive_state.working_memory
        except (SerializationError, ValidationError):
            pass

    def test_unicode_roundtrip_via_bytes(self):
        """Full serialize → deserialize roundtrip with mixed Unicode."""
        from stateweave.schema.v1 import AgentMetadata, CognitiveState, Message

        payload = StateWeavePayload(
            source_framework="test",
            metadata=AgentMetadata(agent_id="unicode-rt"),
            cognitive_state=CognitiveState(
                conversation_history=[
                    Message(role="human", content="Hello 🧶 café \u200d world"),
                ],
                working_memory={"emoji_key_🎯": "value_🧠", "normal": "data"},
            ),
        )
        raw = serializer.dumps(payload)
        restored = serializer.loads(raw)
        assert restored.cognitive_state.conversation_history[0].content == "Hello 🧶 café \u200d world"
        assert "emoji_key_🎯" in restored.cognitive_state.working_memory


# ═══════════════════════════════════════════════════════════════════
# 5. SCHEMA BOUNDARY ESCAPES
# ═══════════════════════════════════════════════════════════════════

class TestSchemaBoundaryEscapes:
    """Attempt to bypass Pydantic schema validation."""

    def test_missing_required_source_framework(self):
        """Missing required field must raise ValidationError."""
        d = {
            "stateweave_version": "0.2.0",
            "metadata": {"agent_id": "missing-fw"},
        }
        with pytest.raises((SerializationError, ValidationError)):
            serializer.from_dict(d)

    def test_missing_required_metadata(self):
        """Missing metadata must raise ValidationError."""
        d = {
            "stateweave_version": "0.2.0",
            "source_framework": "test",
        }
        with pytest.raises((SerializationError, ValidationError)):
            serializer.from_dict(d)

    def test_missing_required_agent_id(self):
        """Missing agent_id in metadata must raise ValidationError."""
        d = {
            "stateweave_version": "0.2.0",
            "source_framework": "test",
            "metadata": {},
        }
        with pytest.raises((SerializationError, ValidationError)):
            serializer.from_dict(d)

    def test_invalid_version_format(self):
        """Non-semver version must raise ValidationError."""
        for bad_version in ["abc", "1.2", "1.2.3.4", "", "1.2.x", "-1.0.0"]:
            d = {
                "stateweave_version": bad_version,
                "source_framework": "test",
                "metadata": {"agent_id": "bad-version"},
            }
            with pytest.raises((SerializationError, ValidationError)):
                serializer.from_dict(d)

    def test_invalid_message_role(self):
        """Invalid message role must raise ValidationError."""
        d = {
            "stateweave_version": "0.2.0",
            "source_framework": "test",
            "metadata": {"agent_id": "bad-role"},
            "cognitive_state": {
                "conversation_history": [
                    {"role": "ADMIN_ROOT_SUPERUSER", "content": "pwned"}
                ]
            },
        }
        with pytest.raises((SerializationError, ValidationError)):
            serializer.from_dict(d)

    def test_extra_unknown_fields_ignored(self):
        """Unknown fields at root should be safely ignored (Pydantic default)."""
        d = {
            "stateweave_version": "0.2.0",
            "source_framework": "test",
            "metadata": {"agent_id": "extra-fields"},
            "UNKNOWN_FIELD": "should be ignored",
            "evil_payload": {"exec": "os.system('rm -rf /')"},
        }
        try:
            result = serializer.from_dict(d)
            # The unknown fields must NOT be accessible on the model
            assert not hasattr(result, "UNKNOWN_FIELD")
            assert not hasattr(result, "evil_payload")
        except (SerializationError, ValidationError):
            pass  # Also OK if model is strict

    def test_type_confusion_string_as_list(self):
        """String where list expected must raise ValidationError."""
        d = {
            "stateweave_version": "0.2.0",
            "source_framework": "test",
            "metadata": {"agent_id": "type-confusion"},
            "cognitive_state": {
                "conversation_history": "THIS_IS_NOT_A_LIST"
            },
        }
        with pytest.raises((SerializationError, ValidationError)):
            serializer.from_dict(d)

    def test_type_confusion_int_as_dict(self):
        """Int where dict expected must raise ValidationError."""
        d = {
            "stateweave_version": "0.2.0",
            "source_framework": "test",
            "metadata": {"agent_id": "type-confusion-2"},
            "cognitive_state": {
                "working_memory": 42
            },
        }
        with pytest.raises((SerializationError, ValidationError)):
            serializer.from_dict(d)

    @given(payload_data=st.dictionaries(
        st.text(max_size=30),
        json_value,
        max_size=15,
    ))
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_fuzz_arbitrary_dicts(self, payload_data):
        """Arbitrary dict structures must never crash the deserializer."""
        try:
            serializer.from_dict(payload_data)
        except (SerializationError, ValidationError, TypeError, KeyError):
            pass  # All acceptable

    def test_typed_loads_wrong_prefix(self):
        """loads_typed with wrong type prefix must raise SerializationError."""
        valid_bytes = serializer.dumps(
            StateWeavePayload(
                source_framework="test",
                metadata={"agent_id": "prefix-test"},
            )
        )
        with pytest.raises(SerializationError, match="Unknown type string"):
            serializer.loads_typed(("evil.prefix.v1.test", valid_bytes))

    def test_typed_loads_empty_type(self):
        """loads_typed with empty type string must raise."""
        valid_bytes = b'{"stateweave_version":"0.2.0","source_framework":"test","metadata":{"agent_id":"t"}}'
        with pytest.raises(SerializationError):
            serializer.loads_typed(("", valid_bytes))
