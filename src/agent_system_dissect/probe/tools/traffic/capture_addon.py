"""
Mitmproxy addon that logs request/response pairs to JSONL.

This file is loaded by mitmdump via the ``-s`` flag and MUST remain
self-contained — it cannot import from the ``agent_system_dissect``
package because mitmdump runs it in its own Python environment.

Output path is controlled by the ``TRAFFIC_OUTPUT_DIR`` environment
variable.  If unset, output goes to the parent directory of this script.

Functions
---------
load : Called by mitmproxy on addon load; logs output path.
response : Called on each completed HTTP flow; appends to JSONL.
"""

import fcntl
import json
import os
import time

from mitmproxy import ctx, http

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.environ.get("TRAFFIC_OUTPUT_DIR", os.path.dirname(SCRIPT_DIR))
OUTPUT = os.path.join(OUTPUT_DIR, "traffic.jsonl")


def load(loader):  # noqa: ARG001
    """Log the output path when the addon is loaded by mitmproxy."""
    ctx.log.info(f"Capture addon loaded. Output: {OUTPUT}")


def response(flow: http.HTTPFlow) -> None:
    """
    Intercept a completed HTTP flow and append it to the JSONL log.

    Writes one JSON object per line containing timestamp, request
    (method, URL, headers, body) and response (status, headers, body).
    SSE responses are stored as raw text; JSON bodies are parsed.
    File-level locking prevents interleaved writes when multiple
    mitmdump instances share the same output file.

    Parameters
    ----------
    flow : mitmproxy.http.HTTPFlow
        The completed HTTP request/response flow.
    """
    ctx.log.info(
        f"FLOW: {flow.request.method} {flow.request.pretty_url}"
        f" -> {flow.response.status_code}"
    )

    req_body = None
    if flow.request.content:
        try:
            req_body = json.loads(flow.request.content)
        except Exception:
            req_body = flow.request.content.decode("utf-8", errors="replace")

    resp_body = None
    if flow.response and flow.response.content:
        content_type = flow.response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            resp_body = flow.response.content.decode("utf-8", errors="replace")
        else:
            try:
                resp_body = json.loads(flow.response.content)
            except Exception:
                resp_body = flow.response.content.decode("utf-8", errors="replace")

    entry = {
        "timestamp": time.time(),
        "request": {
            "method": flow.request.method,
            "url": flow.request.pretty_url,
            "headers": dict(flow.request.headers),
            "body": req_body,
        },
        "response": {
            "status_code": flow.response.status_code if flow.response else None,
            "headers": dict(flow.response.headers) if flow.response else None,
            "body": resp_body,
        },
    }

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    line = json.dumps(entry) + "\n"
    with open(OUTPUT, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(line)
        f.flush()
        fcntl.flock(f, fcntl.LOCK_UN)
