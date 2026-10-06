"""AEAP Composition Boundary Adapter for the Claude Agent SDK.

The Claude Agent SDK registers tools whose handlers execute on the client
side when Claude requests them. This adapter wraps those handlers so the
AEAP Runtime Decision Point evaluates an Intent before the handler runs.

Coding-agent surfaces are the standout use case: file write, command
execution, dependency install, git push, deployment. Each of these is a
consequential action whose authorization should sit at the exact moment
between intent formation and execution — AEAP's exact remit.

Usage (decorator)
-----------------

    from aiyoplane_mcp_authz import create_aiyo_mcp_authz, create_local_rdp
    from aiyoplane_claude_agent_sdk import aiyo_tool

    authz = create_aiyo_mcp_authz(
        rdp=create_local_rdp(policy=my_policy),
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

    # Register with your Claude Agent the usual way.

Fail-closed semantics
---------------------

Every ambiguous condition — missing intent_builder, non-dict Intent, RDP
unreachable — results in BlockedByPolicy. The adapter never fails open.
"""

from __future__ import annotations

import asyncio
import functools
import inspect
from typing import Any, Awaitable, Callable, Dict, Union

from aiyoplane_claude_agent_sdk.errors import (
    AdapterConfigError,
    BlockedByPolicy,
    EscalationRequired,
)

# Signature: (tool_kwargs: Dict[str, Any]) -> Dict[str, Any]
IntentBuilder = Callable[[Dict[str, Any]], Dict[str, Any]]

ToolCallable = Callable[..., Union[Any, Awaitable[Any]]]


def _build_intent(builder: IntentBuilder, kwargs: Dict[str, Any], tool_name: str) -> Dict[str, Any]:
    if not callable(builder):
        raise AdapterConfigError(f"intent_builder for tool '{tool_name}' is not callable")
    try:
        intent = builder(kwargs)
    except Exception as exc:
        raise BlockedByPolicy(
            f"intent_builder for tool '{tool_name}' raised: {exc!r}",
            reason_code="INTENT_BUILD_FAILED",
        ) from exc
    if not isinstance(intent, dict):
        raise BlockedByPolicy(
            f"intent_builder for tool '{tool_name}' did not return a dict",
            reason_code="INTENT_SHAPE_INVALID",
        )
    return intent


async def _evaluate_rdp(authz: Any, tool_name: str, intent: Dict[str, Any]) -> Any:
    if authz is None or not hasattr(authz, "wrap"):
        raise AdapterConfigError("received an invalid authz (missing .wrap)")
    try:
        wrap = authz.wrap(tool_name)
    except Exception as exc:
        raise BlockedByPolicy(
            f"authz.wrap('{tool_name}') failed: {exc!r}",
            reason_code=type(exc).__name__,
        ) from exc

    async def _passthrough(args: Dict[str, Any], ctx: Any) -> Any:
        return ctx

    wrapped = wrap(_passthrough)

    try:
        if inspect.iscoroutinefunction(wrapped):
            ctx = await wrapped(dict(intent), None)
        else:
            ctx = wrapped(dict(intent), None)
            if inspect.isawaitable(ctx):
                ctx = await ctx
    except Exception as exc:
        msg = str(exc)
        if "escalat" in msg.lower() or "ESCALATE" in msg:
            raise EscalationRequired(
                f"AEAP ESCALATE verdict for tool '{tool_name}' (intent={intent!r}): {msg}",
                extra={"inner_exception": type(exc).__name__, "intent": intent},
            ) from exc
        raise BlockedByPolicy(
            f"AEAP non-ALLOW verdict for tool '{tool_name}' (intent={intent!r}): {msg}",
            reason_code=type(exc).__name__,
            extra={"inner_exception": type(exc).__name__, "intent": intent},
        ) from exc
    return ctx


def aiyo_tool(
    *,
    authz: Any,
    tool_name: str,
    intent_builder: IntentBuilder,
    attach_receipt: bool = False,
) -> Callable[[ToolCallable], ToolCallable]:
    """Decorator attaching an AEAP Composition Boundary to a Claude Agent SDK tool handler."""
    if not callable(intent_builder):
        raise AdapterConfigError("aiyo_tool requires an intent_builder callable")
    if not isinstance(tool_name, str) or not tool_name:
        raise AdapterConfigError("aiyo_tool requires a non-empty tool_name")

    def decorator(fn: ToolCallable) -> ToolCallable:
        if not callable(fn):
            raise AdapterConfigError(f"aiyo_tool must decorate a callable, got {type(fn).__name__}")

        is_coro = inspect.iscoroutinefunction(fn)

        if is_coro:
            @functools.wraps(fn)
            async def async_wrapped(**kwargs: Any) -> Any:
                intent = _build_intent(intent_builder, kwargs, tool_name)
                ctx = await _evaluate_rdp(authz, tool_name, intent)
                result = await fn(**kwargs)
                if attach_receipt:
                    return {"result": result, "aeap_receipt": getattr(ctx, "receipt", None)}
                return result
            return async_wrapped

        @functools.wraps(fn)
        def sync_wrapped(**kwargs: Any) -> Any:
            intent = _build_intent(intent_builder, kwargs, tool_name)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import nest_asyncio  # type: ignore
                    nest_asyncio.apply()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            ctx = loop.run_until_complete(_evaluate_rdp(authz, tool_name, intent))
            result = fn(**kwargs)
            if attach_receipt:
                return {"result": result, "aeap_receipt": getattr(ctx, "receipt", None)}
            return result

        return sync_wrapped

    return decorator


def wrap_tool_handler(
    fn: ToolCallable,
    *,
    authz: Any,
    tool_name: str,
    intent_builder: IntentBuilder,
    attach_receipt: bool = False,
) -> ToolCallable:
    """Function form of :func:`aiyo_tool`."""
    return aiyo_tool(
        authz=authz,
        tool_name=tool_name,
        intent_builder=intent_builder,
        attach_receipt=attach_receipt,
    )(fn)
