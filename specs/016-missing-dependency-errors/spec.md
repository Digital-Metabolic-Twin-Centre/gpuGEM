# Feature Specification: Missing-Dependency Error Handling

**Feature Branch**: `016-missing-dependency-errors`

**Created**: 2026-10-05

**Status**: Draft

**Input**: User description: "double check every code and make sure in the case of an independency not exist on a machine it outputs a proper error and increase the error handling coverage and guide the user how to solve or install the dependency"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Library user without the GPU solver (Priority: P1)

A researcher installs gpuGEM on a machine where the GPU solver package is absent, mismatched with the installed CUDA runtime, or cannot see a GPU, and calls `gpugem.solve` or `gpugem.solve_cobra`. Today this surfaces as a raw import failure or a low-level driver error with no hint about the cause.

**Why this priority**: The solver is the one hard dependency and the core of the product; every user hits this path first.

**Independent Test**: Run the public solve entry points in an environment where the solver package is hidden, and in one where it is present but no GPU is visible. Confirm each yields a single clear error naming the missing piece and giving a concrete remedy.

**Acceptance Scenarios**:

1. **Given** the solver package is not installed, **When** the user calls a solve function, **Then** a dedicated, catchable error is raised stating the package is missing, why it is needed, and the exact install command.
2. **Given** the solver package is installed but no compatible GPU or driver is detected, **When** the user calls a solve function, **Then** the error says a GPU/driver problem was detected (not a missing package) and points to driver/CUDA-version checks.
3. **Given** the installed solver version is older than the minimum supported, **When** the user calls a solve function, **Then** the error states installed vs. required version and the upgrade command.
4. **Given** all dependencies are present, **When** the user calls a solve function, **Then** behaviour and results are unchanged.

---

### User Story 2 - Optional COBRA / file-format dependencies (Priority: P2)

A user calls `solve_cobra`, `loaders.from_cobra`, or a model loader for a file format without the optional COBRA package (or a required reader) installed.

**Why this priority**: Optional dependencies are the most common "works on my colleague's machine" failure.

**Independent Test**: Hide the optional package and call each affected public function; each must raise the same style of guided error naming the optional extra to install.

**Acceptance Scenarios**:

1. **Given** the COBRA package is absent, **When** the user calls any function needing it, **Then** the error names the package and the install command for the matching optional extra.
2. **Given** the user loads a model file whose reader is unavailable, **When** loading fails, **Then** the error names the format and the missing reader rather than a raw traceback.

---

### User Story 3 - Benchmark and tooling users (Priority: P3)

A contributor runs a benchmark or helper script that needs a comparison solver, plotting/data library, GPU-inspection tool, MATLAB, or network access to download models, and one of these is missing.

**Why this priority**: Affects contributors, not end users, but silent skips or tracebacks here have produced misleading or incomplete benchmark results.

**Independent Test**: Run each script with each of its external dependencies hidden in turn; every script must exit non-zero up front with a guided message, or — where a dependency is genuinely optional — record in its output that the step was skipped and why.

**Acceptance Scenarios**:

1. **Given** a script requires a missing comparison solver, **When** it starts, **Then** it exits non-zero before doing work, naming the dependency and install command.
2. **Given** a dependency is optional for informational metadata only (e.g. GPU name), **When** it is missing, **Then** the script continues and records the field as unavailable with the reason, rather than swallowing the failure silently.
3. **Given** a licensed dependency is installed but unlicensed or unreachable, **When** the script starts, **Then** the message distinguishes this from "not installed".

---

### User Story 4 - Verifiable coverage (Priority: P2)

A maintainer wants assurance that no dependency-failure path was missed and that none regresses.

**Why this priority**: The request is to "double check every code"; without an inventory and tests the work cannot be shown complete.

**Independent Test**: Review the dependency inventory against a repo-wide search for external imports and tool invocations; run the test suite on a machine that lacks the GPU stack.

**Acceptance Scenarios**:

1. **Given** the repository, **When** the inventory is compared with every external import and external-tool call in package, benchmark and example code, **Then** each has a documented outcome (guided error, deliberate skip with recorded reason, or justified exemption) and none is unaccounted for.
2. **Given** any dependency is simulated as missing, **When** the corresponding test runs, **Then** it asserts the error type and that the message contains the remedy; the test fails if the message regresses to a raw traceback.
3. **Given** a machine without the GPU stack, **When** the test suite runs, **Then** dependency-error tests pass without a GPU, and GPU-dependent tests are reported as unrun, not passed.

---

### Edge Cases

