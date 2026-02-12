"""
Generic capture runner — launches mitmproxy reverse proxies from a CaptureProfile.

Reads a target's ``CaptureProfile``, starts one ``mitmdump`` reverse
proxy per proxy definition, and optionally runs a target command with
environment overrides applied.  All directory paths are overridable via
CLI arguments.

Functions
---------
load_capture_profile : Import a CaptureProfile by target name.
run : Launch reverse proxies and optionally run a target command.
main : CLI entry point.

Examples
--------
::

    python -m agent_system_dissect.probe.tools.traffic.runner \\
        --target codex \\
        --output-dir tmp/my-capture \\
        --upstream-proxy http://proxy:3128 \\
        [-- codex exec "prompt"]
"""

from __future__ import annotations

import argparse
import importlib
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from agent_system_dissect.probe.tools.traffic.types import CaptureProfile


ADDON_PATH = Path(__file__).parent / "capture_addon.py"


def load_capture_profile(target_name: str) -> CaptureProfile:
    """
    Load a CaptureProfile by target name.

    Parameters
    ----------
    target_name : str
        Target identifier (e.g. ``"codex"``).  Maps to
        ``agent_system_dissect.probe.targets.<target_name>.traffic``.

    Returns
    -------
    CaptureProfile
        The target's capture profile.
    """
    module = importlib.import_module(
        f"agent_system_dissect.probe.targets.{target_name}.traffic"
    )
    return module.capture_profile  # type: ignore[no-any-return]


def run(profile: CaptureProfile, target_cmd: list[str] | None = None) -> None:
    """
    Launch reverse proxies and optionally run a target command.

    Starts one ``mitmdump`` reverse proxy instance per entry in
    ``profile.proxies``, waits for them to bind, then either runs
    *target_cmd* with ``profile.env_overrides`` applied or blocks
    until the user presses Ctrl-C.

    Parameters
    ----------
    profile : CaptureProfile
        Capture configuration to use.
    target_cmd : list of str or None, optional
        Command (and arguments) to execute under the proxies.  If
        ``None``, the runner prints instructions and waits.
    """
    mitmdump = shutil.which("mitmdump")
    if not mitmdump:
        print(
            "ERROR: mitmdump not found. Install via: uv tool install mitmproxy",
            file=sys.stderr,
        )
        sys.exit(1)

    output_dir = os.path.abspath(profile.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    print(f"=== Traffic Capture: {profile.name} (Reverse Proxy Mode) ===")
    print()
    for proxy in profile.proxies:
        print(f"  :{proxy.listen_port} -> {proxy.upstream_url}  ({proxy.purpose})")
    if profile.upstream_proxy:
        print(f"  Upstream proxy: {profile.upstream_proxy}")
    print(f"  Traffic log: {output_dir}/traffic.jsonl")
    print()

    if profile.manual_steps:
        print("Manual setup required:")
        for step in profile.manual_steps:
            print(f"  - {step}")
        print()

    env = os.environ.copy()
    env["TRAFFIC_OUTPUT_DIR"] = output_dir

    procs: list[subprocess.Popen[bytes]] = []

    def cleanup(signum: int | None = None, frame: object = None) -> None:
        """Terminate all mitmdump child processes."""
        print("\nStopping mitmdump instances...")
        for p in procs:
            p.terminate()
        for p in procs:
            p.wait()
        print(f"Done. Traffic saved to: {output_dir}/traffic.jsonl")

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    try:
        for proxy in profile.proxies:
            cmd = [
                mitmdump,
                "--mode", f"reverse:{proxy.upstream_url}",
                "-p", str(proxy.listen_port),
                "-s", str(ADDON_PATH),
                "-q",
            ]
            if profile.upstream_proxy:
                cmd.extend(["--set", f"upstream_proxy={profile.upstream_proxy}/"])
            procs.append(subprocess.Popen(cmd, env=env))

        time.sleep(2)

        for p in procs:
            if p.poll() is not None:
                print(
                    f"ERROR: mitmdump (pid {p.pid}) exited early"
                    f" with code {p.returncode}",
                    file=sys.stderr,
                )
                cleanup()
                sys.exit(1)

        print("All proxies are running.")

        if target_cmd:
            target_env = env.copy()
            target_env.update(profile.env_overrides)
            print(f"\nRunning: {' '.join(target_cmd)}")
            print("---")
            result = subprocess.run(target_cmd, env=target_env)
            cleanup()
            sys.exit(result.returncode)
        else:
            if profile.env_overrides:
                print("\nEnvironment overrides for target:")
                for k, v in profile.env_overrides.items():
                    print(f"  export {k}={v}")
            print("\nPress Ctrl+C to stop.")
            for p in procs:
                p.wait()

    except Exception:
        cleanup()
        raise


def main() -> None:
    """Parse CLI arguments, load the target profile, and run capture."""
    parser = argparse.ArgumentParser(
        description="Launch mitmproxy reverse proxies to capture agent traffic."
    )
    parser.add_argument(
        "--target",
        required=True,
        help="Target name (e.g., 'codex') — loads the matching CaptureProfile.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for traffic.jsonl (overrides profile default).",
    )
    parser.add_argument(
        "--upstream-proxy",
        default=None,
        help="Upstream proxy URL for internet access (overrides profile default).",
    )
    parser.add_argument(
        "command",
        nargs="*",
        help="Optional command to run with env overrides applied.",
    )
    args = parser.parse_args()

    profile = load_capture_profile(args.target)
    if args.output_dir is not None:
        profile.output_dir = args.output_dir
    if args.upstream_proxy is not None:
        profile.upstream_proxy = args.upstream_proxy
    run(profile, args.command or None)


if __name__ == "__main__":
    main()
