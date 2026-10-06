# aiyoplane-claude-agent-sdk

**AEAP Composition Boundary Adapter for the Claude Agent SDK.**

A thin wrapper that attaches the AEAP Runtime Decision Point (RDP) to the Claude Agent SDK's tool-invocation surface. Consequential tool executions — file writes, command execution, dependency installs, git pushes, deployments — produce independently verifiable Execution Receipts.

```bash
pip install aiyoplane-claude-agent-sdk
```

## Why coding-agent surfaces specifically

Coding agents produce some of the clearest consequential execution boundaries imaginable:

```
read file  →  modify file  →  run command  →  install dependency  →  git push  →  deploy  →  production
```

Each of those arrows crosses a Composition Boundary. The question *"may this agent perform this class of action?"* is handled by identity, delegation, and runtime permissions. The question *"should this specific file write / this specific command / this specific deploy execute right now, under the Protected Party's current Policy?"* is AEAP's territory. The two layers compose. AEAP does not replace permission-aware tool design; it adds a protocol-level authorization decision at the moment execution happens.

**Positioning:** Claude can decide what it wants to do. AEAP provides an independently verifiable authorization decision at the point where consequential execution occurs. The two are complementary — different layers of the stack.

See the [AEAP specification](https://github.com/aiyoplane/aeap) §9.

## Minimal usage — decorator

```python
from aiyoplane_mcp_authz import create_aiyo_mcp_authz, create_local_rdp
from aiyoplane_claude_agent_sdk import aiyo_tool, BlockedByPolicy, EscalationRequired

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
        "bytes": len(kw["content"]),
    },
)
def write_file(path: str, content: str) -> str:
    with open(path, "w") as f:
        f.write(content)
    return f"Wrote {len(content)} bytes to {path}"

# Register with your Claude Agent SDK agent the usual way.
```

## Minimal usage — function form

```python
from aiyoplane_claude_agent_sdk import wrap_tool_handler

def write_file(path: str, content: str) -> str:
    with open(path, "w") as f:
        f.write(content)
    return f"Wrote {len(content)} bytes to {path}"

guarded = wrap_tool_handler(
    write_file,
    authz=authz,
    tool_name="write_file",
    intent_builder=lambda kw: {"type": "file_write", "path": kw["path"]},
)
```

## Example coding-agent policies

Example policy for a coding agent that may freely read, cautiously write, and never deploy without human approval:

```python
policy = {
    "rules": [
        # Reads are not consequential — they don't appear in tool_config as aiyo_gated.
        # Writes to /tmp allowed.
        {"action_type": "file_write", "path_prefix": "/tmp/", "effect": "allow"},
        # Writes to the project workspace allowed if under a size threshold.
        {"action_type": "file_write", "path_prefix": "./src/", "bytes_max": 50_000, "effect": "allow"},
        # Writes anywhere else require escalation.
        {"action_type": "file_write", "effect": "escalate"},
        # Shell command execution always escalates to a human.
        {"action_type": "shell_exec", "effect": "escalate"},
        # Deploys always escalate.
        {"action_type": "deploy", "effect": "escalate"},
        # git push always escalates.
        {"action_type": "git_push", "effect": "escalate"},
    ]
}
```

## Composition Boundary — what the adapter actually does

1. **Intent construction** via `intent_builder(tool_kwargs)`.
2. **RDP evaluation** via `aiyoplane-mcp-authz`.
3. **Verdict composition.** ALLOW → inner handler runs; ESCALATE → `EscalationRequired`; BLOCK → `BlockedByPolicy`.
4. **Fail-closed default** on every ambiguous condition.

## Local vs. hosted RDP

```python
from aiyoplane_mcp_authz import create_local_rdp, create_hosted_rdp

# Development:
authz = create_aiyo_mcp_authz(rdp=create_local_rdp(policy=policy), tool_config={...})

# Production:
authz = create_aiyo_mcp_authz(
    rdp=create_hosted_rdp(api_key="aiyo_live_..."),
    tool_config={...},
)
```

## API reference

### `aiyo_tool(*, authz, tool_name, intent_builder, attach_receipt=False)`
Decorator form.

### `wrap_tool_handler(fn, *, authz, tool_name, intent_builder, attach_receipt=False)`
Function form.

### Exceptions

- `AiyoClaudeAgentSDKError`, `AdapterConfigError`, `BlockedByPolicy`, `EscalationRequired`

## License

Apache License 2.0.

## Links

- **AEAP specification:** https://github.com/aiyoplane/aeap
- **Underlying implementation:** [`aiyoplane-mcp-authz`](https://pypi.org/project/aiyoplane-mcp-authz/)
- **Node sibling:** `@aiyoplane/claude-agent-sdk` on npm
- **Trust surface:** https://aiyoplane.com/trust
- **Issues:** https://github.com/aiyoplane/claude-agent-sdk-python/issues

Claude and the Claude Agent SDK are trademarks of Anthropic, PBC. This package is an independent AEAP Composition Boundary Adapter and is not affiliated with or endorsed by Anthropic, PBC.

**Verify First. Execute Second.**
