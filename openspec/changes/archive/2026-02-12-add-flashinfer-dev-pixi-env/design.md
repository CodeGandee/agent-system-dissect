## Context

This repository already uses Pixi as the primary environment manager, with a default environment and a feature-specific `codex-build` environment. FlashInfer development currently depends on manual setup in `extern/tracked/flashinfer` (virtualenv, PyTorch/CUDA alignment, editable install), which is easy to misconfigure and hard to reproduce across contributors.

The main constraint is CUDA/PyTorch/toolchain compatibility. The design must make FlashInfer setup reproducible without destabilizing existing repository workflows.

## Goals / Non-Goals

**Goals:**
- Provide a dedicated Pixi environment `flashinfer-dev` for FlashInfer compile-and-run workflows.
- Encode required dependencies and workflow commands as Pixi configuration and tasks.
- Keep onboarding simple: contributor runs a small sequence of `pixi run -e flashinfer-dev ...` commands.
- Preserve existing default and `codex-build` environments.

**Non-Goals:**
- Re-architect FlashInfer itself or modify its upstream build system.
- Guarantee success on hosts without supported GPU/CUDA runtime.
- Add CI pipeline changes in this change unless explicitly requested later.

## Decisions

1. Introduce a feature-scoped Pixi environment instead of extending `default`.
   Rationale: avoids polluting unrelated workflows with heavy GPU/toolchain dependencies.
   Alternative considered: add dependencies to `default`; rejected due to environment bloat and coupling.

2. Use task-driven setup and validation commands under `flashinfer-dev`.
   Rationale: tasks provide a canonical, discoverable workflow and reduce command drift.
   Alternative considered: rely only on documentation snippets; rejected because manual copy/paste is less reliable.

3. Install FlashInfer from vendored source in editable mode via Pixi manifest declarations.
   Rationale: keeps installation reproducible, declarative, and aligned with Pixi-first environment management.
   Alternative considered: direct `pip` install commands inside setup tasks; rejected because imperative installs drift from manifest state.

4. Keep host/toolchain checks explicit and early.
   Rationale: fast failure when GPU/CUDA preconditions are not met prevents opaque compile errors later.
   Alternative considered: implicit failure during build; rejected due to poor developer experience.

5. Pin the FlashInfer development CUDA target to 12.9.
   Rationale: this resolves version ambiguity and aligns with the intended repository baseline for this change.
   Alternative considered: 12.8; rejected to keep a single explicit target.

6. Include optional FlashInfer artifact packages by default (`flashinfer-cubin` and `flashinfer-jit-cache`).
   Rationale: reduces first-run latency and avoids repeated ad-hoc package decisions by contributors.
   Alternative considered: install optional packages manually per user; rejected due to workflow inconsistency.

7. Add NVIDIA toolchain packages via Pixi with `nvidia` channel priority for NVIDIA components.
   Rationale: user-space reproducibility and consistent CUDA toolchain resolution require explicit channel priority and tool packages.
   Alternative considered: relying on host CUDA tools or mixed channel defaults; rejected due to drift and compatibility risk.

8. Treat existing Pixi environments as immutable for this change (`default`, `codex-build`, and other pre-existing envs).
   Rationale: this change is scoped to introducing `flashinfer-dev`, and cross-environment edits can create unintended regressions.
   Alternative considered: adjusting shared/default environment constraints to satisfy solver conflicts; rejected unless explicitly approved by a developer.

9. Enforce a no-direct-pip policy for this workflow.
   Rationale: dependency state must live in Pixi manifest/lock for reproducibility and reviewability.
   Alternative considered: allowing ad-hoc `pip` installs for convenience; rejected due to hidden state and non-reproducible environments.

## Risks / Trade-offs

- [Risk] CUDA/toolchain package resolution may vary by host and channel availability.
  -> Mitigation: pin key versions conservatively and provide a dedicated preflight task.
- [Risk] FlashInfer dependency stack may evolve and require future updates.
  -> Mitigation: keep FlashInfer tasks isolated so maintenance is localized to one Pixi feature.
- [Risk] Solver conflicts may tempt changes to existing environments.
  -> Mitigation: stop implementation and escalate to developer for direction instead of modifying other environments.
- [Trade-off] Separate environment adds maintenance overhead.
  -> Mitigation: reduced setup drift and clearer contributor workflow outweighs added config.

## Migration Plan

1. Add `flashinfer-dev` feature, environment entry, and tasks in `pyproject.toml`, with CUDA 12.9 and NVIDIA tooling from the `nvidia` channel.
2. Add FlashInfer and related PyPI requirements through Pixi manifest declarations for `flashinfer-dev` (no direct `pip` installs).
3. Validate task sequence on a supported GPU host.
4. Update contributor-facing FlashInfer setup notes to prefer the new environment.
5. Keep existing manual setup guidance only as fallback where necessary.

## Open Questions

- None currently. Resolved inputs:
  - CUDA target for `flashinfer-dev`: 12.9
  - Include optional packages by default: `flashinfer-cubin`, `flashinfer-jit-cache`
  - Add NVIDIA toolchain packages in Pixi using the `nvidia` channel with priority over `conda-forge` for NVIDIA packages
  - Never use direct `pip` installs for this workflow; add PyPI dependencies to Pixi manifest instead
