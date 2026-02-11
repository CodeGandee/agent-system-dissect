# agent-system-dissect

## Project Overview

**agent-system-dissect** is a Python project dedicated to dissecting and analyzing popular agent frameworks to learn from their architecture and implementation.

*   **Status:** Early stage (initial structure set up, source currently empty).
*   **Tech Stack:** Python 3.11+
*   **Package Manager:** [Pixi](https://prefix.dev/)
*   **Build Backend:** Hatchling

## Environment & Setup

The project uses `pixi` for dependency management and environment isolation.

### Prerequisites

*   **Pixi:** Ensure `pixi` is installed.
*   **Linux/WSL:** The project is configured for Linux environments.

### Setting up the Environment

1.  **Install Dependencies:**
    Pixi automatically handles environment creation and dependency installation.
    ```bash
    pixi install
    ```

2.  **Activate Shell:**
    ```bash
    pixi shell
    ```

3.  **Configure Environment Variables:**
    Source the setup script to configure proxies and `CODEX_HOME` (if applicable).
    ```bash
    source setup-envs.sh
    ```

## Development Workflow

This project appears to utilize **OpenSpec**, a spec-driven development workflow, and leverages **Magic Context** for reusable AI prompts.

### OpenSpec

*   **Configuration:** `openspec/config.yaml`
*   **Specs & Changes:** Located in `openspec/specs` and `openspec/changes`.
*   **Agent Skills:** The project includes specialized agent skills (e.g., `openspec-new-change`, `openspec-apply-change`, `openspec-verify-change`) to facilitate this workflow. These can be activated to guide development from specification to implementation.

### Magic Context

The `magic-context/` directory contains a knowledge base of re-usable prompts and guides (`magic-context/README.md`). It is structured into:
*   `general/`: Universal prompts and guides (e.g., Python coding guides, git setup).
*   `blender-plugin/`: (Likely inherited context, possibly less relevant unless this project targets Blender).

## Key Directories

*   `src/agent_system_dissect/`: Main source code package (currently empty).
*   `openspec/`: Contains specifications and change definitions for the OpenSpec workflow.
*   `magic-context/`: Shared context and guides for AI assistance.
*   `.github/`: Contains workflow definitions, prompts, and skills configurations.
*   `tests/`: Directory for tests (Integration, Manual, Unit).

## Commands

*   **Run Tests:** (To be defined - likely `pytest` via `pixi run test` if configured, or direct execution).
*   **Lint/Format:** `ruff` is listed as a dependency.
    ```bash
    pixi run ruff check .
    ```
