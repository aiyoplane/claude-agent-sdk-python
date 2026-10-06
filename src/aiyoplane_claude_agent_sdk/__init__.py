"""aiyoplane-claude-agent-sdk.

AEAP Composition Boundary Adapter for the Claude Agent SDK.

A thin wrapper that attaches the AEAP Runtime Decision Point (via
aiyoplane-mcp-authz) to the Claude Agent SDK tool invocation surface.
Especially useful for coding agents, whose consequential actions —
file write, command execution, dependency install, git push, deploy —
are AEAP-shaped problems par excellence.

Positioning: Claude can decide what it wants to do; AEAP provides an
independently verifiable authorization decision at the point where
consequential execution occurs.

Aiyoplane, Inc. - Apache 2.0 licensed.
https://aiyoplane.com

Specification: https://github.com/aiyoplane/aeap
"""

from aiyoplane_claude_agent_sdk.adapter import (
    IntentBuilder,
    aiyo_tool,
    wrap_tool_handler,
)
from aiyoplane_claude_agent_sdk.errors import (
    AdapterConfigError,
    AiyoClaudeAgentSDKError,
    BlockedByPolicy,
    EscalationRequired,
)

__version__ = "1.0.0"

__all__ = [
    "aiyo_tool",
    "wrap_tool_handler",
    "IntentBuilder",
    "AiyoClaudeAgentSDKError",
    "AdapterConfigError",
    "BlockedByPolicy",
    "EscalationRequired",
    "__version__",
]
