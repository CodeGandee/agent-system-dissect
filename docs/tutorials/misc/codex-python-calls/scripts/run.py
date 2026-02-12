#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import select
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


TUTORIAL_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path(__file__).resolve().parents[5]
INPUTS_PATH = TUTORIAL_DIR / "inputs" / "cases.json"
OUTPUTS_DIR = TUTORIAL_DIR / "outputs"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, data: Any) -> None:
    sanitized = sanitize_for_output(data)
    path.write_text(json.dumps(sanitized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


SECRET_KEY_HINTS = ("api_key", "apikey", "token", "secret", "password", "auth")
SECRET_VALUE_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~-]{16,}\b"),
]


def mask_string_value(value: str) -> str:
    masked = value
    workspace_root = str(WORKSPACE_ROOT.resolve())
    home_dir = str(Path.home().resolve())
    if workspace_root:
        masked = masked.replace(workspace_root, "<WORKSPACE_ROOT>")
    if home_dir:
        masked = masked.replace(home_dir, "<HOME>")
    for pattern in SECRET_VALUE_PATTERNS:
        masked = pattern.sub("<REDACTED>", masked)
    return masked


def sanitize_for_output(value: Any, key_hint: str = "") -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_lower = str(key).lower()
            if any(hint in key_lower for hint in SECRET_KEY_HINTS) and isinstance(item, str):
                sanitized[key] = "<REDACTED>"
            else:
                sanitized[key] = sanitize_for_output(item, key_lower)
        return sanitized
    if isinstance(value, list):
        return [sanitize_for_output(item, key_hint) for item in value]
    if isinstance(value, str):
        if any(hint in key_hint for hint in SECRET_KEY_HINTS):
            return "<REDACTED>"
        return mask_string_value(value)
    return value


def normalize_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip()


def is_exact_match(actual: Any, expected: str) -> bool:
    return normalize_text(actual) == expected


