#!/bin/bash
# Thin wrapper to launch codex traffic capture via the generic runner.
#
# Usage:
#   ./run_capture.sh                       # start proxies only
#   ./run_capture.sh codex exec "prompt"   # start proxies, run codex, stop proxies
set -euo pipefail

python -m agent_system_dissect.probe.tools.traffic.runner --target codex "$@"
