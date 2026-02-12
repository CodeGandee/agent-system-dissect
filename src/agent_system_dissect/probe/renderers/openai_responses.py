"""
Body renderers for the OpenAI Responses API format.

Renders request bodies (model/instructions/input/tools) and SSE response
bodies (event breakdown/output text/reasoning/tool calls/usage) as
summarized Markdown.  Shared across any target that uses the OpenAI API.

Functions
---------
format_request_body : Render an OpenAI Responses API request body.
format_response_body : Render an OpenAI SSE response body.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from agent_system_dissect.probe.tools.traffic.sse import parse_sse_events


# ---------------------------------------------------------------------------
# Request body
# ---------------------------------------------------------------------------


def format_request_body(body: Any) -> str:
    """
    Render an OpenAI Responses API request body as summarized Markdown.

    For dict bodies the output highlights model/config fields, system
    instructions (collapsed), input messages (table + collapsible full
    content), and tool definitions.  Non-dict bodies are wrapped in a
    ``<details>`` code block.

    Parameters
    ----------
    body : Any
        Parsed request body — typically a dict from the Responses API,
        but may be ``None``, a raw string, or another type.

    Returns
    -------
    str
        Markdown text summarising the request body.
    """
    if body is None:
        return "*(no body)*"
    if isinstance(body, str):
        return (
            f"<details>\n<summary><b>Body</b> ({len(body):,} bytes)</summary>"
            f"\n\n```\n{body}\n```\n</details>"
        )
    if not isinstance(body, dict):
        text = str(body)
        return (
            f"<details>\n<summary><b>Body</b> ({len(text):,} bytes)</summary>"
            f"\n\n```\n{text}\n```\n</details>"
        )

    lines: list[str] = []

    # Model & config fields
    model = body.get("model", "unknown")
    config_parts = [f"**Model:** `{model}`"]
    for key in ("stream", "tool_choice", "parallel_tool_calls", "store"):
        if key in body:
            config_parts.append(f"**{key}:** `{body[key]}`")
    if body.get("reasoning"):
        reasoning = body["reasoning"]
        if isinstance(reasoning, dict):
            summary = reasoning.get("summary", reasoning.get("effort", ""))
            config_parts.append(f"**reasoning:** `{summary}`")
    lines.append(" | ".join(config_parts))
    lines.append("")

    # System instructions
    instructions = body.get("instructions", "")
    if instructions:
        char_count = len(instructions)
        preview = instructions[:500]
        if len(instructions) > 500:
            preview += "..."
        lines.append(
            f"<details>\n<summary><b>System Instructions</b>"
            f" ({char_count:,} chars)</summary>\n\n```\n{preview}\n```\n</details>"
        )
        lines.append("")

    # Input messages
    input_msgs = body.get("input", [])
    if input_msgs:
        lines.append(f"**Input Messages** ({len(input_msgs)} items):")
        lines.append("")
        lines.append("| # | Role | Type | Content Preview |")
        lines.append("|---|------|------|-----------------|")
        for idx, msg in enumerate(input_msgs):
            role = msg.get("role", "-")
            msg_type = msg.get("type", "-")
            content = msg.get("content")
            preview = _message_content_preview(content)
            lines.append(f"| {idx} | {role} | {msg_type} | {preview} |")
        lines.append("")

        # Collapsible full content for each message
        for idx, msg in enumerate(input_msgs):
            content = msg.get("content")
            full_text = _message_content_full(content)
            if full_text and len(full_text) > 120:
                role = msg.get("role", "-")
                lines.append(
                    f"<details>\n<summary>Message {idx} ({role}) full content"
                    f" ({len(full_text):,} chars)</summary>"
                    f"\n\n```\n{full_text}\n```\n</details>"
                )
                lines.append("")

    # Tools
    tools = body.get("tools", [])
    if tools:
        tool_items = []
        for t in tools:
            name = t.get("name") or "(unnamed)"
            ttype = t.get("type", "function")
            tool_items.append(f"- `{name}` ({ttype})")
        lines.append(
            f"<details>\n<summary><b>Tools</b> ({len(tools)} defined)</summary>\n\n"
            + "\n".join(tool_items)
            + "\n</details>"
        )
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Response body
# ---------------------------------------------------------------------------


def format_response_body(body: Any, status_code: int) -> str:  # noqa: ARG001
    """
    Render an OpenAI SSE response body as summarized Markdown.

    For SSE streams the output includes an event-type breakdown table,
    assembled output text and reasoning summary (collapsed), tool call
    details, and token usage statistics.  Non-SSE bodies are wrapped in
    a ``<details>`` code block.

    Parameters
    ----------
    body : Any
        Response body — typically a raw SSE string, but may be ``None``,
        a dict (non-streaming JSON response), or another type.
    status_code : int
        HTTP status code of the response (currently unused, reserved for
        future error-specific rendering).

    Returns
    -------
    str
        Markdown text summarising the response body.
    """
    if body is None:
        return "*(no body)*"

    # Non-string bodies (dict): render as JSON in <details>
    if isinstance(body, dict):
        formatted = json.dumps(body, indent=2)
        return (
            f"<details>\n<summary><b>Body</b> ({len(formatted):,} bytes)</summary>"
            f"\n\n```json\n{formatted}\n```\n</details>"
        )

    if not isinstance(body, str):
        text = str(body)
        return (
            f"<details>\n<summary><b>Body</b> ({len(text):,} bytes)</summary>"
            f"\n\n```\n{text}\n```\n</details>"
        )

    # Check if this is an SSE stream
    if not body.lstrip().startswith("event:"):
        return (
            f"<details>\n<summary><b>Body</b> ({len(body):,} bytes)</summary>"
            f"\n\n```\n{body}\n```\n</details>"
        )

    # Parse SSE events
    events = parse_sse_events(body)
    event_type_counts: Counter[str] = Counter(e["event"] for e in events)

    lines: list[str] = []
    lines.append(f"**SSE Stream** ({len(body):,} bytes, {len(events)} events)")
    lines.append("")

    # Event type breakdown
    lines.append("| Event Type | Count |")
    lines.append("|------------|-------|")
    for etype, count in event_type_counts.most_common():
        lines.append(f"| `{etype}` | {count} |")
    lines.append("")

    # Assemble output text from delta events
    output_text_parts: list[str] = []
    reasoning_text_parts: list[str] = []
    tool_calls: list[dict[str, str]] = []
    usage = None

    for e in events:
        etype = e["event"]
        data = e.get("data")
        if not isinstance(data, dict):
            continue

        if etype == "response.output_text.delta":
            output_text_parts.append(data.get("delta", ""))
        elif etype == "response.reasoning_summary_text.delta":
            reasoning_text_parts.append(data.get("delta", ""))
        elif etype == "response.function_call_arguments.done":
            tool_calls.append({
                "name": data.get("name", "(unnamed)"),
                "call_id": data.get("call_id", ""),
                "arguments": data.get("arguments", ""),
            })
        elif etype == "response.completed":
            resp = data.get("response", {})
            usage = resp.get("usage")

    # Output text
    if output_text_parts:
        output_text = "".join(output_text_parts)
        lines.append(
            f"<details>\n<summary><b>Output Text</b>"
            f" ({len(output_text):,} chars)</summary>"
            f"\n\n```\n{output_text}\n```\n</details>"
        )
        lines.append("")

    # Reasoning summary
    if reasoning_text_parts:
        reasoning_text = "".join(reasoning_text_parts)
        lines.append(
            f"<details>\n<summary><b>Reasoning Summary</b>"
            f" ({len(reasoning_text):,} chars)</summary>"
            f"\n\n```\n{reasoning_text}\n```\n</details>"
        )
        lines.append("")

    # Tool calls
    if tool_calls:
        lines.append(f"**Tool Calls** ({len(tool_calls)}):")
        lines.append("")
        for tc in tool_calls:
            lines.append(f'- `{tc["name"]}` (call_id: `{tc["call_id"]}`)')
            if tc["arguments"]:
                args_preview = tc["arguments"][:300]
                if len(tc["arguments"]) > 300:
                    args_preview += "..."
                lines.append(f"  ```\n  {args_preview}\n  ```")
        lines.append("")

    # Usage statistics
    if usage:
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        usage_parts = [
            f"{input_tokens:,} input",
            f"{output_tokens:,} output",
            f"{total_tokens:,} total",
        ]
        input_details = usage.get("input_tokens_details", {})
        output_details = usage.get("output_tokens_details", {})
        detail_parts = []
        if input_details.get("cached_tokens"):
            detail_parts.append(f"{input_details['cached_tokens']:,} cached")
        if output_details.get("reasoning_tokens"):
            detail_parts.append(f"{output_details['reasoning_tokens']:,} reasoning")
        usage_str = f"**Usage:** {' | '.join(usage_parts)}"
        if detail_parts:
            usage_str += f" ({', '.join(detail_parts)})"
        lines.append(usage_str)
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _message_content_preview(content: Any, max_len: int = 80) -> str:
    """Return a short single-line text preview from message content."""
    if content is None:
        return "*(none)*"
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict):
                texts.append(item.get("text", ""))
        text = " ".join(texts)
    else:
        text = str(content)
    text = text.replace("\n", " ").strip()
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text if text else "*(empty)*"


def _message_content_full(content: Any) -> str:
    """Return the full text extracted from message content."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict):
                texts.append(item.get("text", ""))
        return "\n".join(texts)
    return str(content)
