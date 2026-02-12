## 1. Define Pixi Environment

- [x] 1.1 Add a new Pixi feature section for `flashinfer-dev` in `pyproject.toml` with FlashInfer-required dependencies (Python, CUDA 12.9 alignment, build tools, and PyTorch stack).
- [x] 1.2 Add NVIDIA toolchain packages required for compile-and-run workflows (including `cuda-nvcc` and CUDA development/runtime libraries) to the `flashinfer-dev` feature.
- [x] 1.3 Configure channel priority so NVIDIA packages for `flashinfer-dev` resolve from `nvidia` before `conda-forge`.
- [x] 1.4 Add a `flashinfer-dev` entry under `[tool.pixi.environments]` that enables the new feature without altering existing environment behavior.
- [x] 1.5 If solver constraints cannot be satisfied without editing `default` or other pre-existing environments, stop and request explicit developer guidance before proceeding.
- [x] 1.6 Declare vendored FlashInfer and any required PyPI dependencies in Pixi manifest entries for `flashinfer-dev` rather than installing with ad-hoc commands.

## 2. Add FlashInfer Workflow Tasks

- [x] 2.1 Add a preflight task to validate GPU/CUDA/PyTorch readiness and fail fast with actionable diagnostics.
- [x] 2.2 Add an install/sync task that provisions editable FlashInfer from `extern/tracked/flashinfer` through Pixi-managed dependency resolution (no direct `pip` commands).
- [x] 2.3 Include optional artifact packages (`flashinfer-cubin`, `flashinfer-jit-cache`) in the default setup flow for `flashinfer-dev`.
- [x] 2.4 Add a configuration task that runs FlashInfer config reporting (`python -m flashinfer show-config` or equivalent).
- [x] 2.5 Add a minimal GPU smoke task that executes a basic FlashInfer runtime operation and reports success/failure clearly.

## 3. Document and Validate

- [x] 3.1 Update repository guidance for FlashInfer setup to reference the `flashinfer-dev` command flow.
- [x] 3.2 Run the `flashinfer-dev` task sequence on a supported host and confirm each task completes as expected.
- [x] 3.3 Sanity-check existing Pixi workflows (`default`, `codex-build`) to verify they remain unaffected by this change.
- [x] 3.4 Confirm final diff for this change does not modify dependency/channel/task definitions of `default` or other pre-existing environments.
- [x] 3.5 Confirm implementation does not introduce direct `pip` installation commands and that new PyPI dependencies are tracked in Pixi manifest.
