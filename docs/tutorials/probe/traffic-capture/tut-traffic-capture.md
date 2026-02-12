---
created_at: "2026-02-12T08:23:00Z"
tutorial_name: traffic-capture
topic: "Probe traffic capture and analysis for AI agent systems"
base_commit: 3ae9ed8fecd1dca7cb7b606291a96e0beea7772a
runtime:
  os: Linux 6.8.0-90-generic x86_64
  python: "3.12.3 (via pixi)"
  key_packages:
    - mitmproxy (external tool, installed via `uv tool install mitmproxy`)
    - agent-system-dissect (this repo)
---

# How do I capture and analyze HTTP traffic from an AI coding agent (e.g., Codex)?

The `probe.tools.traffic` module provides a generic, target-agnostic framework for intercepting API traffic from AI agent systems using mitmproxy reverse proxies. It captures every HTTP request/response as JSONL, then generates structured Markdown analysis reports with endpoint statistics, payload structure, and a fully rendered conversation log.

This tutorial walks through the complete workflow: **capture → analyze → read the report**.

## Prerequisites

- [ ] Python 3.11+ (the repo uses 3.13, but 3.11+ works)
- [ ] [Pixi](https://pixi.sh) package manager installed
- [ ] Repo cloned and dependencies installed (`pixi install`)
- [ ] mitmproxy installed: `uv tool install mitmproxy` (provides the `mitmdump` binary)
- [ ] For live capture: an OpenAI API key (`OPENAI_API_KEY`) and the target agent installed (e.g., [Codex CLI](https://github.com/openai/codex))
- [ ] For sample-only: no API key or external tools needed

## Implementation Idea

The system uses **mitmproxy reverse proxies** to sit between the agent and its upstream API:

```
Agent (Codex)  →  mitmproxy (:8080)  →  api.openai.com
                     ↓
               traffic.jsonl (JSONL log)
                     ↓
              analyze.py  →  analysis_report.md
```

Architecture is three-tiered for reuse across different agents and APIs:

| Tier | Path | Purpose | Changes when adding a target? |
|------|------|---------|-------------------------------|
| 1. Generic tools | `probe/tools/traffic/` | Capture runner, analyzer, SSE parser, types | Never |
| 2. API renderers | `probe/renderers/` | Format request/response bodies for a specific API | Only if new API format |
| 3. Target config | `probe/targets/<name>/` | Proxy ports, env vars, renderer selection | Always (one small file) |

## Critical Example Code

### Profile definition (what makes a target)

Each target exports a `capture_profile` and `analysis_profile`. Here's the Codex target as an example:

```python
# src/agent_system_dissect/probe/targets/codex/traffic.py

from agent_system_dissect.probe.renderers.openai_responses import (
    format_request_body, format_response_body,
)
from agent_system_dissect.probe.tools.traffic.types import (
    AnalysisProfile, CaptureProfile, ProxyConfig,
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
    upstream_proxy="http://127.0.0.1:7890",       # optional internet proxy
    env_overrides={
        "OPENAI_BASE_URL": "http://127.0.0.1:8080/v1",  # redirect codex to our proxy
    },
    manual_steps=[
        'Add to ~/.codex/config.toml: chatgpt_base_url = "http://127.0.0.1:8081/backend-api/"',
    ],
    output_dir="tmp/codex-traffic",
)

analysis_profile = AnalysisProfile(
    name="codex",
    report_title="Codex Traffic Analysis Report",
    request_body_renderer=format_request_body,      # OpenAI Responses API renderer
    response_body_renderer=format_response_body,    # handles SSE streams
    redacted_headers={"authorization", "cookie", "set-cookie", "openai-organization"},
)
```

### Capture runner CLI

```bash
# Start proxies only — run codex manually in another terminal
python -m agent_system_dissect.probe.tools.traffic.runner --target codex

# Start proxies AND run a codex command (all-in-one)
python -m agent_system_dissect.probe.tools.traffic.runner \
    --target codex \
    -- codex exec "write a hello world function"

# Override defaults
python -m agent_system_dissect.probe.tools.traffic.runner \
    --target codex \
    --output-dir /tmp/my-capture \
    --upstream-proxy http://corp-proxy:3128 \
    -- codex exec "write a hello world function"
```

### Analyzer CLI

```bash
python -m agent_system_dissect.probe.tools.traffic.analyze \
    --target codex \
    --input tmp/codex-traffic/traffic.jsonl \
    --output tmp/codex-traffic/analysis_report.md
```

## Input and Output

### Input: `traffic.jsonl`

One JSON object per line. Each entry records a complete HTTP request/response pair:

```json
{
  "timestamp": 1707123456.100,
  "request": {
    "method": "POST",
    "url": "https://api.openai.com/v1/responses",
    "headers": { "content-type": "application/json", "authorization": "Bearer sk-..." },
    "body": {
      "model": "o4-mini",
      "stream": true,
      "instructions": "You are a helpful assistant...",
      "input": [
        { "role": "user", "type": "message", "content": "Write a prime checker." }
      ],
      "tools": [{ "type": "function", "name": "shell" }]
    }
  },
  "response": {
    "status_code": 200,
    "headers": { "content-type": "text/event-stream" },
    "body": "event: response.output_text.delta\ndata: {\"delta\": \"Here's...\"}\n\n..."
  }
}
```

Key details:
- **Request bodies**: parsed JSON if valid, raw UTF-8 string otherwise
- **Response bodies**: raw UTF-8 string for SSE streams (`text/event-stream`), parsed JSON otherwise
- **File locking**: multiple mitmdump instances can safely write to the same file concurrently

### Output: `analysis_report.md`

A Markdown report containing:

1. **Header** — source file, generation timestamp, totals (requests, duration, payload bytes)
2. **Endpoints table** — path, HTTP methods, count
3. **HTTP Methods table** — method breakdown
4. **Status Codes table** — response code distribution
5. **Payload Structure** — top 30 request/response keys by occurrence with types
6. **Full Conversation Log** — every request/response pair with:
   - Redacted headers (auth tokens replaced with `[REDACTED]`)
   - Rendered request body (model, system prompt, input messages table, tools)
   - Rendered response body (SSE event breakdown, assembled output text, tool calls, usage stats)

See `outputs/sample_report.md` for a complete example generated from the bundled sample data.

## Running the Tutorial

### Quick start: analyze sample data (no API key needed)

```bash
# From the repo root, activate the environment
pixi shell

# Run analysis on the bundled sample
./docs/tutorials/probe/traffic-capture/scripts/analyze_sample.sh
```

Output is written to `docs/tutorials/probe/traffic-capture/outputs/sample_report.md`.

### Full workflow: capture live Codex traffic

**Option A: Proxies only (two terminals)**

```bash
# Terminal 1: Start proxies
pixi shell
./scripts/probe/codex/run_capture.sh

# The runner will print:
#   :8080 -> https://api.openai.com/  (Model API)
#   :8081 -> https://chatgpt.com/     (Backend channels)
#   Manual setup required:
#     - Add to ~/.codex/config.toml: chatgpt_base_url = "http://127.0.0.1:8081/backend-api/"
#   Environment overrides for target:
#     export OPENAI_BASE_URL=http://127.0.0.1:8080/v1
#   Press Ctrl+C to stop.

# Terminal 2: Run codex with env override
export OPENAI_BASE_URL=http://127.0.0.1:8080/v1
codex exec "write a hello world function"

# Terminal 1: Press Ctrl-C after codex finishes
# Output: tmp/codex-traffic/traffic.jsonl
```

**Option B: All-in-one (single terminal)**

```bash
pixi shell
./scripts/probe/codex/run_capture.sh -- codex exec "write a hello world function"
# Proxies start → codex runs → proxies stop automatically
# Output: tmp/codex-traffic/traffic.jsonl
```

**Option C: Full capture + analysis pipeline**

```bash
pixi shell
./docs/tutorials/probe/traffic-capture/scripts/run_full_workflow.sh \
    "write a hello world function"
# Output:
#   tmp/codex-traffic/traffic.jsonl
#   tmp/codex-traffic/analysis_report.md
```

### Generate analysis report from any capture

```bash
pixi shell
python -m agent_system_dissect.probe.tools.traffic.analyze \
    --target codex \
    --input tmp/codex-traffic/traffic.jsonl \
    --output tmp/codex-traffic/analysis_report.md
```

## Adding a New Target

To capture traffic from a different agent (e.g., Cursor):

### If it uses the OpenAI API (reuse existing renderers):

Create one file: `src/agent_system_dissect/probe/targets/cursor/traffic.py`

```python
from agent_system_dissect.probe.renderers.openai_responses import (
    format_request_body, format_response_body,
)
from agent_system_dissect.probe.tools.traffic.types import (
    AnalysisProfile, CaptureProfile, ProxyConfig,
)

capture_profile = CaptureProfile(
    name="cursor",
    proxies=[
        ProxyConfig(listen_port=9080, upstream_url="https://api.openai.com/",
                    purpose="Cursor Model API"),
    ],
    env_overrides={"OPENAI_BASE_URL": "http://127.0.0.1:9080/v1"},
    output_dir="tmp/cursor-traffic",
)

analysis_profile = AnalysisProfile(
    name="cursor",
    report_title="Cursor Traffic Analysis Report",
    request_body_renderer=format_request_body,
    response_body_renderer=format_response_body,
)
```

Then: `python -m agent_system_dissect.probe.tools.traffic.runner --target cursor`

### If it uses a different API (e.g., Anthropic):

1. Create a new renderer: `src/agent_system_dissect/probe/renderers/anthropic_messages.py`
2. Create the target: `src/agent_system_dissect/probe/targets/claude_code/traffic.py` using that renderer

No changes to the generic tools (Tier 1) are ever needed.

## Key Source Files

| File | Purpose |
|------|---------|
| `src/agent_system_dissect/probe/tools/traffic/types.py` | `ProxyConfig`, `CaptureProfile`, `AnalysisProfile` dataclasses |
| `src/agent_system_dissect/probe/tools/traffic/capture_addon.py` | mitmproxy addon — intercepts flows, writes JSONL |
| `src/agent_system_dissect/probe/tools/traffic/runner.py` | Generic capture orchestrator (CLI: `--target`, `--output-dir`) |
| `src/agent_system_dissect/probe/tools/traffic/analyze.py` | Generic analyzer + report generator (CLI: `--target`, `--input`) |
| `src/agent_system_dissect/probe/tools/traffic/sse.py` | SSE stream parser |
| `src/agent_system_dissect/probe/renderers/openai_responses.py` | OpenAI Responses API body formatters |
| `src/agent_system_dissect/probe/targets/codex/traffic.py` | Codex target profiles |
| `scripts/probe/codex/run_capture.sh` | Shell convenience wrapper |

## Troubleshooting

### `mitmdump not found`

mitmproxy is an external tool, not a Python project dependency. Install it:

```bash
uv tool install mitmproxy
# or: pipx install mitmproxy
# or: brew install mitmproxy (macOS)
```

Verify: `which mitmdump` should return a path.

### `mitmdump exited early with code 1`

Common causes:
- **Port already in use**: another process is listening on 8080/8081. Check with `lsof -i :8080` and stop the conflicting process.
- **Upstream proxy unreachable**: if `upstream_proxy` is set (default `http://127.0.0.1:7890` for codex), ensure it's running. Override with `--upstream-proxy ""` to disable.

### `ModuleNotFoundError: agent_system_dissect`

The package must be importable. Ensure you activated the pixi environment:

```bash
pixi install
pixi shell
# or prefix commands: pixi run python -m ...
```

### Empty `traffic.jsonl` after capture

- Verify the agent is actually using the proxy URL. For Codex, `OPENAI_BASE_URL` must point to `http://127.0.0.1:8080/v1`.
- Check that manual config steps were followed (e.g., `chatgpt_base_url` in `~/.codex/config.toml`).
- Verify proxies are running: `curl http://127.0.0.1:8080/v1/models` should return a response (possibly an auth error, but not a connection refusal).

### Analysis report looks wrong or incomplete

- Ensure the `--target` flag matches the target that produced the JSONL. Using `--target codex` with traffic from a different API will render bodies incorrectly.
- Check for malformed lines: the analyzer prints `WARNING: skipping malformed line N` to stderr for bad entries.

## Verification

After running the sample analysis (`scripts/analyze_sample.sh`):

1. **File exists**: `outputs/sample_report.md` should be created
2. **Report header**: contains `Total requests: 3`, `Capture duration: 9.7s`
3. **Endpoint table**: shows `/v1/responses` with count 3
4. **Conversation log**: 3 request/response pairs with:
   - Request 1: text output (prime function)
   - Request 2: tool call (`write_file`) with reasoning summary
   - Request 3: tool call (`shell` to run tests)
5. **Redaction**: `authorization` header shows `[REDACTED]`
6. **Usage stats**: each response includes token counts (e.g., `245 input | 89 output | 334 total`)

For live captures, verify similarly but with your actual request counts and content.
