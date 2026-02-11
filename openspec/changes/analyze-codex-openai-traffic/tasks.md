## 1. Setup & Verification

- [ ] 1.1 Verify `mitmproxy` is available via `uv tool run mitmdump --version`
- [ ] 1.2 Verify `codex` is available via `codex --version`
- [ ] 1.3 Generate mitmproxy CA cert (run mitmdump once) and confirm `~/.mitmproxy/mitmproxy-ca-cert.pem` exists
- [ ] 1.4 Create `tmp/codex-traffic/scripts/` directory

## 2. Traffic Capture (mitmproxy addon)

- [ ] 2.1 Create `tmp/codex-traffic/scripts/capture_traffic.py` (mitmproxy addon loaded via `-s`)
- [ ] 2.2 Implement request/response interception logic to filter for OpenAI domains
- [ ] 2.3 Implement logging to `tmp/codex-traffic/traffic.jsonl` (streaming append, one JSON object per line)
- [ ] 2.4 Verify capture works with a simple `curl` test through the proxy

## 3. Runner Script

- [ ] 3.1 Create `tmp/codex-traffic/scripts/run_capture.sh` to launch `uv tool run mitmdump -s tmp/codex-traffic/scripts/capture_traffic.py`
- [ ] 3.2 Set `HTTP_PROXY`, `HTTPS_PROXY`, and `NODE_EXTRA_CA_CERTS` for codex
- [ ] 3.3 End-to-end test: run codex through the proxy and confirm traffic is captured

## 4. Traffic Analysis Script

- [ ] 4.1 Create `tmp/codex-traffic/scripts/analyze_traffic.py`
- [ ] 4.2 Implement JSONLines parsing
- [ ] 4.3 Implement statistics aggregation (endpoints, counts)
- [ ] 4.4 Implement payload structure extraction (keys, types)
- [ ] 4.5 Implement Markdown report generation
- [ ] 4.6 Verify analysis script on captured `tmp/codex-traffic/traffic.jsonl` data

## 5. Documentation

- [ ] 5.1 Document usage instructions (how to run capture, how to run analysis)
- [ ] 5.2 Document the traffic patterns and findings after a real capture session
