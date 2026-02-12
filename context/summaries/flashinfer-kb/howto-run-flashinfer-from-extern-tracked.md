# How to run FlashInfer from `extern/tracked/flashinfer`

This note captures the Pixi-first workflow used in this repository to compile and run the vendored FlashInfer checkout, including preflight checks and a minimal smoke test.

## What you need first

- Linux (FlashInfer installation docs currently list Linux-only support).
- NVIDIA GPU with compute capability SM75 or newer (Turing or later).
- Host NVIDIA driver/runtime compatible with CUDA 12.9 (this repo’s `flashinfer-dev` target).
- Pixi installed.

Quick host check:

```bash
nvidia-smi
```

## Repository workflow (Pixi only, no direct pip installs)

Dependency provisioning is managed by `pyproject.toml` + `pixi.lock`. Do not run direct `pip install` commands for this workflow.

One-time sync:

```bash
pixi lock
pixi install -e flashinfer-dev
```

Standard run sequence:

```bash
pixi run -e flashinfer-dev fi-preflight
pixi run -e flashinfer-dev fi-sync
pixi run -e flashinfer-dev fi-show-config
pixi run -e flashinfer-dev fi-smoke
```

## What `flashinfer-dev` includes by default

- Vendored editable install from `extern/tracked/flashinfer` via Pixi manifest.
- CUDA toolchain packages from the `nvidia` channel, pinned to CUDA 12.9 alignment.
- `flashinfer-cubin` and `flashinfer-jit-cache` in the default `flashinfer-dev` dependency set.
- PyTorch CUDA wheels resolved through the Pixi-managed PyPI configuration for `cu129`.

## Sources

- https://docs.flashinfer.ai/installation.html
- https://docs.flashinfer.ai/cli.html
- https://github.com/flashinfer-ai/flashinfer/blob/main/README.md
- https://github.com/flashinfer-ai/flashinfer/blob/main/CONTRIBUTING.md
- https://github.com/flashinfer-ai/flashinfer/blob/main/requirements.txt
