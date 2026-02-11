## Context

The project aims to understand the behavior of the `codex` agent tool by analyzing its network traffic with OpenAI. Currently, we have no mechanism to observe this traffic. We need a non-intrusive way to capture HTTPS requests and responses and a set of tools to derive insights from this data.

## Goals / Non-Goals

**Goals:**
- reliably intercept HTTPS traffic from `codex`.
- store traffic in a machine-readable format (JSON/JSONLines).
- provide a script to summarize traffic patterns (endpoints, frequency, payload structure).
- minimize setup complexity for the user.

**Non-Goals:**
- building a real-time traffic dashboard.
- modifying the `codex` source code to log traffic (we want black-box observation).
- decrypting traffic without a CA certificate (standard MITM approach requires CA installation).

## Decisions

### 1. Traffic Capture Tool: `mitmproxy` (`mitmdump`)
We will use `mitmproxy`, specifically the `mitmdump` CLI tool, to handle the HTTPS interception.
*   **Rationale**: Industry standard, robust, supports Python scripting for custom logic, and handles certificate generation/management.
*   **Alternatives**:
    *   `Wireshark`/`tcpdump`: Captures packets but decrypting TLS is difficult/impossible without key logging.
    *   Custom `http.server` proxy: Hard to implement correct HTTPS MITM logic from scratch.

### 2. Storage Format: JSONLines (`.jsonl`)
Traffic will be logged to a JSONLines file where each line is a JSON object representing a request/response pair.
*   **Rationale**: Streaming-friendly (append-only), easy to parse line-by-line in Python, human-readable.
*   **Alternatives**:
    *   `HAR` (HTTP Archive): Standard but can be verbose and monolithic (hard to stream write).
    *   `SQLite`: Overkill for this scale.

### 3. Analysis Approach: Python Script
A dedicated Python script will ingest the `.jsonl` file and produce a Markdown report.
*   **Rationale**: leverages the project's Python ecosystem; flexible for custom analysis logic (e.g., counting specific JSON keys in payloads).

## Risks / Trade-offs

-   **Risk**: `codex` might enforce strict SSL pinning.
    *   **Mitigation**: If pinning is used, we might need to patch `codex` to accept the system/mitmproxy CA, but for a "dissect" project, this is an acceptable hurdle. We assume standard HTTPS.
-   **Risk**: Environment configuration for proxying.
    *   **Mitigation**: We will provide clear instructions (or a wrapper script) to set `HTTP_PROXY`, `HTTPS_PROXY`, and `REQUESTS_CA_BUNDLE` environment variables so `codex` routes traffic through `mitmdump`.

## Implementation Plan

1.  **Capture Script**: Write a `mitmproxy` addon script (`capture_traffic.py`) to filter for OpenAI domains and log req/resp pairs to `traffic.jsonl`.
2.  **Analysis Script**: Write `analyze_traffic.py` to read `traffic.jsonl` and output `analysis_report.md`.
3.  **Runner**: Create a shell script to launch `mitmdump` with the addon and set necessary env vars for the user's shell.
