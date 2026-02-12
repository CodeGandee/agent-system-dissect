#!/bin/bash
# analyze_traffic.sh — Generate a Markdown analysis report from captured traffic.
#
# Usage:
#   ./analyze_traffic.sh                                          # default paths
#   ./analyze_traffic.sh --input path/to/traffic.jsonl            # custom input
#   ./analyze_traffic.sh --input in.jsonl --output report.md      # custom both
#
# Prerequisites:
#   - agent-system-dissect package installed (pixi install && pixi shell)
#   - A traffic.jsonl file from a previous capture session
#
# Output:
#   Markdown report written to --output path (default: <input_dir>/analysis_report.md)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"

cd "$REPO_ROOT"

# Default paths — override with --input / --output flags
INPUT="${INPUT:-tmp/codex-traffic/traffic.jsonl}"
OUTPUT="${OUTPUT:-tmp/codex-traffic/analysis_report.md}"

echo "--- Codex Traffic Analysis ---"
echo "Input:  $INPUT"
echo "Output: $OUTPUT"
echo ""

python -m agent_system_dissect.probe.tools.traffic.analyze \
    --target codex \
    --input "$INPUT" \
    --output "$OUTPUT"

echo ""
echo "Done. Open $OUTPUT to view the report."
