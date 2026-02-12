#!/bin/bash
# analyze_sample.sh — Run analysis on the bundled sample traffic.jsonl.
#
# This script demonstrates the analysis pipeline without needing a live
# Codex session or API key. It uses the synthetic sample input bundled
# with this tutorial.
#
# Usage:
#   ./analyze_sample.sh
#
# Prerequisites:
#   - agent-system-dissect package installed (pixi install && pixi shell)
#
# Output:
#   docs/tutorials/probe/traffic-capture/outputs/sample_report.md
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TUTORIAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$TUTORIAL_DIR/../../../.." && pwd)"

cd "$REPO_ROOT"

INPUT="$TUTORIAL_DIR/inputs/sample_traffic.jsonl"
OUTPUT="$TUTORIAL_DIR/outputs/sample_report.md"

echo "--- Sample Traffic Analysis ---"
echo "Input:  $INPUT"
echo "Output: $OUTPUT"
echo ""

python -m agent_system_dissect.probe.tools.traffic.analyze \
    --target codex \
    --input "$INPUT" \
    --output "$OUTPUT"

echo ""
echo "Done. Open $OUTPUT to view the sample report."
