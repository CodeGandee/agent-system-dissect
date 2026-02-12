#!/bin/bash
# capture_codex.sh — Start reverse proxies and capture Codex traffic.
#
# Usage:
#   ./capture_codex.sh                                  # proxies only (manual Codex)
#   ./capture_codex.sh -- codex exec "write hello.py"   # proxies + auto-run codex
#
# Prerequisites:
#   - mitmproxy installed: uv tool install mitmproxy
#   - agent-system-dissect package installed (pixi install && pixi shell)
#   - OPENAI_API_KEY set in environment
#
# Output:
#   tmp/codex-traffic/traffic.jsonl  (JSONL log of all captured HTTP flows)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"

cd "$REPO_ROOT"

echo "--- Codex Traffic Capture ---"
echo "Output: tmp/codex-traffic/traffic.jsonl"
echo ""

python -m agent_system_dissect.probe.tools.traffic.runner --target codex "$@"
