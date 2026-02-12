## Context

We want to understand the behavior of the `codex` agent tool by analyzing its network traffic with OpenAI.

**Environment:**
- `codex` (codex-cli v0.98.0) is a **Rust binary** using `reqwest` with `rustls-tls` (bundled Mozilla CAs). Standard MITM proxy interception fails because the binary ignores system CA stores and env vars like `SSL_CERT_FILE`. See `context/issues/known/issue-codex-bundled-ca-blocks-mitm.md`.
- `mitmproxy` (v12.2.1) is already available via `uv tool`, providing `mitmdump` for headless capture.
- The codex source code in `extern/tracked/codex/` is for reading and reference only.
- An existing HTTP proxy runs at `127.0.0.1:7890` (used for general internet access). mitmproxy must chain through it as an upstream proxy.

## Goals / Non-Goals

**Goals:**
- Reliably intercept traffic from `codex` using `mitmproxy` via `uv tool`.
- Store traffic in a machine-readable format (JSONLines).
- Provide a script to summarize traffic patterns (endpoints, frequency, payload structure).
- Minimize setup complexity — no recompilation, no source changes to codex.

**Non-Goals:**
- Building a real-time traffic dashboard.
- Modifying or rebuilding the `codex` binary (black-box observation only).
- Capturing hardcoded low-value channels (OAuth login, OTEL telemetry).

## Decisions

### 1. Traffic Capture: Reverse Proxy Mode (No TLS Between Codex and Proxy)

The standard forward proxy approach fails because codex's Rust `reqwest` client uses `rustls-tls` with bundled WebPKI root CAs — it ignores system cert stores, `SSL_CERT_FILE`, and `NODE_EXTRA_CA_CERTS`. TLS handshake fails with `tlsv1 alert unknown ca`.

**Solution:** Use mitmproxy in **reverse proxy mode**. Codex connects to local HTTP endpoints (no TLS), and mitmproxy forwards upstream over HTTPS. No CA trust problem because there's no TLS on the codex → proxy leg.

Codex accepts `http://` base URLs without validation — this is how OSS providers (ollama, lmstudio) work, defaulting to `http://localhost:{port}/v1`.

```
REVERSE PROXY ARCHITECTURE
════════════════════════════════════════════════════════════════════

  ┌─────────┐         ┌──────────────────┐         ┌──────────────┐
  │  codex  │──HTTP──▶│  127.0.0.1:8080  │──HTTPS─▶│ api.openai   │
  │         │         │  mitmdump        │         │   .com       │
  │         │         │  (reverse mode)  │         │              │
  │         │         └──────────────────┘         └──────────────┘
  │         │                  │
  │         │                  │ addon writes
  │         │                  ▼
  │         │         traffic.jsonl
  │         │
  │         │         ┌──────────────────┐         ┌──────────────┐
  │         │──HTTP──▶│  127.0.0.1:8081  │──HTTPS─▶│  chatgpt     │
  │         │         │  mitmdump        │         │   .com       │
  │         │         │  (reverse mode)  │         │              │
  └─────────┘         └──────────────────┘         └──────────────┘
```

**Two proxy instances** are needed because codex has two independent URL roots:
- **Model API** (`OPENAI_BASE_URL`): targets `api.openai.com` (API key mode) or `chatgpt.com` (ChatGPT auth mode)
- **Backend** (`chatgpt_base_url`): targets `chatgpt.com` — controls backend-client, analytics, MCP, remote skills, and direct ChatGPT channels

When using ChatGPT auth mode, both target `chatgpt.com` and can be simplified to a single proxy instance:

```bash
# Single proxy for ChatGPT auth mode
mitmdump --mode reverse:https://chatgpt.com/ -p 8081 \
  --set upstream_proxy=http://127.0.0.1:7890/ -s capture_traffic.py

# Model API uses /backend-api/codex (not /v1) in ChatGPT auth mode
export OPENAI_BASE_URL="http://127.0.0.1:8081/backend-api/codex"
```

**Note:** In ChatGPT auth mode, the model API path is `/backend-api/codex/responses` (not `/v1/responses` as in API key mode).

