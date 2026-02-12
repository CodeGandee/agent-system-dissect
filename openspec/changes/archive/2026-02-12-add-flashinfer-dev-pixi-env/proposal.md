## Why

Developers currently need ad-hoc local setup to build and run vendored FlashInfer from `extern/tracked/flashinfer`, which creates toolchain drift across machines. This is especially brittle for CUDA/PyTorch alignment, and our current default Pixi environment does not provide FlashInfer-ready dependencies.

## What Changes

- Add a dedicated Pixi environment named `flashinfer-dev` for FlashInfer development and validation.
- Pin FlashInfer environment CUDA alignment to 12.9 and include dependencies needed to compile and run FlashInfer in editable mode (Python, CUDA toolchain, build tools, and PyTorch stack).
- Add NVIDIA toolchain packages through Pixi using the `nvidia` channel with priority for NVIDIA packages.
- Add repeatable Pixi tasks for host/toolchain checks, editable installation from `extern/tracked/flashinfer`, configuration verification, and a minimal GPU smoke test.
- Include optional FlashInfer artifact packages (`flashinfer-cubin`, `flashinfer-jit-cache`) in the default `flashinfer-dev` setup flow.
- Enforce Pixi-only dependency provisioning: do not use direct `pip` install commands; add required PyPI dependencies to the Pixi manifest.
- Document the intended workflow so contributors can run FlashInfer setup with a small set of standard commands.

## Capabilities

### New Capabilities
- `flashinfer-dev-environment`: Provide a reproducible Pixi-based workflow to compile and run vendored FlashInfer code in this repository.

### Modified Capabilities
- None.

## Impact

- Affected files: workspace `pyproject.toml` (Pixi features/environments/tasks), plus FlashInfer setup documentation under `context/summaries/flashinfer-kb/` and/or related docs.
- Affected dependencies: additional Pixi-managed packages from CUDA/PyTorch ecosystems.
- Affected systems: local GPU development workflow for FlashInfer submodule work.
