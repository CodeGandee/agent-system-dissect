## Context

We want to understand the behavior of the `codex` agent tool by analyzing its network traffic with OpenAI.

**Environment:**
- `codex` (codex-cli v0.98.0) is installed on the host via bun. It is a Node.js tool — we treat it as a black box.
- `mitmproxy` (v12.2.1) is already available via `uv tool`, providing `mitmdump` for headless capture.
- The codex source code in `extern/tracked/codex/` is for reading and reference only.
- An existing HTTP proxy runs at `127.0.0.1:7890` (used for general internet access). mitmproxy must chain through it as an upstream proxy.

## Goals / Non-Goals

**Goals:**
- Reliably intercept HTTPS traffic from `codex` using `mitmproxy` via `uv tool`.
- Store traffic in a machine-readable format (JSONLines).
- Provide a script to summarize traffic patterns (endpoints, frequency, payload structure).
- Minimize setup complexity — leverage tools already installed on the host.

**Non-Goals:**
- Building a real-time traffic dashboard.
- Modifying or rebuilding the `codex` binary (black-box observation only).
- Decrypting traffic without a CA certificate (standard MITM approach requires CA installation).

## Decisions

### 1. Traffic Capture Tool: `mitmproxy` via `uv tool`
We use `mitmdump` (from `mitmproxy`, already installed as a `uv tool`) in **upstream proxy mode** to handle HTTPS interception.
*   **Invocation**: `uv tool run mitmdump --mode upstream:http://127.0.0.1:7890/ -s tmp/codex-traffic/scripts/capture_traffic.py`
*   **Upstream chaining**: The host already uses a proxy at `:7890` for internet access. mitmdump runs as an intermediate proxy on `:8080` and forwards all traffic through the existing proxy. This is transparent to codex.
*   **Rationale**: Already available on the host. Industry standard, supports Python addon scripts for custom filtering/logging, handles certificate generation.
*   **Alternatives considered**:
    *   `Wireshark`/`tcpdump`: Captures packets but decrypting TLS is difficult without SSLKEYLOGFILE.
    *   Custom proxy: Hard to implement correct HTTPS MITM from scratch.

```
PROXY CHAIN
════════════════════════════════════════════════════════════

  ┌─────────┐         ┌──────────────────┐         ┌──────────┐         ┌──────────┐
  │  codex  │────────▶│  127.0.0.1:8080  │────────▶│  :7890   │────────▶│  OpenAI  │
  │ (node)  │  proxy  │  mitmdump        │ upstream│  (proxy) │         │   API    │
  └─────────┘         └──────────────────┘         └──────────┘         └──────────┘
                              │
                              │ addon writes
                              ▼
                    tmp/codex-traffic/traffic.jsonl
```

### 2. Proxy Configuration for Node.js codex
Since `codex` is a Node.js tool, we configure the proxy and CA trust via environment variables:
*   `HTTP_PROXY` / `HTTPS_PROXY`: Point to mitmdump (e.g., `http://127.0.0.1:8080`), **not** the existing proxy at `:7890`. mitmdump handles upstream forwarding to `:7890` internally via `--mode upstream:...`.
*   `NODE_EXTRA_CA_CERTS`: Point to `~/.mitmproxy/mitmproxy-ca-cert.pem` so Node.js trusts the mitmproxy CA.
*   **Note**: `REQUESTS_CA_BUNDLE` is Python-specific and does not apply here.

### 3. Storage Format: JSONLines (`.jsonl`)
Traffic is logged to a JSONLines file where each line is a JSON object representing a request/response pair.
*   **Output directory**: `tmp/codex-traffic/` (git-ignored). All capture outputs and analysis reports live here.
*   **Rationale**: Streaming-friendly (append-only), easy to parse line-by-line in Python, human-readable.
*   **Alternatives considered**:
    *   `HAR` (HTTP Archive): Standard but verbose and monolithic (hard to stream write).
    *   `SQLite`: Overkill for this scale.

### 4. Analysis Approach: Python Script
A dedicated Python script ingests the `.jsonl` file and produces a Markdown report.
*   **Rationale**: Leverages the project's Python ecosystem (pixi, scipy, etc.); flexible for custom analysis logic.

### 5. File Layout

Everything lives under `tmp/codex-traffic/` (git-ignored). Scripts, captured data, and reports are co-located in the output directory.

```
tmp/codex-traffic/
├── scripts/
│   ├── capture_traffic.py     # mitmproxy addon (loaded by mitmdump via -s)
│   ├── run_capture.sh         # wrapper to launch mitmdump with env vars
│   └── analyze_traffic.py     # analysis tool, reads traffic.jsonl
├── traffic.jsonl              # raw captured request/response pairs
└── analysis_report.md         # generated summary from analyze_traffic.py
```

## Risks / Trade-offs

-   **Risk**: `codex` (or its OpenAI SDK) might enforce strict SSL pinning or ignore proxy env vars.
    *   **Mitigation**: Node.js respects `HTTP_PROXY`/`HTTPS_PROXY` via most HTTP libraries (including the OpenAI Node SDK). If pinning is present, we can fall back to `SSLKEYLOGFILE` + Wireshark as an alternative capture method. We will not modify codex.
-   **Risk**: mitmproxy CA certificate not trusted by codex's Node.js runtime.
    *   **Mitigation**: Set `NODE_EXTRA_CA_CERTS=~/.mitmproxy/mitmproxy-ca-cert.pem` before launching codex. This is the standard Node.js mechanism for adding custom CA certificates.
-   **Risk**: Streaming responses (SSE) may need special handling in the mitmproxy addon.
    *   **Mitigation**: OpenAI uses Server-Sent Events for streaming. The mitmproxy addon should capture the full response body after the stream completes, not attempt to log partial chunks.

## Implementation Plan

1.  **Capture Addon**: Write `tmp/codex-traffic/scripts/capture_traffic.py` as a mitmproxy addon — filter for OpenAI domains, log request/response pairs to `tmp/codex-traffic/traffic.jsonl`.
2.  **Runner Script**: Write `tmp/codex-traffic/scripts/run_capture.sh` to launch `uv tool run mitmdump --mode upstream:http://127.0.0.1:7890/ -s tmp/codex-traffic/scripts/capture_traffic.py` and set `HTTP_PROXY`, `HTTPS_PROXY` (to `:8080`), and `NODE_EXTRA_CA_CERTS` before invoking codex.
3.  **Analysis Script**: Write `tmp/codex-traffic/scripts/analyze_traffic.py` to read `tmp/codex-traffic/traffic.jsonl` and output `tmp/codex-traffic/analysis_report.md`.
