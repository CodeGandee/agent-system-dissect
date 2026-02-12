## ADDED Requirements

### Requirement: Define Capture Profile Interface
The system SHALL define a `CaptureProfile` data structure that describes how to set up traffic capture for any target agent system.

#### Scenario: CaptureProfile Contains Proxy Definitions
- **WHEN** a CaptureProfile is defined
- **THEN** it SHALL include a list of proxy configurations, each specifying a listen port, upstream URL, and purpose description

#### Scenario: CaptureProfile Contains Environment Overrides
- **WHEN** a CaptureProfile is defined
- **THEN** it SHALL include a dictionary of environment variable overrides to set before running the target

#### Scenario: CaptureProfile Contains Manual Steps
- **WHEN** a CaptureProfile is defined
- **THEN** it SHALL include a list of manual configuration steps (e.g., config file edits) that the user must perform

#### Scenario: CaptureProfile Contains Output Directory
- **WHEN** a CaptureProfile is defined
- **THEN** it SHALL include an output directory path where captured traffic data is written

### Requirement: Define Analysis Profile Interface
The system SHALL define an `AnalysisProfile` data structure that describes how to analyze and render traffic for any target agent system.

#### Scenario: AnalysisProfile Contains Report Metadata
- **WHEN** an AnalysisProfile is defined
- **THEN** it SHALL include a target name and report title

#### Scenario: AnalysisProfile Contains Pluggable Body Renderers
- **WHEN** an AnalysisProfile is defined
- **THEN** it SHALL include a request body renderer callable and a response body renderer callable, each accepting the raw body and returning a Markdown string

#### Scenario: AnalysisProfile Contains Header Redaction Rules
- **WHEN** an AnalysisProfile is defined
- **THEN** it SHALL include a set of header names whose values are redacted in the report

### Requirement: Generic Capture Runner
The system SHALL provide a generic capture runner that launches mitmproxy reverse proxy instances based on a CaptureProfile.

#### Scenario: Launch Proxies From Profile
- **WHEN** the capture runner is invoked with a CaptureProfile
- **THEN** it launches one `mitmdump` reverse proxy instance per proxy definition in the profile

#### Scenario: Chain Through Upstream Proxy
- **WHEN** the CaptureProfile specifies an upstream proxy
- **THEN** each mitmdump instance is configured with `--set upstream_proxy=<url>`

#### Scenario: Apply Environment Overrides
- **WHEN** the CaptureProfile specifies environment overrides
- **THEN** the runner prints the overrides and applies them when launching the target command (if provided)

#### Scenario: Display Manual Steps
- **WHEN** the CaptureProfile includes manual configuration steps
- **THEN** the runner displays them to the user before starting

### Requirement: CLI Override of Profile Defaults
All directory paths and configurable values provided by target profiles SHALL be overridable via CLI arguments. The profile provides defaults; CLI arguments take precedence.

#### Scenario: Runner Output Directory Override
- **WHEN** the capture runner is invoked with `--output-dir <path>`
- **THEN** the runner uses `<path>` as the output directory instead of the profile's `output_dir`

#### Scenario: Runner Upstream Proxy Override
- **WHEN** the capture runner is invoked with `--upstream-proxy <url>`
- **THEN** the runner uses `<url>` as the upstream proxy instead of the profile's `upstream_proxy`

#### Scenario: Analyzer Input Path Required
- **WHEN** the analyzer is invoked
- **THEN** it requires `--input <path>` as a CLI argument (no default derived from profile)

#### Scenario: Analyzer Output Path Override
- **WHEN** the analyzer is invoked with `--output <path>`
- **THEN** the report is written to `<path>` instead of the default location

#### Scenario: Profile Values Are Defaults Only
- **WHEN** a target profile defines `output_dir`, `upstream_proxy`, or other configurable values
- **THEN** those values serve as defaults that are always overridable from the command line

### Requirement: Generic Traffic Analyzer
The system SHALL provide a generic traffic analyzer that reads JSONL traffic data and produces a Markdown report using an AnalysisProfile.

#### Scenario: Analyze With Pluggable Renderers
- **WHEN** the analyzer is invoked with an AnalysisProfile and a JSONL input file
- **THEN** it calls the profile's request body renderer for each request body and the profile's response body renderer for each response body

#### Scenario: Generate Statistics Without Target Knowledge
- **WHEN** the analyzer computes aggregate statistics (endpoint counts, methods, status codes, payload structure)
- **THEN** no target-specific logic is involved — statistics are computed generically from the JSONL data

#### Scenario: Target Selection Via CLI
- **WHEN** the analyzer is run from the command line
- **THEN** it accepts a `--target <name>` argument that loads the corresponding target's AnalysisProfile

### Requirement: Generic SSE Parser
The system SHALL provide a reusable SSE (Server-Sent Events) stream parser.

#### Scenario: Parse SSE Stream Into Events
- **WHEN** an SSE-formatted string is provided
- **THEN** the parser returns a list of event objects, each with an event type and parsed data payload

#### Scenario: Handle JSON and Non-JSON Data
- **WHEN** an SSE event's data field contains valid JSON
- **THEN** the parser returns it as a parsed dict
- **WHEN** an SSE event's data field is not valid JSON
- **THEN** the parser returns it as a raw string

### Requirement: Generic Capture Addon
The system SHALL provide a self-contained mitmproxy addon that logs request/response pairs to JSONL.

#### Scenario: Addon Is Self-Contained
- **WHEN** the capture addon is loaded by mitmdump via `-s`
- **THEN** it operates without importing from the `agent_system_dissect` package

#### Scenario: Output Path Via Environment Variable
- **WHEN** the environment variable `TRAFFIC_OUTPUT_DIR` is set
- **THEN** the addon writes to `$TRAFFIC_OUTPUT_DIR/traffic.jsonl`
- **WHEN** `TRAFFIC_OUTPUT_DIR` is not set
- **THEN** the addon writes to a default path relative to its own location
