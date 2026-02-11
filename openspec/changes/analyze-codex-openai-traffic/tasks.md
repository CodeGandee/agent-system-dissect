## 1. Setup & Dependencies

- [ ] 1.1 Add `mitmproxy` to project dependencies (or verify availability)
- [ ] 1.2 Create `src/agent_system_dissect/traffic` directory for scripts

## 2. Traffic Capture (mitmproxy addon)

- [ ] 2.1 Create `src/agent_system_dissect/traffic/capture_traffic.py`
- [ ] 2.2 Implement request/response interception logic to filter for OpenAI domains
- [ ] 2.3 Implement logging to `traffic.jsonl` (streaming write)
- [ ] 2.4 Verify capture works with a simple `curl` test

## 3. Traffic Analysis Script

- [ ] 3.1 Create `src/agent_system_dissect/traffic/analyze_traffic.py`
- [ ] 3.2 Implement JSONLines parsing
- [ ] 3.3 Implement statistics aggregation (endpoints, counts)
- [ ] 3.4 Implement payload structure extraction (keys, types)
- [ ] 3.5 Implement Markdown report generation
- [ ] 3.6 Verify analysis script on sample `traffic.jsonl` data

## 4. Integration & Documentation

- [ ] 4.1 Create `run_capture.sh` helper script to launch mitmdump with correct env vars
- [ ] 4.2 Document usage instructions (how to set CA bundle, how to run capture/analysis)
- [ ] 4.3 End-to-end test with `codex` (if feasible) or simulated traffic
