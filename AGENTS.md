# Repository Guidelines

## Project Structure & Module Organization

- `src/agent_system_dissect/`: Main Python package.
  - `probe/tools/traffic/`: Capture + analysis CLIs (`runner.py`, `analyze.py`).
  - `probe/renderers/`: API-specific payload renderers.
  - `probe/targets/<name>/`: Target configs (e.g. `codex/traffic.py`).
- `tests/`: Test layout scaffold; see `tests/README.md` for conventions.
- `docs/`: Markdown tutorials (example: traffic capture walkthroughs).
- `scripts/`: Small CLI helpers and automation entry points.
- `context/`, `openspec/`, `.codex/`: Design notes and OpenSpec workflow artifacts.
- `extern/`, `magic-context/`: Git submodules / vendored external code.
- `tmp/`: Generated artifacts (captures, reports). Avoid committing.

## Build, Test, and Development Commands

- `git submodule update --init --recursive`: Fetch submodules (`magic-context`, `extern/tracked/codex`).
- `pixi install`: Create the dev environment (Python 3.13 by default) and install deps.
- `pixi shell`: Activate the environment (or prefix commands with `pixi run`).
- If capturing live HTTP traffic: install mitmproxy (`uv tool install mitmproxy`) to get `mitmdump`.
- Capture traffic (Codex example):
  - `pixi run python -m agent_system_dissect.probe.tools.traffic.runner --target codex`
  - `pixi run python -m agent_system_dissect.probe.tools.traffic.runner --target codex -- codex exec "..."` (run a command under capture)
- Analyze a capture:
  - `pixi run python -m agent_system_dissect.probe.tools.traffic.analyze --target codex --input tmp/codex-traffic/traffic.jsonl --output tmp/codex-traffic/analysis_report.md`
- Optional submodule builds (Pixi environment `codex-build`):
  - `pixi run -e codex-build build-codex-rs` (Rust `codex` binary)
  - `pixi run -e codex-build build-gui` (requires `pnpm`)

## Coding Style & Naming Conventions

- Python: 4-space indentation; prefer type hints for public functions and dataclasses.
- Naming: `snake_case` for files/functions, `PascalCase` for classes.
- Tooling (installed via Pixi): `ruff` for lint/format, `mypy` for type checks.
  - `pixi run ruff format .`
  - `pixi run ruff check .`
  - `pixi run mypy src`

## Testing Guidelines

- Follow `tests/README.md` structure: `tests/unit/`, `tests/integration/`, `tests/manual/`.
- Keep unit tests hermetic; place I/O/network/service tests under `tests/integration/`.
- Run tests (when `pytest` is available in your environment): `pixi run python -m pytest`.

## Commit & Pull Request Guidelines

- Commits in this repo are generally imperative; some use Conventional Commit prefixes (e.g. `chore:`).
  - Prefer: `feat: ...`, `fix: ...`, `docs: ...`, `chore: ...` with a short subject.
- PRs should include: what/why, a concrete test plan (commands run), and links to relevant specs/notes in `openspec/` or `context/` when applicable.
- Security: never commit secrets (e.g. `OPENAI_API_KEY`) or raw traffic captures; keep logs and generated reports under `tmp/`.