- Dependency present but broken at import time (binary mismatch, missing shared library): must be reported as broken, with the underlying cause preserved, not as "not installed".
- Dependency present but too old or too new: version message must state both versions.
- Dependency missing inside a worker subprocess: the parent run must surface the child's guided message, not only a generic non-zero exit.
- Importing the package itself must not fail merely because the solver is missing, so that non-solving utilities (loaders, scaling, lifting) remain usable and the error appears only when a solve is requested.
- Offline machine when a model must be downloaded: message must say network access failed and where to place the file manually.
- Repeated calls: the check must not add noticeable overhead per solve.
- Error messages must not hide the original exception (chained cause remains available for debugging).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide one dedicated, documented error category for missing, broken, or incompatible dependencies, distinguishable by callers from ordinary solve failures.
- **FR-002**: Every error in that category MUST state (a) what is missing/broken, (b) why gpuGEM needs it, and (c) a concrete remedy (install/upgrade command, driver check, or environment fix).
- **FR-003**: The system MUST distinguish "not installed", "installed but fails to load", "version outside supported range", and "no GPU/driver available", each with its own remedy.
- **FR-004**: Calling any public solve entry point without the required solver MUST raise the guided error instead of a raw import or driver exception.
- **FR-005**: Importing the package MUST succeed without the solver installed; the guided error appears only when functionality needing it is invoked.
- **FR-006**: Functions needing an optional dependency MUST raise the guided error naming the optional extra to install.
- **FR-007**: Model loading MUST report unavailable readers and unreachable download sources with a guided message including a manual alternative.
- **FR-008**: Every benchmark, aggregation, figure and example script MUST either exit non-zero before doing work with a guided message, or skip a genuinely optional step while recording the skip and reason in its output; silent swallowing of dependency failures is prohibited.
- **FR-009**: External tools invoked as subprocesses (GPU inspection, MATLAB, package installers) MUST have their absence and failure handled with the same guided style.
- **FR-010**: Minimum supported versions MUST be stated in one place and the same values used by installation metadata, version checks, and documentation.
- **FR-011**: Original underlying exceptions MUST remain accessible on the raised error.
- **FR-012**: A maintained inventory of all external dependencies (required, optional, benchmark-only, tool-only) MUST list for each its failure mode and guided outcome, and be verified against a repo-wide search of imports and tool invocations.
- **FR-013**: Each inventory entry MUST be covered by an automated test that simulates the dependency being absent (and, where applicable, broken or too old) and asserts error category and remedy text.
- **FR-014**: README MUST document the dependencies, install commands, and troubleshooting for each error kind; any newly discovered limitation MUST be added to "Known limitations".
- **FR-015**: Successful-path numerical results and public API signatures MUST be unchanged.

### Key Entities

- **Dependency inventory entry**: name, role (required / optional / benchmark-only / tool-only), where used, minimum version, failure modes, guided remedy, covering test.
- **Dependency error**: category, dependency name, failure kind, detected vs. required version (if relevant), remedy text, chained cause.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For 100% of inventory entries, simulating the dependency as absent produces a message containing the dependency name and a remedy; zero raw import tracebacks reach the user as the final error.
- **SC-002**: A repo-wide search finds zero external imports or tool calls without an inventory entry.
- **SC-003**: A new user on a machine without the GPU stack can identify the fix from the error message alone, without searching elsewhere, in at least 9 of 10 trial cases across the four failure kinds.
- **SC-004**: The full test suite's dependency-error tests pass on a machine with no GPU and no optional packages, and GPU-only tests are reported as unrun.
- **SC-005**: Results of existing tests and benchmarks on a fully equipped machine are identical before and after the change.
- **SC-006**: No script silently continues after a failed dependency check: 0 occurrences of a dependency failure swallowed without either a non-zero exit or a recorded skip reason.

## Assumptions

- Scope covers the package, benchmark scripts, figure scripts, examples and tests in this repository; third-party packages' own internal messages are out of scope except where wrapped.
- "Dependency" includes Python packages, system tools (GPU inspection utility, MATLAB), GPU driver/CUDA runtime, solver licences, and network access for model download.
- The hard-dependency set stays as stated in project instructions (numeric stack and GPU solver); COBRA stays optional. No dependency is added or promoted.
- Guidance text is English, plain, and printable in a terminal; install commands target pip-based environments, with a pointer to the solver vendor's install documentation for CUDA-specific variants.
- This is error handling, not an algorithmic change (Principle VII does not apply). Principle VIII does not apply; no MATLAB↔Python translation is altered.
- The solver's own install instructions are available via the existing `cuopt-install` skill and are the source for remedy text on GPU/CUDA mismatches.
- Constitution Principles III and V apply: tests accompany changes to solver-facing modules, and new limitations are recorded in the README.
