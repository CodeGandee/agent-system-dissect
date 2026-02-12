## Why

The traffic capture and analysis scripts currently live in `tmp/codex-traffic/scripts/` (git-ignored). They are working, tested tools that should be promoted into the main repo as tracked source code. Additionally, the scripts are monolithic — generic traffic tooling (JSONL capture, stats aggregation, report generation) is entangled with codex/OpenAI-specific logic (body rendering, proxy setup). As we plan to inspect other agent systems (Claude Code, Cursor, Devin, etc.), the tools need to be restructured so reusable parts are separated from target-specific configuration.

## What Changes

- Introduce `src/agent_system_dissect/probe/` package as the top-level namespace for all agent inspection work.
- Create `probe/tools/traffic/` with generic, reusable traffic capture and analysis tools that accept target profiles as configuration.
- Create `probe/renderers/` for API-specific body renderers (starting with OpenAI Responses API) shared across multiple targets.
- Create `probe/targets/codex/` with codex-specific capture and analysis profiles (proxy definitions, env vars, renderer selection).
- Move the mitmproxy capture addon to `probe/tools/traffic/capture_addon.py` (self-contained, loaded via `mitmdump -s`).
- Replace `run_capture.sh` with a generic Python capture runner (`probe/tools/traffic/runner.py`) that reads a target's `CaptureProfile`.
- Replace the monolithic `analyze_traffic.py` with a generic analyzer (`probe/tools/traffic/analyze.py`) that accepts an `AnalysisProfile` with pluggable body renderers.
- Move the shell wrapper to `scripts/probe/codex/run_capture.sh` (thin wrapper calling the Python runner).
- Define `CaptureProfile` and `AnalysisProfile` dataclasses as the configuration interface between tools and targets.

## Capabilities

### New Capabilities
- `traffic-tool-framework`: Generic traffic capture and analysis framework — defines profile interfaces (CaptureProfile, AnalysisProfile), the generic capture runner, the generic analyzer, and the SSE parser. Target-agnostic.
- `openai-body-renderer`: OpenAI Responses API body renderers — summarized rendering of request bodies (model/instructions/input/tools) and SSE response bodies (event breakdown/output text/reasoning/tool calls/usage). Shared across any target that uses the OpenAI API.
- `codex-target-profile`: Codex-specific target configuration — capture profile (proxy definitions, env vars) and analysis profile (renderer selection, header redaction rules).

### Modified Capabilities
- `traffic-capture`: Capture addon moves from tmp to tracked source; runner becomes profile-driven instead of hardcoded.
- `traffic-analysis`: Analyzer becomes profile-driven with pluggable body renderers instead of hardcoded OpenAI logic.

## Impact

- **New package**: `src/agent_system_dissect/probe/` with subpackages `tools/`, `renderers/`, `targets/`.
- **Scripts**: `scripts/probe/codex/run_capture.sh` replaces `tmp/codex-traffic/scripts/run_capture.sh`.
- **Tests**: `tests/integration/probe/codex/test_traffic_capture.py` replaces `tmp/codex-traffic/scripts/test_capture.py`.
- **No external dependency changes** — mitmproxy is still invoked via `uv tool run`.
- **Output data** stays in `tmp/codex-traffic/` (git-ignored, configured via profile's `output_dir`).
- **Original scripts in tmp/ are left as-is** — no deletion, users can compare.
