"""Minimal example of aiyoplane-claude-agent-sdk.

Simulates a coding-agent surface with a file_write tool. Runs in-process;
no network, no credentials.

Run: python examples/minimal.py
"""

from __future__ import annotations

from aiyoplane_mcp_authz import create_aiyo_mcp_authz, create_local_rdp
from aiyoplane_claude_agent_sdk import (
    BlockedByPolicy,
    EscalationRequired,
    aiyo_tool,
)


def main() -> None:
    policy = {
        "rules": [
            {"action_type": "file_write", "path_prefix": "/tmp/", "effect": "allow"},
            {"action_type": "file_write", "path_prefix": "/etc/", "effect": "block"},
            {"action_type": "file_write", "effect": "escalate"},
        ]
    }

    authz = create_aiyo_mcp_authz(
        rdp=create_local_rdp(policy=policy),
        tool_config={
            "write_file": {"aiyo_gated": True, "action": {"type": "file_write"}},
        },
    )

    @aiyo_tool(
        authz=authz,
        tool_name="write_file",
        intent_builder=lambda kw: {
            "type": "file_write",
            "path": kw["path"],
            "bytes": len(kw.get("content", "")),
        },
    )
    def write_file(path: str, content: str) -> str:
        return f"Wrote {len(content)} bytes to {path}"

    print("ALLOW (/tmp/foo):")
    print("  ", write_file(path="/tmp/foo.txt", content="hello"))

    print("\nESCALATE (/home/user/foo):")
    try:
        write_file(path="/home/user/foo.txt", content="hello")
    except EscalationRequired as exc:
        print("  Held:", exc)

    print("\nBLOCK (/etc/passwd):")
    try:
        write_file(path="/etc/passwd", content="evil")
    except BlockedByPolicy as exc:
        print("  Blocked:", exc)


if __name__ == "__main__":
    main()
