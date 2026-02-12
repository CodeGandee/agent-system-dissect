## Context

Working traffic capture and analysis scripts exist in `tmp/codex-traffic/scripts/` (git-ignored) from the `analyze-codex-openai-traffic` change. They work well but are monolithic — generic traffic tooling is entangled with codex/OpenAI-specific logic. We want to promote them into tracked source code and restructure for multi-target reuse.

**Current state:**
- `capture_traffic.py` (56 lines) — mitmproxy addon, 100% generic
- `run_capture.sh` (108 lines) — shell orchestrator, 90% codex-specific
- `analyze_traffic.py` (563 lines) — ~60% generic framework, ~40% OpenAI API rendering
- `test_capture.py` (40 lines) — manual capture test

**Key insight:** The body renderers in `analyze_traffic.py` are OpenAI Responses API-specific, not codex-specific. Any target that uses OpenAI's API (Cursor, etc.) would reuse the same renderers. This creates a three-tier architecture: generic tools → API renderers → target configs.

## Goals / Non-Goals

**Goals:**
- Promote scripts from git-ignored `tmp/` into tracked `src/` and `scripts/`.
- Separate generic tools from target-specific configuration via a profile interface.
- Extract OpenAI body renderers as a shared, reusable layer.
- Enable adding new inspection targets (Claude Code, Cursor) by writing only a profile module — no changes to tools.
- Provide CLI entry points: `python -m agent_system_dissect.probe.tools.traffic.analyze --target codex`.

**Non-Goals:**
- Building a plugin discovery/registry system (targets are imported directly by name).
- Deleting the original `tmp/codex-traffic/scripts/` (left as-is for reference).
- Adding new targets beyond codex (future work).
- Changing the JSONL format or capture behavior.

## Decisions

### 1. Package Namespace: `probe`

The top-level subpackage is `agent_system_dissect.probe` (not `inspect`).

- **Rationale**: Avoids shadowing Python's built-in `inspect` module. While full-path imports work (`agent_system_dissect.inspect.tools...`), relative imports within the package and `import inspect` in any submodule would be confusing. `probe` is concise and unambiguous.

### 2. Three-Tier Architecture

```
src/agent_system_dissect/probe/
├── tools/                    # Tier 1: Generic, target-agnostic tools
│   └── traffic/
│       ├── capture_addon.py  #   mitmproxy addon (self-contained)
│       ├── runner.py         #   generic capture runner
│       ├── analyze.py        #   generic analyzer + CLI
│       ├── sse.py            #   SSE stream parser
│       └── types.py          #   CaptureProfile, AnalysisProfile dataclasses
│
├── renderers/                # Tier 2: API-specific body renderers (shared)
│   └── openai_responses.py   #   OpenAI Responses API rendering
│
└── targets/                  # Tier 3: Per-agent-system configs
    └── codex/
        └── traffic.py        #   codex CaptureProfile + AnalysisProfile
```

- **Tier 1 (tools/)**: Pure framework. No knowledge of OpenAI, codex, or any API. Accepts profiles as configuration.
- **Tier 2 (renderers/)**: API-format-specific rendering. Shared across targets using the same API. `openai_responses.py` handles the OpenAI Responses API format (model/instructions/input/tools for requests; SSE events/output/reasoning/tool calls/usage for responses).
- **Tier 3 (targets/)**: Minimal config modules. Each target provides a `CaptureProfile` and `AnalysisProfile`, selecting which renderer to use.

**Rationale**: When adding a target that uses the same API (e.g., Cursor → OpenAI), only a target config is needed. When adding a target with a new API (e.g., Claude Code → Anthropic Messages API), a new renderer + target config is needed. The generic tools never change.

**Alternatives considered**:
- Two-tier (no renderers layer): Would duplicate OpenAI rendering logic across codex and cursor targets.
- Plugin registry with entry points: Overkill for 1-3 targets. Direct imports are simpler.

### 3. Profile Interfaces

```python
@dataclass
class ProxyConfig:
    listen_port: int
    upstream_url: str
    purpose: str

@dataclass
class CaptureProfile:
    name: str
    proxies: list[ProxyConfig]
    upstream_proxy: str | None
    env_overrides: dict[str, str]
    manual_steps: list[str]
    output_dir: str

@dataclass
class AnalysisProfile:
    name: str
    report_title: str
    request_body_renderer: Callable[[Any], str]
    response_body_renderer: Callable[[Any, int], str]
    redacted_headers: set[str]
```

- **Renderers as callables**: The analysis profile carries two functions — `request_body_renderer(body) -> str` and `response_body_renderer(body, status_code) -> str`. The generic analyzer calls these without knowing what API format they handle.
- **Rationale**: Simple function injection. No abstract base classes, no registration, no metaclasses. The codex target imports `format_request_body` and `format_response_body` from `renderers.openai_responses` and passes them to the profile.

### 4. Capture Addon: Self-Contained With Env Var Configuration

The mitmproxy addon (`capture_addon.py`) is loaded by `mitmdump -s` in mitmdump's own Python environment. It cannot import from `agent_system_dissect`.

**Output path configuration**: The addon reads `TRAFFIC_OUTPUT_DIR` env var to determine where to write `traffic.jsonl`. If unset, falls back to a path relative to its own `__file__`. The runner sets this env var before launching mitmdump.

