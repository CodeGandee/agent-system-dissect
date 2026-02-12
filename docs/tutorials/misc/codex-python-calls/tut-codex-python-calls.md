---
tutorial_name: codex-python-calls
created_at: 2026-02-12T08:21:37Z
base_commit: 3ae9ed8fecd1dca7cb7b606291a96e0beea7772a
topic: Codex CLI - Python integration for exec and app-server
runtime:
  os: Ubuntu 24.04.3 LTS (Linux 6.8.0-90-generic x86_64)
  python: 3.12.3
  device: cpu
  notes: codex-cli 0.98.0; defaults CODEX_HOME to <workspace>/.codex when present
---

# How to call Codex from Python (3 practical cases)

## Question

How do I call Codex from Python in three ways:
1. Stateless one-off turn via `codex exec`
2. Session-persistent multi-turn via `codex exec resume`
3. Stateful protocol flow via `codex app-server`

## Prerequisites

This tutorial assumes prerequisites are already met.

- `codex` is installed and available in `PATH`.
- Auth is already configured (for this workspace, `.codex/auth.json` exists).
- Python 3.10+ is available.
- You are running from this repository root.

## Implementation Idea

- **Approach:**
  1. Use Python `subprocess` to call the host `codex`.
  2. Keep prompts/test-cases in `inputs/cases.json`.
  3. For each integration mode, run a minimal verification prompt and check exact reply match.
  4. Write all artifacts to `outputs/`:
     - per-case result JSON
     - consolidated conversation transcript JSON
     - run summary JSON

## Critical Example Code

The full implementation is in `scripts/run.py`. The snippet below shows the key `codex exec` pattern and exact-match verification.

```python
import json
import subprocess

# 1) Build the codex exec command.
#    - Use --json to consume machine-readable JSONL events.
#    - Add ["resume", thread_id] only when continuing an existing session.
cmd = ["codex", "exec", "--json"]
if thread_id is not None:
    cmd += ["resume", thread_id]

# 2) Send the prompt via stdin and collect stdout/stderr.
proc = subprocess.Popen(
    cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
stdout, stderr = proc.communicate(prompt, timeout=900)

# 3) Parse JSONL events and extract:
#    - thread_id from "thread.started"
#    - final assistant reply from "item.completed"
events = [json.loads(line) for line in stdout.splitlines() if line.strip()]

# 4) Verify exact match with expected output.
actual_reply = extract_final_message(events)
ok = (actual_reply or "").strip() == expected_reply
```

Run the full tutorial script:

```bash
python3 docs/tutorials/misc/codex-python-calls/scripts/run.py
```

## Input and Output

### Input

Tutorial input file: `inputs/cases.json`

- `exec_stateless`: one-off prompt and expected reply.
- `exec_persistent`: turn-1 template + turn-2 recall prompt.
- `app_server`: one-turn prompt and expected reply.

### Output

Generated under `outputs/`:

- `result-exec-stateless.json`
- `result-exec-persistent.json`
- `result-app-server.json`
- `conversation-inspection.json`
- `summary.json`

Safety note:
- Generated JSON output is sanitized by the script:
  - Absolute workspace/home paths are replaced with `<WORKSPACE_ROOT>` / `<HOME>`.
  - Secret-like values are replaced with `<REDACTED>`.

Representative transcript shape (`conversation-inspection.json`):

```json
{
  "records": [
    {
      "approach": "exec_persistent_resume",
      "turns": [
        {
          "turn": 1,
          "input": "... reference code ...",
          "actual_reply": "stored",
          "exact_match": true
        },
        {
          "turn": 2,
          "input": "... recall previous reference code ...",
          "actual_reply": "REF-XXXXXXXXXXXX",
          "exact_match": true
        }
      ]
    }
  ]
}
```

## Verification

Run:

```bash
python3 docs/tutorials/misc/codex-python-calls/scripts/run.py
```

Then confirm:

1. `docs/tutorials/misc/codex-python-calls/outputs/summary.json` has `"all_success": true`.
2. `docs/tutorials/misc/codex-python-calls/outputs/conversation-inspection.json` exists.
3. In `conversation-inspection.json`, all turns have `"exact_match": true`.
4. In `result-exec-persistent.json`, both:
   - `"same_thread_on_resume": true`
   - `"session_persistence_proof.turn_2_exact_match": true`

## Appendix

### Troubleshooting

- `codex not found in PATH`:
  - Ensure host installation is active (for example `which codex`).
- Auth errors / unauthorized:
  - Ensure `CODEX_HOME` points to a valid home with credentials (`auth.json`).
- `--ephemeral` unsupported:
  - Older host versions may not support it in `codex exec`; the script falls back to non-resume one-off mode.
- `app-server` timeout:
  - Re-run and inspect `outputs/result-app-server.json` for protocol error text.

### Key parameters

| Name | Meaning | Value used by this tutorial |
|---|---|---|
| `CODEX_HOME` | Codex home/config/auth root | `<workspace>/.codex` (if present and not pre-set) |
| `exec_stateless.prompt` | one-off exec verification prompt | arithmetic exact match |
| `exec_persistent.turn1_prompt_template` | persistence seed prompt | stores dynamic reference code |
| `exec_persistent.turn2_prompt` | persistence recall prompt | asks for turn-1 code |
| `app_server.prompt` | app-server verification prompt | arithmetic exact match |

## References

- Codex Rust workspace README: `extern/tracked/codex/codex-rs/README.md`
- App server protocol docs: `extern/tracked/codex/codex-rs/app-server/README.md`
- This repo smoke harness basis: `tmp/codex-python-integration-smoke/run_codex_approaches.py`
