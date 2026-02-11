## Why

We need to understand the communication patterns between the `codex` tool and OpenAI's endpoints to effectively dissect its behavior. By capturing and analyzing the traffic, we can gain insights into the protocol, payload structures, and interaction sequences, which is essential for learning from this agent framework.

## Prerequisites

- **codex**: Already installed on the host via bun (`~/.bun/bin/codex`, codex-cli v0.98.0). This is a Node.js tool — we treat it as a black box.
- **mitmproxy**: Already installed via `uv tool` (v12.2.1), providing `mitmdump`, `mitmproxy`, and `mitmweb`.
- **Source reference**: The codex source code in `extern/tracked/codex/` is for reading and reference only — we do not build or modify it.

## What Changes

- Create a `mitmproxy` addon script to capture HTTP/HTTPS traffic between `codex` and OpenAI endpoints.
- Store captured traffic in a structured format for analysis.
- Create a Python analysis script to extract meaningful patterns from the captured traffic.
- Document the findings regarding communication protocols and patterns.

## Capabilities

### New Capabilities
- `traffic-capture`: Functionality to intercept and record network requests and responses between `codex` and remote endpoints.
- `traffic-analysis`: Tools and methodology to parse, inspect, and summarize the recorded traffic data.

### Modified Capabilities
- None

## Impact

- **New Scripts**: A mitmproxy addon, runner script, and analysis script — all co-located in `tmp/codex-traffic/scripts/` (git-ignored, disposable).
- **Environment**: Requires proxy env vars (`HTTP_PROXY`, `HTTPS_PROXY`) and CA trust (`NODE_EXTRA_CA_CERTS`) to be set when running codex through the proxy.
- **Documentation**: New documentation will be generated based on the analysis findings.
