## MODIFIED Requirements

### Requirement: Store Traffic in Structured Format
The system SHALL save the recorded traffic data in a structured format (e.g., JSON, HAR) to a persistent storage location for later analysis.

#### Scenario: Save to File
- **WHEN** a request/response cycle is complete
- **THEN** the system appends the traffic data to `traffic.jsonl` in the output directory specified by the active CaptureProfile

#### Scenario: Preserve Full Request/Response Bodies
- **WHEN** a request/response pair is recorded
- **THEN** the entry contains the complete request body (including JSON payloads such as model config, instructions, input messages, and tool definitions) and the complete response body (including full SSE event streams)
- **AND** no content is truncated or summarized at capture time

#### Scenario: Maintain Chronological Order
- **WHEN** multiple request/response pairs are captured during a session
- **THEN** entries in `traffic.jsonl` are ordered chronologically by the time each response was received, preserving the conversation turn sequence