**Rationale**: The runner knows the profile's `output_dir` and passes it to the addon via environment. No file-path coupling between runner and addon.

### 5. CLI Override of Profile Defaults

Target profiles provide sensible defaults, but all directory paths and configurable values are overridable via CLI arguments. CLI arguments always take precedence over profile values.

**Capture runner CLI:**
```bash
python -m agent_system_dissect.probe.tools.traffic.runner \
    --target codex \
    --output-dir /tmp/my-capture \
    --upstream-proxy http://proxy:3128 \
    [-- codex exec "prompt"]
```

**Analyzer CLI:**
```bash
python -m agent_system_dissect.probe.tools.traffic.analyze \
    --target codex \
    --input /path/to/traffic.jsonl \
    --output /path/to/report.md
```

The pattern: profile loads defaults → CLI `argparse` defaults come from profile → explicit CLI args override.

```python
# In runner.py:
profile = load_capture_profile(args.target)
output_dir = args.output_dir or profile.output_dir
upstream_proxy = args.upstream_proxy if args.upstream_proxy is not None else profile.upstream_proxy
```

**Rationale**: Profiles encode team/project conventions (standard ports, proxy addresses, output locations). CLI overrides enable one-off runs, CI pipelines, and environments where defaults don't apply. No directory path should require editing Python source to change.

### 6. Shell Wrapper

`scripts/probe/codex/run_capture.sh` remains as a thin convenience wrapper. It passes all arguments through:

```bash
python -m agent_system_dissect.probe.tools.traffic.runner --target codex "$@"
```

This means CLI overrides work naturally: `./run_capture.sh --output-dir /tmp/test`.

**Rationale**: Some users prefer `./scripts/probe/codex/run_capture.sh` over the module invocation. Minimal maintenance cost.

### 7. Target Discovery

Targets are loaded by direct import:

```python
def load_target(name: str):
    module = importlib.import_module(f"agent_system_dissect.probe.targets.{name}.traffic")
    return module.capture_profile, module.analysis_profile
```

Each target module exports `capture_profile` and `analysis_profile` at module level.

**Rationale**: Simple, explicit, no magic. Adding a target means adding a Python module. The `--target codex` CLI argument maps directly to the module path.

**Alternatives considered**:
- YAML/TOML config files: Can't express renderer callables without a separate mapping layer.
- Entry points / plugin registry: Unnecessary complexity for <5 targets.

### 8. Code Migration Strategy

| Source (tmp/) | Destination (src/) | Changes |
|---|---|---|
| `capture_traffic.py` | `probe/tools/traffic/capture_addon.py` | Add `TRAFFIC_OUTPUT_DIR` env var support |
| `analyze_traffic.py` → generic parts | `probe/tools/traffic/analyze.py` | Remove body renderers, accept AnalysisProfile |
| `analyze_traffic.py` → SSE parser | `probe/tools/traffic/sse.py` | Extract `parse_sse_events()` |
| `analyze_traffic.py` → OpenAI renderers | `probe/renderers/openai_responses.py` | Extract body renderers + helpers |
| `analyze_traffic.py` → codex config | `probe/targets/codex/traffic.py` | New: profile definitions |
| `run_capture.sh` → generic runner | `probe/tools/traffic/runner.py` | New Python runner reading CaptureProfile |
| `run_capture.sh` → shell wrapper | `scripts/probe/codex/run_capture.sh` | Thin wrapper calling Python runner |
| `test_capture.py` | `tests/integration/probe/codex/test_traffic_capture.py` | Update imports |

### 9. File Layout

```
src/agent_system_dissect/
└── probe/
    ├── __init__.py
    ├── tools/
    │   ├── __init__.py
    │   └── traffic/
    │       ├── __init__.py
    │       ├── capture_addon.py
    │       ├── runner.py
    │       ├── analyze.py
    │       ├── sse.py
    │       └── types.py
    ├── renderers/
    │   ├── __init__.py
    │   └── openai_responses.py
    └── targets/
        ├── __init__.py
        └── codex/
            ├── __init__.py
            └── traffic.py

scripts/probe/codex/
└── run_capture.sh

tests/integration/probe/codex/
└── test_traffic_capture.py
```

## Risks / Trade-offs

- **Risk**: `capture_addon.py` must be self-contained (no package imports) because mitmdump loads it in its own environment.
  - **Mitigation**: Already the case today. The env var interface (`TRAFFIC_OUTPUT_DIR`) keeps it decoupled. Add a comment at the top of the file explaining this constraint.

- **Risk**: Adding `TRAFFIC_OUTPUT_DIR` env var to the addon changes its behavior for anyone who had the old version.
  - **Mitigation**: Fallback to `__file__`-relative path when env var is unset, matching current behavior.

- **Trade-off**: Three tiers add indirection vs. a simpler two-tier approach.
  - **Accepted**: The third tier (renderers) prevents duplicating ~200 lines of OpenAI rendering logic when adding a second OpenAI-based target. If only one target ever uses OpenAI, the separation was harmless (just a different file location).

- **Trade-off**: Shell wrapper adds a file to maintain.
  - **Accepted**: It's 3 lines. Deletion cost is zero if it becomes stale.
