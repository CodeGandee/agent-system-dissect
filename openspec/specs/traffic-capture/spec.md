## ADDED Requirements

### Requirement: Capture HTTP/HTTPS Traffic
The system SHALL intercept HTTP and HTTPS traffic between the local machine and remote endpoints, specifically targeting communication with OpenAI's API.

#### Scenario: Intercept HTTPS Request
- **WHEN** a tool (e.g., `codex`) sends an HTTPS request to `api.openai.com`
- **THEN** the system intercepts the request before it reaches the destination

#### Scenario: Intercept HTTPS Response
- **WHEN** the remote server sends a response back to the tool
- **THEN** the system intercepts the response before it reaches the tool

### Requirement: Record Traffic Data
The system SHALL record the full details of intercepted requests and responses, including headers, body, method, and URL.

#### Scenario: Log Request Details
- **WHEN** a request is intercepted
- **THEN** the system logs the timestamp, method, URL, headers, and body content

#### Scenario: Log Response Details
- **WHEN** a response is intercepted
- **THEN** the system logs the status code, headers, and body content

### Requirement: Store Traffic in Structured Format
The system SHALL save the recorded traffic data in a structured format (e.g., JSON, HAR) to a persistent storage location for later analysis.

#### Scenario: Save to File
- **WHEN** a request/response cycle is complete
- **THEN** the system appends the traffic data to `tmp/codex-traffic/traffic.jsonl` in the workspace

#### Scenario: Preserve Full Request/Response Bodies
- **WHEN** a request/response pair is recorded
- **THEN** the entry contains the complete request body (including JSON payloads such as model config, instructions, input messages, and tool definitions) and the complete response body (including full SSE event streams)
- **AND** no content is truncated or summarized at capture time

#### Scenario: Maintain Chronological Order
- **WHEN** multiple request/response pairs are captured during a session
- **THEN** entries in `traffic.jsonl` are ordered chronologically by the time each response was received, preserving the conversation turn sequence
