#!/bin/bash
# run_full_workflow.sh — Capture + analyze in one shot.
#
# Runs codex with traffic capture, then immediately generates the analysis report.
# This is the quickest way to get a full traffic report from a single Codex prompt.
#
# Usage:
#   ./run_full_workflow.sh "write a hello world function in Python"
#
# Prerequisites:
#   - mitmproxy installed: uv tool install mitmproxy
#   - agent-system-dissect package installed (pixi install && pixi shell)
#   - OPENAI_API_KEY set in environment
#
# Output:
#   tmp/codex-traffic/traffic.jsonl         (raw JSONL capture)
#   tmp/codex-traffic/analysis_report.md    (Markdown report)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"

cd "$REPO_ROOT"

PROMPT="${1:?Usage: $0 \"<prompt>\"}"

OUTPUT_DIR="tmp/codex-traffic"
JSONL="$OUTPUT_DIR/traffic.jsonl"
REPORT="$OUTPUT_DIR/analysis_report.md"

echo "=== Step 1: Capture traffic ==="
echo "Prompt: $PROMPT"
echo ""

python -m agent_system_dissect.probe.tools.traffic.runner \
    --target codex \
    -- codex exec "$PROMPT"

echo ""
echo "=== Step 2: Analyze traffic ==="
echo ""

python -m agent_system_dissect.probe.tools.traffic.analyze \
    --target codex \
    --input "$JSONL" \
    --output "$REPORT"

echo ""
echo "=== Done ==="
echo "  Raw traffic:  $JSONL"
echo "  Report:       $REPORT"
