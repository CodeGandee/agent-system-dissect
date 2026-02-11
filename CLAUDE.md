# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**agent-system-dissect** is a Python project for dissecting and analyzing popular agent frameworks to learn from their architecture and implementation. The project is in early stage with infrastructure set up but source code currently minimal.

## Tech Stack

- **Language:** Python 3.13 (requires 3.11+)
- **Package Manager:** Pixi
- **Build System:** Hatchling
- **Linting:** ruff
- **Type Checking:** mypy
- **Development Workflow:** OpenSpec (spec-driven development)
- **AI Context:** Magic Context (submodule for reusable prompts)

## Environment Setup

```bash
# Install dependencies and create environment
pixi install

# Activate the environment
pixi shell

# Configure environment variables (CODEX_HOME, proxies)
source setup-envs.sh

# Add SSH keys if needed
./add-my-keys.sh
```

## Development Commands

```bash
# Linting
pixi run ruff check .

# Type checking
pixi run mypy src/

# Run tests (when configured)
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests
pytest                       # All tests
```

## Architecture

### Directory Structure

- **src/agent_system_dissect/** - Main Python package (currently empty, awaiting implementation)
- **context/** - Centralized AI knowledge base with design docs, hints, issues, plans, tasks, etc.
- **openspec/** - Spec-driven development artifacts (specs/ and changes/)
- **magic-context/** - Git submodule with reusable AI prompts and templates
- **extern/tracked/** - Git submodules for pinned external dependencies (e.g., Codex fork)
- **extern/orphan/** - Local-only external code (not tracked in git)
- **tests/** - Test suite organized by type: unit/, integration/, manual/
- **scripts/** - CLI tools and automation scripts
- **docs/** - Project documentation
- **tmp/** - Temporary files (git-ignored)

### OpenSpec Workflow

This project uses OpenSpec for spec-driven development:

- Configuration: `openspec/config.yaml`
- Specifications: `openspec/specs/`
- Active changes: `openspec/changes/`
- Available skills: `openspec-new-change`, `openspec-continue-change`, `openspec-apply-change`, `openspec-verify-change`, `openspec-archive-change`

Use these skills to follow the structured workflow from specification to implementation.

### Context Directory

The `context/` directory is a knowledge base for AI assistants:
- **design/** - Technical specs and architecture
- **hints/** - Troubleshooting and how-to guides
- **instructions/** - Reusable prompt snippets
- **issues/** - Known and resolved issues
- **plans/** - Implementation roadmaps
- **tasks/** - Work items (backlog/, working/, done/)
- **rules/** - Task-specific rules for AI agents
- **summaries/** - Knowledge base and analysis

Consult these directories before making significant changes.

### External Dependencies

**Tracked (git submodules):**
- `magic-context/` - Reusable prompts and AI interaction patterns
- `extern/tracked/codex/` - Forked Codex codebase (branch: hz-dev)

**Orphan (local-only):**
- `extern/orphan/` - Temporary clones and references (git-ignored except README)

Update submodules explicitly and review changes carefully.

## Testing Conventions

- Unit tests: Fast, deterministic, hermetic tests in `tests/unit/`
- Integration tests: Tests with external dependencies in `tests/integration/`
- Manual scripts: Non-CI scripts in `tests/manual/` (prefix: `manual_*.py`)
- Test files use `test_*.py` naming convention

Keep unit tests independent and use `pixi run` for execution when tasks are configured.

## Git Workflow

- **Main branch:** `master` (use this for PRs)
- **Current branch:** `main`
- Commit messages follow conventional commits style
- External dependencies managed via git submodules

## Special Files

- **GEMINI.md** - Documentation for Gemini AI (similar purpose to this file)
- **pyproject.toml** - Project metadata and build configuration
- **pixi.lock** - Locked dependencies for reproducible builds
- **.codex/** - Codex-related configuration (if present, CODEX_HOME is set)

## Notes

- The project currently has minimal source code - most work ahead is implementation
- Magic Context provides proven prompt patterns for AI development - refer to it for guidance
- OpenSpec skills are available for structured development workflow
- Environment variables (especially proxies) are auto-configured via setup scripts
