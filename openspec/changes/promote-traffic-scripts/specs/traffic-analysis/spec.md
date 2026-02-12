## MODIFIED Requirements

### Requirement: Generate Analysis Report
The system SHALL generate a readable report (e.g., Markdown) summarizing the findings from the traffic analysis.

#### Scenario: Create Markdown Report
- **WHEN** analysis is complete
- **THEN** the system saves a Markdown file containing the summary of endpoints, request counts, and payload structures

#### Scenario: Include Full Conversation Log
- **WHEN** analysis is complete
- **THEN** the report includes a full conversation log section showing every captured request/response pair with:
  - Request headers (with sensitive values redacted per the AnalysisProfile's redacted header set) in code blocks
  - Response headers in code blocks
  - Request body rendered by the AnalysisProfile's request body renderer callable
  - Response body rendered by the AnalysisProfile's response body renderer callable
- **AND** long content sections are wrapped in collapsible `<details>` sections to keep the report scannable
- **AND** actual content excerpts use fenced code blocks within the collapsible sections