def unique_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def find_codex_candidates() -> list[str]:
    proc = subprocess.run(
        ["bash", "-lc", "which -a codex || true"],
        cwd=str(WORKSPACE_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    return unique_keep_order(lines)


def pick_host_codex(candidates: list[str]) -> str | None:
    workspace_prefix = str(WORKSPACE_ROOT.resolve())
    for candidate in candidates:
        try:
            resolved = str(Path(candidate).resolve())
        except OSError:
            resolved = candidate
        if not resolved.startswith(workspace_prefix + os.sep):
            return candidate
    if candidates:
        return candidates[0]
    return None


def read_version(codex_path: str) -> str:
    proc = subprocess.run(
        [codex_path, "--version"],
        cwd=str(WORKSPACE_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    stdout = proc.stdout.strip()
    if stdout:
        return stdout
    return proc.stderr.strip()


def exec_supports_flag(codex_path: str, flag: str) -> bool:
    proc = subprocess.run(
        [codex_path, "exec", "--help"],
        cwd=str(WORKSPACE_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    return flag in proc.stdout


def run_command(
    cmd: list[str],
    *,
    env: dict[str, str],
    stdin_text: str,
    timeout_sec: int,
) -> dict[str, Any]:
    started = time.time()
    start_iso = utc_now()
    proc = subprocess.Popen(
        cmd,
        cwd=str(WORKSPACE_ROOT),
        env=env,
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    timed_out = False
    try:
        stdout, stderr = proc.communicate(stdin_text, timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()
        stdout, stderr = proc.communicate()
    end_iso = utc_now()
    return {
        "cmd": cmd,
        "start_utc": start_iso,
        "end_utc": end_iso,
        "duration_sec": round(time.time() - started, 3),
        "timed_out": timed_out,
        "returncode": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
    }


def parse_jsonl(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    parse_errors: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            value = json.loads(stripped)
        except json.JSONDecodeError as err:
            parse_errors.append(
                {
                    "line_number": line_no,
                    "error": str(err),
                    "preview": stripped[:200],
                }
            )
            continue
        if isinstance(value, dict):
            events.append(value)
        else:
            parse_errors.append(
                {
                    "line_number": line_no,
                    "error": f"json root is {type(value).__name__}, expected object",
                    "preview": stripped[:200],
                }
            )
    return events, parse_errors


def find_exec_thread_id(events: list[dict[str, Any]]) -> str | None:
    for event in events:
        if event.get("type") == "thread.started":
            thread_id = event.get("thread_id") or event.get("threadId")
            if isinstance(thread_id, str) and thread_id:
                return thread_id
    return None


def find_exec_final_message(events: list[dict[str, Any]]) -> str | None:
    for event in reversed(events):
        if event.get("type") != "item.completed":
            continue
        item = event.get("item")
        if not isinstance(item, dict):
            continue
        if item.get("type") in {"agent_message", "agentMessage"}:
            text = item.get("text")
            if isinstance(text, str):
                return text
    return None


def make_exec_result(
    *,
    approach: str,
    prompt: str,
    expected: str,
    run: dict[str, Any],
) -> dict[str, Any]:
    events, parse_errors = parse_jsonl(run["stdout"])
    final_message = find_exec_final_message(events)
    thread_id = find_exec_thread_id(events)
    exact_match = is_exact_match(final_message, expected)
    return {
        "approach": approach,
        "status": "ok" if run["returncode"] == 0 and not run["timed_out"] else "failed",
        "command": run["cmd"],
        "returncode": run["returncode"],
        "timed_out": run["timed_out"],
        "duration_sec": run["duration_sec"],
        "prompt_text": prompt,
        "expected_reply": expected,
        "exact_match": exact_match,
        "thread_id": thread_id,
        "final_message": final_message,
        "event_count": len(events),
        "json_parse_error_count": len(parse_errors),
        "json_parse_errors": parse_errors[:5],
        "stderr_tail": run["stderr"][-2000:],
    }


def test_exec_stateless(codex_path: str, env: dict[str, str], case: dict[str, Any]) -> dict[str, Any]:
    prompt = str(case["prompt"])
    expected = str(case["expected_reply"])
    timeout_sec = int(case.get("timeout_sec", 900))
    prefer_ephemeral = bool(case.get("prefer_ephemeral", True))

    supports_ephemeral = exec_supports_flag(codex_path, "--ephemeral")
    cmd = [codex_path, "exec", "--json"]
    mode = "one_off_non_resume"
    notes: list[str] = []
    if prefer_ephemeral and supports_ephemeral:
        cmd.append("--ephemeral")
        mode = "one_off_ephemeral"
    elif prefer_ephemeral:
        notes.append(
            "host codex does not expose --ephemeral for exec; using non-resume one-off invocation"
        )

    run = run_command(cmd, env=env, stdin_text=prompt, timeout_sec=timeout_sec)
    result = make_exec_result(
        approach="exec_stateless",
        prompt=prompt,
        expected=expected,
        run=run,
    )
    result["stateless_mode"] = mode
    result["supports_ephemeral"] = supports_ephemeral
    result["notes"] = notes
    result["success"] = result["status"] == "ok" and bool(result.get("exact_match"))
    result["conversation_turn"] = {
        "input": prompt,
        "expected_reply": expected,
        "actual_reply": result.get("final_message"),
        "exact_match": result.get("exact_match"),
    }
    return result


def test_exec_persistent(codex_path: str, env: dict[str, str], case: dict[str, Any]) -> dict[str, Any]:
    reference_code = f"REF-{uuid4().hex[:12].upper()}"
    turn1_prompt = str(case["turn1_prompt_template"]).format(reference_code=reference_code)
    turn1_expected = str(case["turn1_expected_reply"])
    turn2_prompt = str(case["turn2_prompt"])
    turn2_expected = reference_code
    timeout_sec = int(case.get("timeout_sec", 900))

    turn1_run = run_command(
        [codex_path, "exec", "--json"],
        env=env,
        stdin_text=turn1_prompt,
        timeout_sec=timeout_sec,
    )
    turn1_result = make_exec_result(
        approach="exec_persistent_turn_1",
        prompt=turn1_prompt,
        expected=turn1_expected,
        run=turn1_run,
    )

    resume_thread_id = turn1_result.get("thread_id")
    turn2_result: dict[str, Any] | None = None
    if isinstance(resume_thread_id, str) and resume_thread_id:
        turn2_run = run_command(
            [codex_path, "exec", "--json", "resume", resume_thread_id],
            env=env,
            stdin_text=turn2_prompt,
            timeout_sec=timeout_sec,
        )
        turn2_result = make_exec_result(
            approach="exec_persistent_turn_2_resume",
            prompt=turn2_prompt,
            expected=turn2_expected,
            run=turn2_run,
        )

    same_thread = False
    if isinstance(turn2_result, dict):
        second_tid = turn2_result.get("thread_id")
        same_thread = second_tid in (None, resume_thread_id)

    success = (
        turn1_result["status"] == "ok"
        and bool(turn1_result.get("exact_match"))
        and isinstance(resume_thread_id, str)
        and bool(resume_thread_id)
        and isinstance(turn2_result, dict)
        and turn2_result["status"] == "ok"
        and bool(turn2_result.get("exact_match"))
        and same_thread
    )

    return {
        "approach": "exec_persistent_resume",
        "success": success,
        "thread_id": resume_thread_id,
        "same_thread_on_resume": same_thread,
        "session_persistence_proof": {
            "reference_code_from_turn_1": reference_code,
            "turn_2_expected_to_recall_reference_code": True,
            "turn_2_exact_match": turn2_result.get("exact_match") if isinstance(turn2_result, dict) else False,
        },
        "turn_1": turn1_result,
        "turn_2": turn2_result,
        "conversation_turns": [
            {
                "turn": 1,
                "input": turn1_prompt,
                "expected_reply": turn1_expected,
                "actual_reply": turn1_result.get("final_message"),
                "exact_match": turn1_result.get("exact_match"),
            },
            {
                "turn": 2,
                "input": turn2_prompt,
                "expected_reply": turn2_expected,
                "actual_reply": turn2_result.get("final_message") if isinstance(turn2_result, dict) else None,
                "exact_match": turn2_result.get("exact_match") if isinstance(turn2_result, dict) else False,
            },
        ],
    }


def parse_app_server_agent_text(messages: list[dict[str, Any]]) -> str | None:
    for message in reversed(messages):
        if message.get("method") not in {"item/completed", "item.completed"}:
            continue
        params = message.get("params")
        if not isinstance(params, dict):
            continue
        item = params.get("item")
        if not isinstance(item, dict):
            continue
        if item.get("type") in {"agentMessage", "agent_message"}:
            text = item.get("text")
            if isinstance(text, str):
                return text
    return None


def test_app_server(codex_path: str, env: dict[str, str], case: dict[str, Any]) -> dict[str, Any]:
    prompt = str(case["prompt"])
    expected = str(case["expected_reply"])
    timeout_sec = int(case.get("timeout_sec", 300))

    started = time.time()
    messages: list[dict[str, Any]] = []
    parse_errors: list[dict[str, Any]] = []
    process: subprocess.Popen[str] | None = None
    error: str | None = None
    thread_id: str | None = None
    turn_id: str | None = None
    final_message: str | None = None

    def send_json(payload: dict[str, Any]) -> None:
        if process is None or process.stdin is None:
            raise RuntimeError("app-server stdin is unavailable")
        process.stdin.write(json.dumps(payload) + "\n")
        process.stdin.flush()

    def read_next_json(timeout: float) -> dict[str, Any]:
        if process is None or process.stdout is None:
            raise RuntimeError("app-server stdout is unavailable")
        deadline = time.time() + timeout
        while time.time() < deadline:
            if process.poll() is not None:
                stderr = process.stderr.read() if process.stderr is not None else ""
                raise RuntimeError(
                    f"app-server exited early with code {process.returncode}; stderr: {stderr[-2000:]}"
                )
            remaining = max(0.0, deadline - time.time())
            wait = min(0.25, remaining)
            ready, _, _ = select.select([process.stdout], [], [], wait)
            if not ready:
                continue
            line = process.stdout.readline()
            if not line:
                continue
            stripped = line.strip()
            if not stripped:
                continue
            try:
                msg = json.loads(stripped)
            except json.JSONDecodeError as err:
                parse_errors.append({"error": str(err), "preview": stripped[:200]})
                continue
            if isinstance(msg, dict):
                messages.append(msg)
                return msg
            parse_errors.append({"error": "non-object json message", "preview": stripped[:200]})
        raise TimeoutError(f"timed out waiting for app-server message after {timeout} seconds")

    def wait_for(predicate, timeout: float) -> dict[str, Any]:
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = read_next_json(max(0.1, deadline - time.time()))
            if predicate(msg):
                return msg
        raise TimeoutError(f"timed out waiting for condition after {timeout} seconds")

    try:
        process = subprocess.Popen(
            [codex_path, "app-server"],
            cwd=str(WORKSPACE_ROOT),
            env=env,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
        )
        send_json(
            {
                "id": 1,
                "method": "initialize",
                "params": {
                    "clientInfo": {
                        "name": "tutorial_python_client",
                        "title": "Tutorial Python Client",
                        "version": "0.1.0",
                    }
                },
            }
        )
        wait_for(lambda m: m.get("id") == 1, timeout=45)
        send_json({"method": "initialized", "params": {}})

        send_json({"id": 2, "method": "thread/start", "params": {"cwd": str(WORKSPACE_ROOT)}})
        thread_resp = wait_for(lambda m: m.get("id") == 2, timeout=60)
        thread = thread_resp.get("result", {}).get("thread", {})
        if isinstance(thread, dict) and isinstance(thread.get("id"), str):
            thread_id = thread["id"]
        if not thread_id:
            raise RuntimeError("thread/start response missing thread id")

        send_json(
            {
                "id": 3,
                "method": "turn/start",
                "params": {
                    "threadId": thread_id,
                    "input": [{"type": "text", "text": prompt}],
                },
            }
        )
        turn_resp = wait_for(lambda m: m.get("id") == 3, timeout=60)
        turn = turn_resp.get("result", {}).get("turn", {})
        if isinstance(turn, dict) and isinstance(turn.get("id"), str):
            turn_id = turn["id"]

        def is_completed(msg: dict[str, Any]) -> bool:
            if msg.get("method") not in {"turn/completed", "turn.completed"}:
                return False
            if not turn_id:
                return True
            params = msg.get("params", {})
            if not isinstance(params, dict):
                return False
            payload = params.get("turn", {})
            return isinstance(payload, dict) and payload.get("id") == turn_id

        wait_for(is_completed, timeout=max(60, timeout_sec))
        final_message = parse_app_server_agent_text(messages)
    except Exception as exc:
        error = str(exc)
    finally:
        if process is not None:
            if process.stdin is not None and not process.stdin.closed:
                process.stdin.close()
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception:
                process.kill()
                process.wait(timeout=5)

    exact_match = is_exact_match(final_message, expected)
    status = "ok" if error is None else "failed"
    return {
        "approach": "app_server_stateful",
        "status": status,
        "success": status == "ok" and exact_match,
        "duration_sec": round(time.time() - started, 3),
        "prompt_text": prompt,
        "expected_reply": expected,
        "exact_match": exact_match,
        "thread_id": thread_id,
        "turn_id": turn_id,
        "final_message": final_message,
        "message_count": len(messages),
        "json_parse_error_count": len(parse_errors),
        "json_parse_errors": parse_errors[:10],
        "error": error,
        "conversation_turn": {
            "input": prompt,
            "expected_reply": expected,
            "actual_reply": final_message,
            "exact_match": exact_match,
        },
    }


def build_conversation_inspection(tests: list[dict[str, Any]]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for test in tests:
        approach = test.get("approach")
        if approach == "exec_stateless":
            records.append(
                {
                    "approach": approach,
                    "mode": test.get("stateless_mode"),
                    "thread_id": test.get("thread_id"),
                    "turns": [test.get("conversation_turn")],
                }
            )
        elif approach == "exec_persistent_resume":
            records.append(
                {
                    "approach": approach,
                    "thread_id": test.get("thread_id"),
                    "same_thread_on_resume": test.get("same_thread_on_resume"),
                    "turns": test.get("conversation_turns"),
                    "proof": test.get("session_persistence_proof"),
                }
            )
        elif approach == "app_server_stateful":
            records.append(
                {
                    "approach": approach,
                    "thread_id": test.get("thread_id"),
                    "turn_id": test.get("turn_id"),
                    "turns": [test.get("conversation_turn")],
                }
            )
    return {"generated_utc": utc_now(), "records": records}


def load_cases() -> dict[str, Any]:
    return json.loads(INPUTS_PATH.read_text(encoding="utf-8"))


def main() -> int:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    cases = load_cases()

    candidates = find_codex_candidates()
    codex_path = pick_host_codex(candidates)
    if codex_path is None:
        write_json(
            OUTPUTS_DIR / "summary.json",
            {
                "run_started_utc": utc_now(),
                "run_finished_utc": utc_now(),
                "error": "codex not found in PATH",
                "codex_candidates": candidates,
                "tests": [],
                "all_success": False,
            },
        )
        print("ERROR: codex not found in PATH")
        return 1

    default_codex_home = WORKSPACE_ROOT / ".codex"
    base_env = dict(os.environ)
    if "CODEX_HOME" not in base_env and default_codex_home.is_dir():
        base_env["CODEX_HOME"] = str(default_codex_home)

    run_started = utc_now()
    tests: list[dict[str, Any]] = []

    exec_stateless = test_exec_stateless(codex_path, base_env, cases["exec_stateless"])
    tests.append(exec_stateless)
    write_json(OUTPUTS_DIR / "result-exec-stateless.json", exec_stateless)

    exec_persistent = test_exec_persistent(codex_path, base_env, cases["exec_persistent"])
    tests.append(exec_persistent)
    write_json(OUTPUTS_DIR / "result-exec-persistent.json", exec_persistent)

    app_server = test_app_server(codex_path, base_env, cases["app_server"])
    tests.append(app_server)
    write_json(OUTPUTS_DIR / "result-app-server.json", app_server)

    conversation_inspection = build_conversation_inspection(tests)
    write_json(OUTPUTS_DIR / "conversation-inspection.json", conversation_inspection)

    all_success = all(test.get("success", False) for test in tests)
    summary = {
        "run_started_utc": run_started,
        "run_finished_utc": utc_now(),
        "workspace_root": str(WORKSPACE_ROOT),
        "tutorial_dir": str(TUTORIAL_DIR),
        "inputs_file": str(INPUTS_PATH),
        "outputs_dir": str(OUTPUTS_DIR),
        "codex_candidates": candidates,
        "selected_codex": codex_path,
        "selected_codex_version": read_version(codex_path),
        "codex_home": base_env.get("CODEX_HOME"),
        "conversation_file": str(OUTPUTS_DIR / "conversation-inspection.json"),
        "tests": tests,
        "all_success": all_success,
    }
    write_json(OUTPUTS_DIR / "summary.json", summary)

    print(
        json.dumps(
            {
                "summary_file": str(OUTPUTS_DIR / "summary.json"),
                "conversation_file": str(OUTPUTS_DIR / "conversation-inspection.json"),
                "all_success": all_success,
            }
        )
    )
    return 0 if all_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