*   **Rationale**: Zero source changes, captures all high-value traffic. Already available on the host.
*   **Alternatives considered**:
    *   Forward proxy with recompilation (Approach B in issue doc): Captures all traffic including auth/OTEL, but requires 4 `Cargo.toml` edits + rebuild.
    *   `Wireshark`/`tcpdump`: Cannot decrypt TLS without `SSLKEYLOGFILE` (not enabled in this build).

### 2. Codex Configuration for Reverse Proxy

Codex traffic is redirected to local proxies via two mechanisms:

**Environment variable** (model API):
```bash
export OPENAI_BASE_URL="http://127.0.0.1:8080/v1"
```

**Config file** (`~/.codex/config.toml`) (backend channels):
```toml
chatgpt_base_url = "http://127.0.0.1:8081/backend-api/"
```

**Why this works (verified against source):**
- `OPENAI_BASE_URL` is read in `model_provider_info.rs` via `std::env::var()` with no scheme validation.
- `chatgpt_base_url` is read from TOML config with no scheme validation.
- `PathStyle::from_base_url()` in `backend-client/src/client.rs` checks `contains("/backend-api")` (hostname-agnostic), so `http://127.0.0.1:8081/backend-api` correctly triggers `ChatGptApi` path style (`/wham/...` paths).
- Remote skills strip `/backend-api` suffix before building `/public-api/hazelnuts/`, producing correct upstream paths.

**Host header handling:** Codex does NOT set an explicit `Host` header — reqwest auto-derives it from the URL (`Host: 127.0.0.1:PORT`). mitmproxy's default reverse proxy behavior rewrites the Host header to match the upstream, which is correct. Do NOT use `--set keep_host_header=true`.

### 3. Traffic Channel Coverage

| Channel | Source File | Captured? | Via |
|---------|-----------|-----------|-----|
| Model API (`/v1/responses`) | `codex-api/src/provider.rs` | ✅ | `OPENAI_BASE_URL` → `:8080` |
| Backend-client (`/wham/*`) | `backend-client/src/client.rs` | ✅ | `chatgpt_base_url` → `:8081` |
| Analytics | `core/src/analytics_client.rs` | ✅ | `chatgpt_base_url` → `:8081` |
| MCP Apps | `core/src/mcp/mod.rs` | ✅ | `chatgpt_base_url` → `:8081` |
| Remote Skills | `core/src/skills/remote.rs` | ✅ | `chatgpt_base_url` → `:8081` |
| Direct ChatGPT | `chatgpt/src/chatgpt_client.rs` | ✅ | `chatgpt_base_url` → `:8081` |
| OAuth Login | hardcoded `auth.openai.com` | ❌ | One-time, low-value |
| OTEL Telemetry | hardcoded `ab.chatgpt.com` | ❌ | No analytical value |

### 4. Upstream Proxy Chaining

The host uses an existing proxy at `:7890` for internet access. mitmproxy reverse mode supports upstream proxying — add `--set upstream_proxy=http://127.0.0.1:7890/` to chain through it.

### 5. Storage Format: JSONLines (`.jsonl`)

Traffic is logged to a JSONLines file where each line is a JSON object representing a request/response pair.
*   **Full body preservation**: Each entry contains the complete request body (JSON payloads including model config, instructions, input messages, tool definitions) and complete response body (including full SSE event streams). No content is truncated or summarized at capture time.
*   **Chronological ordering**: Entries are appended in the order responses arrive. When using two proxy instances (API key mode), concurrent writes to the same file are protected by file-level locking (`fcntl.flock()`) to prevent interleaved writes and maintain ordering.
*   **Output directory**: `tmp/codex-traffic/` (git-ignored). All capture outputs and analysis reports live here.
*   **Rationale**: Streaming-friendly (append-only), easy to parse line-by-line in Python, human-readable.
*   **Alternatives considered**:
    *   `HAR` (HTTP Archive): Standard but verbose and monolithic (hard to stream write).
    *   `SQLite`: Overkill for this scale.

### 6. Analysis Approach: Python Script

A dedicated Python script ingests the `.jsonl` file and produces a Markdown report containing:
*   **Aggregate statistics**: Endpoint summary (paths, methods, counts), HTTP method breakdown, response status codes, and payload structure tables showing key paths with observed data types and occurrence counts.
*   **Full conversation log**: Every captured request/response pair rendered with redacted headers (in code blocks), summarized request body (model config, instructions preview, message table, tool list), and summarized response body (SSE event breakdown, assembled output text, reasoning summary, tool calls, usage statistics). Collapsible `<details>` sections manage readability for long content.
*   **Rationale**: Leverages the project's Python ecosystem (pixi, scipy, etc.); flexible for custom analysis logic.

