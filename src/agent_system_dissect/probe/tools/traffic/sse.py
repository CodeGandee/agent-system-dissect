"""
SSE (Server-Sent Events) stream parser.

Provides a reusable parser that splits a raw SSE text stream into
discrete event objects with parsed JSON data payloads.

Functions
---------
parse_sse_events : Parse an SSE stream string into event dicts.
"""

from __future__ import annotations

import json


def parse_sse_events(raw: str) -> list[dict]:
    """
    Parse an SSE stream string into a list of event dicts.

    Each SSE block is delimited by ``\\n\\n``.  Within a block, lines
    starting with ``event:`` set the event type and lines starting with
    ``data:`` contribute to the data payload.  If the data is valid JSON
    it is returned as a parsed object; otherwise it is returned as a raw
    string.

    Parameters
    ----------
    raw : str
        The raw SSE stream text.

    Returns
    -------
    list of dict
        Each dict has keys ``"event"`` (str) and ``"data"``
        (parsed JSON object, raw str, or None).
    """
    events: list[dict] = []
    for block in raw.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        event_type = ""
        data_lines: list[str] = []
        for line in block.split("\n"):
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                data_lines.append(line[6:])
            elif line.startswith("data:"):
                data_lines.append(line[5:])
        if event_type or data_lines:
            data_str = "\n".join(data_lines)
            data = None
            if data_str:
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    data = data_str
            events.append({"event": event_type, "data": data})
    return events
