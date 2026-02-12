"""
Codex target — capture and analysis profiles for traffic inspection.

Defines ``capture_profile`` and ``analysis_profile`` module-level
instances used by the generic traffic tools when invoked with
``--target codex``.  Uses the OpenAI Responses API body renderers.
"""

from agent_system_dissect.probe.renderers.openai_responses import (
    format_request_body,
    format_response_body,
)
from agent_system_dissect.probe.tools.traffic.types import (
    AnalysisProfile,
    CaptureProfile,
    ProxyConfig,
)

capture_profile = CaptureProfile(
    name="codex",
    proxies=[
        ProxyConfig(
            listen_port=8080,
            upstream_url="https://api.openai.com/",
            purpose="Model API (API key mode)",
        ),
        ProxyConfig(
            listen_port=8081,
            upstream_url="https://chatgpt.com/",
            purpose="Backend channels",
        ),
    ],
    upstream_proxy="http://127.0.0.1:7890",
    env_overrides={
        "OPENAI_BASE_URL": "http://127.0.0.1:8080/v1",
    },
    manual_steps=[
        'Add to ~/.codex/config.toml: chatgpt_base_url = "http://127.0.0.1:8081/backend-api/"',
    ],
    output_dir="tmp/codex-traffic",
)

analysis_profile = AnalysisProfile(
    name="codex",
    report_title="Codex Traffic Analysis Report",
    request_body_renderer=format_request_body,
    response_body_renderer=format_response_body,
    redacted_headers={"authorization", "cookie", "set-cookie", "openai-organization"},
)
