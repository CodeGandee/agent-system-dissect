"""
Generic traffic analyzer — reads JSONL, produces a Markdown report.

Provides a target-agnostic analysis framework.  Statistics (endpoints,
methods, status codes, payload structure) are computed generically.
Body rendering is delegated to the ``AnalysisProfile``'s pluggable
renderer callables.

Functions
---------
load_entries : Parse a JSONL file into a list of dicts.
type_name : Return a human-readable type label for a value.
extract_keys : Recursively extract dotted key paths with types.
analyze : Compute aggregate statistics from traffic entries.
redact_headers : Replace sensitive header values with ``[REDACTED]``.
format_conversations : Render the full conversation log section.
format_report : Assemble the complete Markdown report.
load_analysis_profile : Import an AnalysisProfile by target name.
main : CLI entry point.

Examples
--------
::

    python -m agent_system_dissect.probe.tools.traffic.analyze \\
        --target codex \\
        --input  tmp/codex-traffic/traffic.jsonl \\
        --output tmp/codex-traffic/analysis_report.md
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from agent_system_dissect.probe.tools.traffic.types import AnalysisProfile


# ---------------------------------------------------------------------------
# JSONL loading
# ---------------------------------------------------------------------------


def load_entries(path: str) -> list[dict]:
    """
    Load traffic entries from a JSONL file.

    Parameters
    ----------
    path : str
        Filesystem path to the ``.jsonl`` file.

    Returns
    -------
    list of dict
        Parsed JSON objects, one per non-empty line.  Malformed lines
        are skipped with a warning to stderr.
    """
    entries: list[dict] = []
    with open(path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"WARNING: skipping malformed line {i}: {e}", file=sys.stderr)
    return entries


# ---------------------------------------------------------------------------
# Payload structure helpers
# ---------------------------------------------------------------------------


def type_name(v: Any) -> str:
    """
    Return a human-readable type label for a JSON-like value.

    Parameters
    ----------
    v : Any
        The value to classify.

    Returns
    -------
    str
        One of ``"null"``, ``"bool"``, ``"int"``, ``"float"``,
        ``"string"``, ``"array"``, ``"object"``, or the Python type name.
    """
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    if isinstance(v, dict):
        return "object"
    return type(v).__name__


def extract_keys(obj: Any, prefix: str = "") -> list[tuple[str, str]]:
    """
    Recursively extract dotted key paths with data types.

    Parameters
    ----------
    obj : Any
        A parsed JSON value (dict, list, or scalar).
    prefix : str, optional
        Dotted path prefix accumulated during recursion.

    Returns
    -------
    list of (str, str)
        Tuples of ``(dotted_key_path, type_label)``.
    """
    keys: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            full = f"{prefix}.{k}" if prefix else k
            keys.append((full, type_name(v)))
            keys.extend(extract_keys(v, full))
    elif isinstance(obj, list) and obj:
        keys.extend(extract_keys(obj[0], f"{prefix}[]"))
    return keys


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def analyze(entries: list[dict]) -> dict:
    """
    Compute aggregate statistics from traffic entries.

    Parameters
    ----------
    entries : list of dict
        Parsed JSONL entries, each containing ``request`` and ``response``
        sub-dicts.

    Returns
    -------
    dict
        Keys include ``total_requests``, ``duration_seconds``,
        ``endpoint_counts``, ``method_counts``, ``status_counts``,
        ``endpoint_methods``, ``request_key_counts``,
        ``response_key_counts``, ``request_key_types``,
        ``response_key_types``, ``total_req_bytes``,
        ``total_resp_bytes``.
    """
    endpoint_counts: Counter[str] = Counter()
    method_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    request_key_counts: Counter[str] = Counter()
    response_key_counts: Counter[str] = Counter()
    request_key_types: dict[str, set[str]] = defaultdict(set)
    response_key_types: dict[str, set[str]] = defaultdict(set)
    endpoint_methods: dict[str, set[str]] = defaultdict(set)
    timestamps: list[float] = []
    total_req_bytes = 0
    total_resp_bytes = 0

    for entry in entries:
        req = entry.get("request", {})
        resp = entry.get("response", {})
        url = req.get("url", "")
        method = req.get("method", "?")
        status = resp.get("status_code")
        ts = entry.get("timestamp")

        parsed = urlparse(url)
        endpoint = parsed.path or "/"
        endpoint_counts[endpoint] += 1
        method_counts[method] += 1
        endpoint_methods[endpoint].add(method)
        if status is not None:
            status_counts[str(status)] += 1
        if ts:
            timestamps.append(ts)

        req_body = req.get("body")
        if isinstance(req_body, dict):
            for key, dtype in extract_keys(req_body):
                request_key_counts[key] += 1
                request_key_types[key].add(dtype)
        if isinstance(req_body, (str, bytes)):
            total_req_bytes += (
                len(req_body) if isinstance(req_body, bytes) else len(req_body.encode())
            )
        elif req_body is not None:
            total_req_bytes += len(json.dumps(req_body))

        resp_body = resp.get("body")
        if isinstance(resp_body, dict):
            for key, dtype in extract_keys(resp_body):
                response_key_counts[key] += 1
                response_key_types[key].add(dtype)
        if isinstance(resp_body, (str, bytes)):
            total_resp_bytes += (
                len(resp_body)
                if isinstance(resp_body, bytes)
                else len(resp_body.encode())
            )
        elif resp_body is not None:
            total_resp_bytes += len(json.dumps(resp_body))

    duration = max(timestamps) - min(timestamps) if len(timestamps) >= 2 else 0

    return {
        "total_requests": len(entries),
        "duration_seconds": round(duration, 1),
        "endpoint_counts": endpoint_counts.most_common(),
        "method_counts": method_counts.most_common(),
        "status_counts": status_counts.most_common(),
        "endpoint_methods": {k: sorted(v) for k, v in endpoint_methods.items()},
        "request_key_counts": request_key_counts.most_common(30),
        "response_key_counts": response_key_counts.most_common(30),
        "request_key_types": request_key_types,
        "response_key_types": response_key_types,
        "total_req_bytes": total_req_bytes,
        "total_resp_bytes": total_resp_bytes,
    }


# ---------------------------------------------------------------------------
# Header redaction
# ---------------------------------------------------------------------------


def redact_headers(headers: dict[str, str], redacted: set[str]) -> dict[str, str]:
    """
    Replace sensitive header values with a redaction marker.

    Parameters
    ----------
    headers : dict of str to str
        Raw HTTP headers.
    redacted : set of str
        Lowercase header names to redact.

    Returns
    -------
    dict of str to str
        A copy of *headers* with matching values replaced by
        ``"[REDACTED]"`` (or a truncated prefix followed by
        ``"...[REDACTED]"``).
    """
    result: dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() in redacted:
            result[k] = v[:20] + "...[REDACTED]" if len(v) > 20 else "[REDACTED]"
        else:
            result[k] = v
    return result


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def format_conversations(entries: list[dict], profile: AnalysisProfile) -> str:
    """
    Format the full conversation log section of the report.

    Each request/response pair is rendered with redacted headers and
    body content produced by the profile's pluggable renderers.

    Parameters
    ----------
    entries : list of dict
        Parsed JSONL traffic entries.
    profile : AnalysisProfile
        Provides body renderers and header redaction rules.

    Returns
    -------
    str
        Markdown text for the conversation log section.
    """
    lines: list[str] = []
    lines.append("## Full Conversation Log")
    lines.append("")

    for i, entry in enumerate(entries, 1):
        req = entry.get("request", {})
        resp = entry.get("response", {})
        ts = entry.get("timestamp", 0)
        ts_str = (
            datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%H:%M:%S.%f")[:-3]
            if ts
            else "?"
        )

        method = req.get("method", "?")
        url = req.get("url", "?")
        status = resp.get("status_code", "?")
        headers = req.get("headers", {})
        resp_headers = resp.get("headers", {})

        lines.append(f"### Request {i}: `{method} {url}` → {status}")
        lines.append(f"**Time:** {ts_str} UTC")
        lines.append("")

        # Request headers (redacted)
        lines.append("<details>")
        lines.append("<summary><b>Request Headers</b></summary>")
        lines.append("")
        lines.append("```")
        for k, v in redact_headers(headers, profile.redacted_headers).items():
            lines.append(f"{k}: {v}")
        lines.append("```")
        lines.append("</details>")
        lines.append("")

        # Request body — delegated to profile renderer
        lines.append("#### Request Body")
        lines.append("")
        lines.append(profile.request_body_renderer(req.get("body")))
        lines.append("")

        # Response headers
        lines.append("<details>")
        lines.append("<summary><b>Response Headers</b></summary>")
        lines.append("")
        lines.append("```")
        for k, v in redact_headers(resp_headers, profile.redacted_headers).items():
            lines.append(f"{k}: {v}")
        lines.append("```")
        lines.append("</details>")
        lines.append("")

        # Response body — delegated to profile renderer
        lines.append("#### Response Body")
        lines.append("")
        lines.append(profile.response_body_renderer(resp.get("body"), status))
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def format_report(
    analysis_data: dict,
    entries: list[dict],
    input_path: str,
    profile: AnalysisProfile,
) -> str:
    """
    Assemble the complete Markdown analysis report.

    Parameters
    ----------
    analysis_data : dict
        Output of :func:`analyze`.
    entries : list of dict
        Parsed JSONL traffic entries.
    input_path : str
        Path to the source JSONL file (shown in the report header).
    profile : AnalysisProfile
        Provides report title, body renderers, and header redaction.

    Returns
    -------
    str
        The full Markdown report text.
    """
    lines: list[str] = []
    lines.append(f"# {profile.report_title}")
    lines.append("")
    lines.append(f"**Source:** `{input_path}`")
    lines.append(
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    lines.append(f"**Total requests:** {analysis_data['total_requests']}")
    lines.append(f"**Capture duration:** {analysis_data['duration_seconds']}s")
    lines.append(f"**Total request payload:** {analysis_data['total_req_bytes']:,} bytes")
    lines.append(
        f"**Total response payload:** {analysis_data['total_resp_bytes']:,} bytes"
    )
    lines.append("")

    # Endpoint summary
    lines.append("## Endpoints")
    lines.append("")
    lines.append("| Endpoint | Methods | Count |")
    lines.append("|----------|---------|-------|")
    for endpoint, count in analysis_data["endpoint_counts"]:
        methods = ", ".join(
            analysis_data["endpoint_methods"].get(endpoint, [])
        )
        lines.append(f"| `{endpoint}` | {methods} | {count} |")
    lines.append("")

    # HTTP methods
    lines.append("## HTTP Methods")
    lines.append("")
    lines.append("| Method | Count |")
    lines.append("|--------|-------|")
    for method, count in analysis_data["method_counts"]:
        lines.append(f"| {method} | {count} |")
    lines.append("")

    # Status codes
    lines.append("## Response Status Codes")
    lines.append("")
    lines.append("| Status | Count |")
    lines.append("|--------|-------|")
    for status, count in analysis_data["status_counts"]:
        lines.append(f"| {status} | {count} |")
    lines.append("")

    # Request payload structure
    if analysis_data["request_key_counts"]:
        lines.append("## Request Payload Structure (Top Keys)")
        lines.append("")
        lines.append("| Key Path | Type | Occurrences |")
        lines.append("|----------|------|-------------|")
        for key, count in analysis_data["request_key_counts"]:
            types = ", ".join(
                sorted(analysis_data["request_key_types"].get(key, set()))
            )
            lines.append(f"| `{key}` | {types} | {count} |")
        lines.append("")

    # Response payload structure
    if analysis_data["response_key_counts"]:
        lines.append("## Response Payload Structure (Top Keys)")
        lines.append("")
        lines.append("| Key Path | Type | Occurrences |")
        lines.append("|----------|------|-------------|")
        for key, count in analysis_data["response_key_counts"]:
            types = ", ".join(
                sorted(analysis_data["response_key_types"].get(key, set()))
            )
            lines.append(f"| `{key}` | {types} | {count} |")
        lines.append("")

    # Full conversation log
    lines.append(format_conversations(entries, profile))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Target discovery
# ---------------------------------------------------------------------------


def load_analysis_profile(target_name: str) -> AnalysisProfile:
    """
    Load an AnalysisProfile by target name.

    Parameters
    ----------
    target_name : str
        Target identifier (e.g. ``"codex"``).  Maps to
        ``agent_system_dissect.probe.targets.<target_name>.traffic``.

    Returns
    -------
    AnalysisProfile
        The target's analysis profile.
    """
    module = importlib.import_module(
        f"agent_system_dissect.probe.targets.{target_name}.traffic"
    )
    return module.analysis_profile  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse CLI arguments, load the target profile, and run analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze captured traffic and produce a Markdown report."
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Target name (e.g., 'codex') — loads the matching AnalysisProfile.",
    )
    parser.add_argument("--input", required=True, help="Path to traffic.jsonl")
    parser.add_argument(
        "--output",
        default=None,
        help="Path to write the Markdown report (default: <input_dir>/analysis_report.md)",
    )
    args = parser.parse_args()

    profile = load_analysis_profile(args.target)

    input_path = args.input
    output_path = args.output or os.path.join(
        os.path.dirname(input_path), "analysis_report.md"
    )

    if not os.path.exists(input_path):
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    entries = load_entries(input_path)
    if not entries:
        print(f"ERROR: no valid entries in {input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(entries)} entries from {input_path}")
    analysis_data = analyze(entries)
    report = format_report(analysis_data, entries, input_path, profile)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report)
    print(f"Report written to {output_path}")


if __name__ == "__main__":
    main()
