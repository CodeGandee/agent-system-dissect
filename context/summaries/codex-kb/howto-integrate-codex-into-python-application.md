# How to integrate Codex into a Python application

This note explains practical integration patterns for using Codex from Python, based on the vendored `extern/tracked/codex/codex-rs` source.

## Choose the integration surface

- Use `codex exec` when you want one-shot, non-interactive automation.
- Use `codex app-server` when you need a long-lived, stateful session protocol (threads/turns/events/approvals).

Rule of thumb:
- Batch jobs / CI / fire-and-forget tasks: `codex exec`.
- Product backend serving users with resumable conversations: `codex app-server`.

## Pattern A: `codex exec` (one-shot process, optional persistent thread)

`codex exec` always runs as a subprocess per turn, then exits. You can still do both stateless and session-persistent conversations.

### A1. Stateless one-off turn (`--ephemeral`)

Use this when every request is independent and should not be resumed later.

```python
import json
import subprocess

def run_one_off(prompt: str) -> list[dict]:
    proc = subprocess.Popen(
        ["codex", "exec", "--json", "--ephemeral"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = proc.communicate(prompt, timeout=1800)
    if proc.returncode != 0:
        raise RuntimeError(f"codex exec failed: {stderr}")
    return [json.loads(line) for line in stdout.splitlines() if line.strip()]
```

### A2. Session-persistent conversation via `threadId` + `resume`

This is the same model used by the TypeScript `codex-sdk`: capture `thread.started.thread_id`, then call future turns with `resume <thread_id>`.

```python
import json
import subprocess

def run_exec_turn(prompt: str, thread_id: str | None = None) -> tuple[list[dict], str | None]:
    cmd = ["codex", "exec", "--json"]
    if thread_id:
        cmd += ["resume", thread_id]
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = proc.communicate(prompt, timeout=1800)
    if proc.returncode != 0:
        raise RuntimeError(f"codex exec failed: {stderr}")
    events = [json.loads(line) for line in stdout.splitlines() if line.strip()]

    next_thread_id = thread_id
    for event in events:
        if event.get("type") == "thread.started":
            next_thread_id = event.get("thread_id")
            break
    return events, next_thread_id
```

Store `thread_id` in your DB keyed by your app session/user so later turns can resume the same Codex thread.

Why this is good:
- Lowest protocol complexity.
- Easy retries and horizontal scaling (one subprocess per turn).
- Lets you choose stateless or persistent behavior per use case.

## Pattern B: `codex app-server` (stateful sessions)

`codex app-server` is a bidirectional JSON-RPC protocol over stdio.

Architecture:
- Frontends talk to your Python backend.
- Backend spawns and manages `codex app-server` subprocesses.
- Backend maps your app session/user to Codex `threadId`.

Minimal request flow:
1. Start subprocess.
2. Send `initialize`.
3. Send `initialized`.
4. Send `thread/start` to create a thread.
5. Send `turn/start` for user input.
6. Read streamed notifications until `turn/completed`.

Skeleton:

```python
import json
import subprocess

proc = subprocess.Popen(
    ["codex", "app-server"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
)

def send(msg: dict) -> None:
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()

send({
    "id": 1,
    "method": "initialize",
    "params": {"clientInfo": {"name": "my_python_backend", "version": "0.1.0"}},
})
send({"method": "initialized", "params": {}})
send({"id": 2, "method": "thread/start", "params": {"cwd": "/path/to/workspace"}})
```

## Multi-user/session strategy

Use one `app-server` process per user/tenant (or per isolated workspace), not a shared multi-tenant process.

Reason:
- State and auth are tied to `codex_home`.
- Thread history and rollouts are persisted and looked up from that state.
- `app-server` uses stdio JSON-RPC (subprocess channel), so it is naturally process-scoped.

Recommended mapping:
- Your app session ID -> Codex `threadId`.
- Persist mapping in your DB.
- Resume with `thread/resume` for ongoing conversations.

## Storage and memory behavior

Default behavior:
- Codex persists config/session/auth state under `CODEX_HOME` (default `~/.codex`).

Near-memory mode:
- In `thread/start`, set `"ephemeral": true`.
- Keep `CODEX_HOME` on a temp/tmpfs path for reduced disk persistence.

Caveats for ephemeral threads:
- `includeTurns` readback is not supported for ephemeral threads.
- Resume-by-thread-id via persisted rollout is unavailable unless there is a rollout on disk.

## Approval handling (important for app-server)

Your backend must handle server-initiated approval requests during a turn:
- command execution approvals
- file change approvals

Route approval state by `(threadId, turnId)` and respond with accept/decline.

## Operational checklist

1. Build/install `codex` binary and ensure it is in `PATH`.
2. Set per-user/per-tenant `CODEX_HOME` isolation.
3. Decide `exec` vs `app-server` based on session needs.
4. For `app-server`, implement initialize + event loop + approvals.
5. Persist your own mapping from app identity to Codex `threadId`.
6. Add restart/recovery logic for subprocess crashes.

## Source pointers in vendored code

- `extern/tracked/codex/codex-rs/README.md` (`codex exec`, workspace overview)
- `extern/tracked/codex/codex-rs/app-server/README.md` (protocol, lifecycle, events, approvals)
- `extern/tracked/codex/codex-rs/app-server-protocol/src/protocol/v2.rs` (`thread/start` fields including `ephemeral`)
- `extern/tracked/codex/codex-rs/app-server/src/codex_message_processor.rs` (ephemeral behavior and thread handling)
- `extern/tracked/codex/codex-rs/core/src/config/mod.rs` (`CODEX_HOME` defaults/behavior)
- `extern/tracked/codex/codex-rs/core/src/auth/storage.rs` (auth storage behavior)
- `extern/tracked/codex/sdk/typescript/src/exec.ts` + `extern/tracked/codex/sdk/typescript/src/thread.ts` (`codex-sdk` pattern: parse `thread.started`, then `resume <threadId>`)
