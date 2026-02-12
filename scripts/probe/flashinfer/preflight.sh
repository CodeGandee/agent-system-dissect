#!/usr/bin/env bash

set -euo pipefail

command -v nvidia-smi >/dev/null 2>&1 || {
  echo "nvidia-smi not found" >&2
  exit 1
}

nvidia-smi -L >/dev/null

if ! nvcc --version | grep -q "release 12.9"; then
  echo "Expected nvcc release 12.9 from flashinfer-dev environment" >&2
  nvcc --version >&2
  exit 1
fi

python - <<'PY'
import torch

cuda_version = torch.version.cuda or ""
if not torch.cuda.is_available():
    raise SystemExit("torch.cuda.is_available() is False")
if not cuda_version.startswith("12.9"):
    raise SystemExit(f"Expected torch CUDA 12.9, got {cuda_version}")
print("preflight-ok", torch.__version__, cuda_version)
PY
