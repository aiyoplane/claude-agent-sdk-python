"""Tests for the AEAP Composition Boundary Adapter for the Claude Agent SDK."""

from __future__ import annotations

import pytest

from aiyoplane_claude_agent_sdk import (
    AdapterConfigError,
    BlockedByPolicy,
    EscalationRequired,
    aiyo_tool,
    wrap_tool_handler,
)


def _make_authz(rules):
    from aiyoplane_mcp_authz import create_aiyo_mcp_authz, create_local_rdp
    return create_aiyo_mcp_authz(
        rdp=create_local_rdp(policy={"rules": rules}),
        tool_config={"write_file": {"aiyo_gated": True, "action": {"type": "file_write"}}},
    )


def _write(path: str, content: str) -> str:
    return f"Wrote {len(content)} bytes to {path}"


def test_allow_runs_the_handler():
    authz = _make_authz([{"action_type": "file_write", "effect": "allow"}])
    gated = aiyo_tool(
        authz=authz,
        tool_name="write_file",
        intent_builder=lambda kw: {"type": "file_write", "path": kw["path"]},
    )(_write)
    assert "Wrote" in gated(path="/tmp/foo", content="hi")


def test_block_prevents_execution():
    authz = _make_authz([{"action_type": "file_write", "effect": "block"}])
    gated = aiyo_tool(
        authz=authz,
        tool_name="write_file",
        intent_builder=lambda kw: {"type": "file_write"},
    )(_write)
    with pytest.raises(BlockedByPolicy):
        gated(path="/etc/passwd", content="evil")


def test_escalate_raises():
    authz = _make_authz([{"action_type": "file_write", "effect": "escalate"}])
    gated = aiyo_tool(
        authz=authz,
        tool_name="write_file",
        intent_builder=lambda kw: {"type": "file_write"},
    )(_write)
    with pytest.raises((EscalationRequired, BlockedByPolicy)):
        gated(path="/home/user/foo", content="hi")


def test_broken_intent_builder_blocks():
    authz = _make_authz([{"action_type": "file_write", "effect": "allow"}])

    def _broken(kw):
        raise ValueError("broken")

    gated = aiyo_tool(authz=authz, tool_name="write_file", intent_builder=_broken)(_write)
    with pytest.raises(BlockedByPolicy):
        gated(path="/tmp/foo", content="hi")


def test_non_dict_intent_blocks():
    authz = _make_authz([{"action_type": "file_write", "effect": "allow"}])
    gated = aiyo_tool(
        authz=authz,
        tool_name="write_file",
        intent_builder=lambda kw: "not a dict",
    )(_write)
    with pytest.raises(BlockedByPolicy):
        gated(path="/tmp/foo", content="hi")


def test_non_callable_intent_builder_raises_config_error():
    authz = _make_authz([{"action_type": "file_write", "effect": "allow"}])
    with pytest.raises(AdapterConfigError):
        aiyo_tool(
            authz=authz,
            tool_name="write_file",
            intent_builder="not callable",  # type: ignore[arg-type]
        )


def test_wrap_tool_handler_function_form():
    authz = _make_authz([{"action_type": "file_write", "effect": "allow"}])
    gated = wrap_tool_handler(
        _write,
        authz=authz,
        tool_name="write_file",
        intent_builder=lambda kw: {"type": "file_write"},
    )
    assert "Wrote" in gated(path="/tmp/foo", content="hi")
