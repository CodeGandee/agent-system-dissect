## 1. Package Structure

- [x] 1.1 Create `src/agent_system_dissect/probe/__init__.py`
- [x] 1.2 Create `src/agent_system_dissect/probe/tools/__init__.py`
- [x] 1.3 Create `src/agent_system_dissect/probe/tools/traffic/__init__.py`
- [x] 1.4 Create `src/agent_system_dissect/probe/renderers/__init__.py`
- [x] 1.5 Create `src/agent_system_dissect/probe/targets/__init__.py`
- [x] 1.6 Create `src/agent_system_dissect/probe/targets/codex/__init__.py`

## 2. Profile Types

- [x] 2.1 Create `probe/tools/traffic/types.py` with `ProxyConfig`, `CaptureProfile`, and `AnalysisProfile` dataclasses

## 3. Generic Tools (Tier 1)

- [x] 3.1 Create `probe/tools/traffic/sse.py` — extract `parse_sse_events()` from `tmp/codex-traffic/scripts/analyze_traffic.py`
- [x] 3.2 Create `probe/tools/traffic/capture_addon.py` — migrate from `tmp/codex-traffic/scripts/capture_traffic.py`, add `TRAFFIC_OUTPUT_DIR` env var support
- [x] 3.3 Create `probe/tools/traffic/analyze.py` — extract generic analysis framework (load_entries, extract_keys, type_name, analyze, redact_headers, format_conversations, format_report, main) from `tmp/codex-traffic/scripts/analyze_traffic.py`, replace hardcoded body renderers with AnalysisProfile callables, add `--target` CLI argument
- [x] 3.4 Create `probe/tools/traffic/runner.py` — new generic capture runner that reads CaptureProfile, launches mitmdump instances, applies env overrides, displays manual steps

## 4. OpenAI Renderers (Tier 2)

- [x] 4.1 Create `probe/renderers/openai_responses.py` — extract `format_request_body()`, `format_response_body()`, `_message_content_preview()`, `_message_content_full()` from `tmp/codex-traffic/scripts/analyze_traffic.py`, import `parse_sse_events` from `probe.tools.traffic.sse`

## 5. Codex Target (Tier 3)

- [x] 5.1 Create `probe/targets/codex/traffic.py` — define `capture_profile` and `analysis_profile` using types from `probe.tools.traffic.types`, import renderers from `probe.renderers.openai_responses`

## 6. Scripts & Tests

- [x] 6.1 Create `scripts/probe/codex/run_capture.sh` — thin shell wrapper calling `python -m agent_system_dissect.probe.tools.traffic.runner --target codex`
- [x] 6.2 Create `tests/integration/probe/codex/test_traffic_capture.py` — migrate from `tmp/codex-traffic/scripts/test_capture.py`, update imports

## 7. Verification

- [x] 7.1 Run `pixi run ruff check src/agent_system_dissect/probe/` — no lint errors
- [x] 7.2 Run `pixi run mypy src/agent_system_dissect/probe/` — no type errors (capture_addon.py excluded: mitmproxy is not a project dep)
- [x] 7.3 Run `python -m agent_system_dissect.probe.tools.traffic.analyze --target codex --input tmp/codex-traffic/traffic.jsonl --output tmp/codex-traffic/analysis_report_new.md` — produces report matching previous output
- [x] 7.4 Verify report content: compare `analysis_report_new.md` with existing `analysis_report.md` for structural equivalence (same sections, same data, same body summaries)

## 8. CLI Override of Profile Defaults

- [x] 8.1 Add `--output-dir` and `--upstream-proxy` CLI arguments to `runner.py`, using profile values as defaults when not specified
- [x] 8.2 Verify `analyze.py` already accepts `--input` and `--output` as CLI args (no profile-derived defaults for paths)
- [x] 8.3 Re-run verification: `pixi run ruff check src/agent_system_dissect/probe/` and `pixi run mypy src/agent_system_dissect/probe/ --exclude capture_addon` — no errors
