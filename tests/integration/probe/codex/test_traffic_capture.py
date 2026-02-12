"""Integration test for codex traffic capture.

This is a mitmproxy addon for manual testing — load via:
    mitmdump -p 8080 --mode reverse:https://api.openai.com/ -s test_traffic_capture.py

It verifies that the capture addon's JSONL format is correct by logging
a summary of each captured flow.
"""

import json
import os
import time

from mitmproxy import ctx, http

OUTPUT = os.path.join(os.getcwd(), "tmp/codex-traffic/traffic.jsonl")


def response(flow: http.HTTPFlow) -> None:
    ctx.log.info(
        f"CAPTURED: {flow.request.method} {flow.request.pretty_url}"
        f" -> {flow.response.status_code}"
    )
    entry = {
        "timestamp": time.time(),
        "request": {
            "method": flow.request.method,
            "url": flow.request.pretty_url,
            "headers": dict(flow.request.headers),
            "body": (
                flow.request.content.decode("utf-8", errors="replace")
                if flow.request.content
                else None
            ),
        },
        "response": {
            "status_code": flow.response.status_code if flow.response else None,
            "headers": dict(flow.response.headers) if flow.response else None,
            "body": (
                flow.response.content.decode("utf-8", errors="replace")
                if flow.response and flow.response.content
                else None
            ),
        },
    }
    with open(OUTPUT, "a") as f:
        f.write(json.dumps(entry) + "\n")
