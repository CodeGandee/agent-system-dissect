"""
Profile types for traffic capture and analysis tools.

Defines the data structures used to configure generic traffic capture
and analysis tools for any target agent system.  Target-specific modules
provide instances of these profiles; the tools consume them.

Classes
-------
ProxyConfig : Configuration for a single mitmproxy reverse proxy instance.
CaptureProfile : Full capture session configuration for a target.
AnalysisProfile : Full analysis/report configuration for a target.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProxyConfig:
    """
    Configuration for a single mitmproxy reverse proxy instance.

    Attributes
    ----------
    listen_port : int
        Local port the reverse proxy listens on.
    upstream_url : str
        Upstream URL to forward traffic to (e.g. ``https://api.openai.com/``).
    purpose : str
        Human-readable description (e.g. ``"Model API"``).
    """

    listen_port: int
    upstream_url: str
    purpose: str


@dataclass
class CaptureProfile:
    """
    Describes how to set up traffic capture for a target agent system.

    Attributes
    ----------
    name : str
        Short identifier for the target (e.g. ``"codex"``).
    proxies : list of ProxyConfig
        Reverse proxy instances to launch.
    upstream_proxy : str or None
        Optional upstream proxy URL for internet access
        (e.g. ``"http://127.0.0.1:7890"``).
    env_overrides : dict of str to str
        Environment variables to set before running the target command.
    manual_steps : list of str
        Human-readable manual configuration steps shown to the user.
    output_dir : str
        Directory where ``traffic.jsonl`` is written.
    """

    name: str
    proxies: list[ProxyConfig]
    upstream_proxy: str | None = None
    env_overrides: dict[str, str] = field(default_factory=dict)
    manual_steps: list[str] = field(default_factory=list)
    output_dir: str = "tmp/traffic"


@dataclass
class AnalysisProfile:
    """
    Describes how to analyze and render traffic for a target agent system.

    Attributes
    ----------
    name : str
        Short identifier for the target (e.g. ``"codex"``).
    report_title : str
        Title for the generated Markdown report.
    request_body_renderer : callable
        ``(body: Any) -> str`` — renders a request body as Markdown.
    response_body_renderer : callable
        ``(body: Any, status_code: int) -> str`` — renders a response body
        as Markdown.
    redacted_headers : set of str
        Header names whose values are redacted in the report.
    """

    name: str
    report_title: str
    request_body_renderer: Callable[[Any], str]
    response_body_renderer: Callable[[Any, int], str]
    redacted_headers: set[str] = field(
        default_factory=lambda: {"authorization", "cookie", "set-cookie"}
    )
