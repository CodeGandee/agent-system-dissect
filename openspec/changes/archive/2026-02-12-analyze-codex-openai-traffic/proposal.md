## Why

We need to understand the communication patterns between the `codex` tool and OpenAI's endpoints to effectively dissect its behavior. By capturing and analyzing the traffic, we can gain insights into the protocol, payload structures, and interaction sequences, which is essential for learning from this agent framework.

## Prerequisites

- **codex**: Already installed on the host (codex-cli v0.98.0). This is a **Rust binary** — it uses `reqwest` with `rustls-tls` (bundled CAs), making standard MITM proxy interception impossible without workarounds. See `context/issues/known/issue-codex-bundled-ca-blocks-mitm.md`.
- **mitmproxy**: Already installed via `uv tool` (v12.2.1), providing `mitmdump`, `mitmproxy`, and `mitmweb`.
- **Source reference**: The codex source code in `extern/tracked/codex/` is for reading and reference only — we do not build or modify it.

## What Changes

- Run `mitmproxy` in **reverse proxy mode** to accept plain HTTP from codex and forward HTTPS to OpenAI endpoints — bypassing the bundled CA issue entirely.
- Create a `mitmproxy` addon script to capture and log traffic in structured format.
- Store captured traffic in a structured format for analysis.
- Create a Python analysis script to extract meaningful patterns from the captured traffic.
- Document the findings regarding communication protocols and patterns.

## Capabilities

### New Capabilities
- `traffic-capture`: Functionality to intercept and record network requests and responses between `codex` and remote endpoints, using reverse proxy mode to bypass the Rust binary's bundled CA trust store. Captures complete request/response bodies (no truncation) in chronological order.
- `traffic-analysis`: Tools and methodology to parse, inspect, and summarize the recorded traffic data. Produces a Markdown report with aggregate statistics (endpoints, payload key paths with data types) and a full conversation log showing every request/response pair with redacted headers, structured bodies, and parsed SSE events in collapsible sections.

### Modified Capabilities
- None

## Impact

- **New Scripts**: A mitmproxy addon, runner script, and analysis script — all co-located in `tmp/codex-traffic/scripts/` (git-ignored, disposable).
- **Environment**: Requires `OPENAI_BASE_URL` env var and `chatgpt_base_url` in `~/.codex/config.toml` to point codex at local reverse proxy endpoints (plain HTTP). No CA trust manipulation needed.
- **Documentation**: New documentation will be generated based on the analysis findings.
