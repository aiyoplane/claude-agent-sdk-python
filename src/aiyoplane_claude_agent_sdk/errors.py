"""Typed errors raised by the AEAP Composition Boundary Adapter for the Claude Agent SDK."""

from __future__ import annotations

from typing import Any, Dict, Optional


class AiyoClaudeAgentSDKError(Exception):
    """Base class for all adapter-raised errors."""


class AdapterConfigError(AiyoClaudeAgentSDKError):
    """Adapter configuration is invalid. Fail-closed semantics."""


class BlockedByPolicy(AiyoClaudeAgentSDKError):
    """The RDP returned verdict=BLOCK. The tool MUST NOT execute."""

    def __init__(
        self,
        message: str,
        *,
        reason_code: Optional[str] = None,
        intent_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.intent_id = intent_id
        self.extra = extra or {}


class EscalationRequired(AiyoClaudeAgentSDKError):
    """The RDP returned verdict=ESCALATE. The tool call is held pending resolution."""

    def __init__(
        self,
        message: str,
        *,
        escalation_id: Optional[str] = None,
        intent_id: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.escalation_id = escalation_id
        self.intent_id = intent_id
        self.extra = extra or {}