### 6a. Body Rendering in Conversation Log

Request and response bodies in the conversation log are rendered as **summarized key parts with explanations**, not raw dumps. This keeps the report concise while preserving all important information.

**Request bodies** (parsed `dict`) are decomposed into semantic sections:
*   **Model & config**: Inline display of model name and key config fields (stream, tool_choice, parallel_tool_calls, etc.).
*   **System instructions**: Character count shown inline, full text in a collapsible `<details>` section with a code block.
*   **Input messages**: Table with index, role, type, and content preview. Each message's full content available in a collapsible `<details>` section.
*   **Tools**: Listed by name and type (e.g., `exec_command` (function), `apply_patch` (custom)). Description text omitted for brevity.

**SSE response bodies** (text/event-stream strings) are parsed and summarized:
*   **Stream overview**: Total byte size and event count shown inline.
*   **Event type breakdown**: Table mapping each event type to its count.
*   **Output text**: Assembled from `response.output_text.delta` events, shown in a collapsible `<details>` section with a code block.
*   **Reasoning summary**: Assembled from `response.reasoning_summary_text.delta` events, shown in a collapsible `<details>` section with a code block.
*   **Tool calls**: Extracted from `response.function_call_arguments.done` events, showing function name and arguments.
*   **Usage statistics**: Extracted from the `response.completed` event — input tokens, output tokens, total tokens (with cached/reasoning breakdowns if available).

**Non-SSE dict bodies** (rare): Rendered as `json.dumps(indent=2)` in a code block inside `<details>` for simplicity.

*   **Rationale**: Summarized rendering dramatically reduces report size (from ~370KB to ~30-50KB for 3 requests) while making the content more scannable and informative. Key parts (model, message flow, output text, usage) are immediately visible without expanding anything. Full content is still accessible via collapsible sections.

### 7. File Layout

Everything lives under `tmp/codex-traffic/` (git-ignored). Scripts, captured data, and reports are co-located in the output directory.

```
tmp/codex-traffic/
├── scripts/
│   ├── capture_traffic.py     # mitmproxy addon (loaded by mitmdump via -s)
│   ├── run_capture.sh         # wrapper to launch mitmdump + configure codex
│   └── analyze_traffic.py     # analysis tool, reads traffic.jsonl
├── traffic.jsonl              # raw captured request/response pairs
└── analysis_report.md         # generated summary from analyze_traffic.py
```

## Risks / Trade-offs

-   **Risk**: Streaming responses (SSE) may need special handling in the mitmproxy addon.
    *   **Mitigation**: OpenAI uses Server-Sent Events for streaming. The mitmproxy addon should capture the full response body after the stream completes, not attempt to log partial chunks.
-   **Risk**: Sandbox mode (`CODEX_SANDBOX_ENV_VAR=seatbelt`) calls `no_proxy()` on reqwest, disabling HTTP_PROXY/HTTPS_PROXY env vars.
    *   **Mitigation**: Does not affect us — we redirect via base URL, not via proxy env vars. The reverse proxy approach is transparent to reqwest's proxy settings.
-   **Risk**: Future codex versions could add URL scheme validation (reject `http://`).
    *   **Mitigation**: Unlikely — `http://` is the standard for local OSS model providers. If it happens, fall back to Approach B (recompile with `rustls-tls-native-roots`).

## Implementation Plan

1.  **Capture Addon**: Write `tmp/codex-traffic/scripts/capture_traffic.py` as a mitmproxy addon — log all proxied request/response pairs to `tmp/codex-traffic/traffic.jsonl`.
2.  **Runner Script**: Write `tmp/codex-traffic/scripts/run_capture.sh` to launch two `mitmdump` reverse proxy instances (`:8080` for model API, `:8081` for backend) with the capture addon, set `OPENAI_BASE_URL`, and invoke codex.
3.  **Analysis Script**: Write `tmp/codex-traffic/scripts/analyze_traffic.py` to read `tmp/codex-traffic/traffic.jsonl` and output `tmp/codex-traffic/analysis_report.md`.
