## ADDED Requirements

### Requirement: Dedicated FlashInfer Pixi Environment
The repository SHALL provide a dedicated Pixi environment named `flashinfer-dev` for FlashInfer development workflows, SHALL pin the CUDA target to 12.9 for this environment, SHALL keep existing environments usable without requiring FlashInfer-specific dependencies, and SHALL NOT modify dependency/channel/task definitions of existing environments (including `default` and `codex-build`) as part of creating `flashinfer-dev`.

#### Scenario: Create FlashInfer environment
- **WHEN** a contributor runs Pixi commands targeting the `flashinfer-dev` environment
- **THEN** Pixi resolves and creates an environment that includes the dependencies required for FlashInfer source installation and execution with CUDA 12.9 alignment

#### Scenario: Default workflows remain unaffected
- **WHEN** a contributor uses the `default` or `codex-build` environments
- **THEN** those workflows continue to operate without requiring activation of `flashinfer-dev`

#### Scenario: Existing environment definitions remain unchanged
- **WHEN** maintainers add or update the `flashinfer-dev` environment
- **THEN** environment definitions for `default` and other pre-existing environments are not modified as part of this change

#### Scenario: Solver conflict requires cross-environment changes
- **WHEN** dependency/channel constraints cannot be satisfied for `flashinfer-dev` without modifying `default` or other existing environments
- **THEN** the implementation process stops before modifying those environments and requests explicit developer direction on how to proceed

### Requirement: NVIDIA Channel Toolchain Policy
The repository SHALL configure `flashinfer-dev` so NVIDIA packages are sourced with `nvidia` channel priority over `conda-forge` for CUDA-related tooling, and SHALL include NVIDIA toolchain components needed for compile-and-run workflows.

#### Scenario: NVIDIA toolchain packages are available in environment
- **WHEN** a contributor activates or runs commands in `flashinfer-dev`
- **THEN** CUDA compile/runtime tooling from NVIDIA packages (such as `cuda-nvcc` and development/runtime CUDA libraries) is available from the Pixi-managed environment

#### Scenario: Channel priority prevents unintended CUDA package source drift
- **WHEN** Pixi resolves NVIDIA package dependencies for `flashinfer-dev`
- **THEN** the `nvidia` channel is preferred for those NVIDIA packages unless explicitly overridden by maintainers

### Requirement: Standardized FlashInfer Setup Tasks
The repository SHALL provide Pixi tasks under `flashinfer-dev` to execute FlashInfer setup and validation steps from the vendored path `extern/tracked/flashinfer`.

#### Scenario: Install vendored FlashInfer in editable mode
- **WHEN** a contributor runs the FlashInfer install task in `flashinfer-dev`
- **THEN** the task installs `extern/tracked/flashinfer` in editable mode via Pixi-managed dependency resolution from manifest declarations

#### Scenario: Verify FlashInfer CLI configuration
- **WHEN** a contributor runs the FlashInfer configuration check task
- **THEN** the task executes FlashInfer configuration reporting (for example `show-config`) and exposes toolchain/runtime metadata needed for debugging

#### Scenario: Optional artifact packages are included by default
- **WHEN** a contributor follows the standard `flashinfer-dev` setup flow
- **THEN** optional artifact packages `flashinfer-cubin` and `flashinfer-jit-cache` are installed without requiring a separate opt-in step

### Requirement: Pixi-Only Python Dependency Management
The repository SHALL manage FlashInfer-related Python dependencies through the Pixi manifest, and implementation for this change SHALL NEVER use direct `pip` or `python -m pip` install commands for environment provisioning tasks.

#### Scenario: Add a new PyPI dependency
- **WHEN** a maintainer needs an additional PyPI dependency for `flashinfer-dev`
- **THEN** the dependency is added to the Pixi manifest (for example under `pypi-dependencies`) and resolved through Pixi

#### Scenario: Provision without direct pip commands
- **WHEN** a contributor executes the documented `flashinfer-dev` setup flow
- **THEN** all dependency installation steps run through Pixi and do not invoke direct `pip` installation commands

### Requirement: Preflight and Smoke Validation
The repository SHALL provide a preflight validation task and a minimal GPU runtime smoke task for FlashInfer so contributors can confirm readiness before running larger workloads.

#### Scenario: Preflight fails fast on unsupported host
- **WHEN** required host/runtime conditions (such as GPU visibility or CUDA/PyTorch readiness) are not satisfied
- **THEN** the preflight task exits with a clear failure and actionable diagnostics

#### Scenario: Smoke test confirms runnable installation
- **WHEN** preflight and installation have succeeded on a supported host
- **THEN** the smoke task executes a minimal FlashInfer GPU operation and reports success

### Requirement: Contributor Workflow Documentation
The repository SHALL document the `flashinfer-dev` workflow and required command sequence in repository knowledge docs used by contributors.

#### Scenario: Contributor follows documented flow
- **WHEN** a contributor follows the documented `flashinfer-dev` commands
- **THEN** they can reproduce the intended setup and validation sequence without ad-hoc manual environment construction
