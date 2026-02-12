## 1. Setup & Verification

- [x] 1.1 Verify `mitmproxy` is available via `uv tool run --from mitmproxy mitmdump --version`
- [x] 1.2 Verify `codex` is available via `codex --version`
- [x] 1.3 Generate mitmproxy CA cert (run mitmdump once) and confirm `~/.mitmproxy/mitmproxy-ca-cert.pem` exists
- [x] 1.4 Create `tmp/codex-traffic/scripts/` directory

## 2. Traffic Capture (mitmproxy addon)

- [x] 2.1 Create `tmp/codex-traffic/scripts/capture_traffic.py` (mitmproxy addon loaded via `-s`)
- [x] 2.2 Implement request/response interception logic (log all proxied traffic — no domain filter needed since reverse proxy only sees codex traffic)
- [x] 2.3 Implement logging to `tmp/codex-traffic/traffic.jsonl` (streaming append, one JSON object per line)
- [x] 2.4 Verify capture works with a simple `curl` test through the reverse proxy

## 3. Runner Script

- [x] 3.1 Create `tmp/codex-traffic/scripts/run_capture.sh`
- [x] 3.2 Launch two `mitmdump` reverse proxy instances:
  - `:8080` → `https://api.openai.com/` (model API, API key mode)
  - `:8081` → `https://chatgpt.com/` (backend channels)
  - Both with `--set upstream_proxy=http://127.0.0.1:7890/` for internet access
  - Both with `-s capture_traffic.py` addon
  - Do NOT use `--set keep_host_header=true` (reqwest sends `Host: 127.0.0.1`, mitmproxy default rewrites to upstream)
- [x] 3.3 Set `OPENAI_BASE_URL=http://127.0.0.1:8080/v1` for codex
- [x] 3.4 Set `chatgpt_base_url = "http://127.0.0.1:8081/backend-api/"` in codex config (or document manual step)
- [x] 3.5 End-to-end test: run codex through the reverse proxies and confirm traffic is captured

## 4. Traffic Analysis Script

- [x] 4.1 Create `tmp/codex-traffic/scripts/analyze_traffic.py`
- [x] 4.2 Implement JSONLines parsing
- [x] 4.3 Implement statistics aggregation (endpoints, counts)
- [x] 4.4 Implement payload structure extraction (keys, types)
- [x] 4.5 Implement Markdown report generation
- [x] 4.6 Verify analysis script on captured `tmp/codex-traffic/traffic.jsonl` data

## 5. Documentation

- [x] 5.1 Document usage instructions (how to run capture, how to run analysis)
- [x] 5.2 Document the traffic patterns and findings after a real capture session

## 6. Spec Compliance Fixes

Gaps found by auditing implementation against updated specs.

- [x] 6.1 Fix: payload structure tables missing data types
  - **Spec:** `traffic-analysis/spec.md` → "Extract Payload Structure" requires identifying common keys **and data types**
  - **Gap:** `analyze_traffic.py` reports key paths and occurrence counts but not data types. The `type_name()` helper exists (line 56-71) but is never called.
  - **Fix:** Add a "Type" column to the Request/Response Payload Structure tables showing the observed data type for each key.

- [x] 6.2 Fix: analysis report truncates "full" conversation bodies
  - **Spec:** `traffic-analysis/spec.md` → "Include Full Conversation Log" requires **full** request body and **full** response body, with `<details>` sections for readability.
  - **Gap:** `format_request_body()` and `format_sse_response()` truncate content at various limits: string bodies `[:5000]`, system instructions `[:10000]`, message text `[:10000]`, tool descriptions `[:200]`, content deltas `[:200]`, output item text `[:500]`, other fields `[:3000]`.
  - **Fix:** Remove all `[:N]` truncation limits. The `<details>` collapsible sections already manage readability — truncation is not needed.

- [x] 6.3 Fix: two-proxy file write race on traffic.jsonl
  - **Spec:** `traffic-capture/spec.md` → "Maintain Chronological Order" requires entries ordered by response time.
  - **Gap:** In API key mode, two separate `mitmdump` processes load the addon and append to the same `traffic.jsonl`. Concurrent writes of large entries (28KB+) can exceed POSIX atomic write limits, risking interleaved/corrupt lines and unordered entries.
  - **Risk:** Low in practice — the two channels rarely respond simultaneously. ChatGPT auth mode uses a single proxy, avoiding the issue entirely.
  - **Fix options:** (a) Use `fcntl.flock()` for file-level locking in the addon, (b) write to separate files per proxy and merge by timestamp, or (c) document as a known limitation for API key mode.

## 7. Report Body Rendering (Code Block Requirement)

Spec updated: all request/response bodies must be in fenced code blocks.

- [x] 7.1 Simplify `format_request_body()`: render dict bodies as a single ```` ```json ```` block inside `<details>`, remove semantic decomposition (model config, instructions, messages, tools sections)
- [x] 7.2 Simplify `format_response_body()`: render SSE string bodies as raw text in a ```` ``` ```` block inside `<details>`, remove `format_sse_response()` and `parse_sse_events()`
- [x] 7.3 Verify: run analysis script and confirm all bodies in the report are inside fenced code blocks
