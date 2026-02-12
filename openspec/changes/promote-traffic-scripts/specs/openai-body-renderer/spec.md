## ADDED Requirements

### Requirement: Render OpenAI Request Bodies
The system SHALL provide a request body renderer for the OpenAI Responses API format that produces summarized Markdown.

#### Scenario: Render Model and Config Fields
- **WHEN** a request body dict is provided
- **THEN** the renderer displays the model name and key config fields (stream, tool_choice, parallel_tool_calls, store, reasoning) inline

#### Scenario: Render System Instructions
- **WHEN** the request body contains an `instructions` field
- **THEN** the renderer shows the character count and a preview in a collapsible `<details>` section with a code block

#### Scenario: Render Input Messages
- **WHEN** the request body contains an `input` array of messages
- **THEN** the renderer shows a table with index, role, type, and content preview for each message
- **AND** each message's full content is available in a collapsible `<details>` section

#### Scenario: Render Tool Definitions
- **WHEN** the request body contains a `tools` array
- **THEN** the renderer lists each tool by name and type in a collapsible section

### Requirement: Render OpenAI SSE Response Bodies
The system SHALL provide a response body renderer for OpenAI SSE streams that produces summarized Markdown.

#### Scenario: Render Event Type Breakdown
- **WHEN** an SSE response body string is provided
- **THEN** the renderer shows total byte size, event count, and a table mapping each event type to its count

#### Scenario: Assemble Output Text
- **WHEN** the SSE stream contains `response.output_text.delta` events
- **THEN** the renderer assembles the full output text and displays it in a collapsible `<details>` section

#### Scenario: Assemble Reasoning Summary
- **WHEN** the SSE stream contains `response.reasoning_summary_text.delta` events
- **THEN** the renderer assembles the reasoning text and displays it in a collapsible `<details>` section

#### Scenario: Extract Tool Calls
- **WHEN** the SSE stream contains `response.function_call_arguments.done` events
- **THEN** the renderer shows each tool call with function name and arguments

#### Scenario: Extract Usage Statistics
- **WHEN** the SSE stream contains a `response.completed` event with usage data
- **THEN** the renderer shows input tokens, output tokens, total tokens, and detail breakdowns (cached, reasoning) if available

### Requirement: Handle Non-Standard Bodies
The renderer SHALL gracefully handle non-standard body formats.

#### Scenario: Non-Dict Request Body
- **WHEN** a request body is a string or other non-dict type
- **THEN** the renderer wraps it in a collapsible `<details>` section with a code block

#### Scenario: Non-SSE Response Body
- **WHEN** a response body is a dict (not an SSE stream)
- **THEN** the renderer formats it as indented JSON in a collapsible `<details>` section
