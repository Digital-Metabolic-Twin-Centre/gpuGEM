# Feature Specification: Integrate cuOpt Skills into gpuGEM

**Feature Branch**: `001-cuopt-skills-integration`

**Created**: 2026-07-24

**Status**: Draft

**Input**: User description: "I want to add all the cuOpt skills documented at this repository to be added as a skill in the gpuGEM: https://github.com/NVIDIA/cuopt/blob/main/AGENTS.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Set up cuOpt numerical optimization (Priority: P1)

A developer wants to use cuOpt for linear programming (LP), mixed-integer linear programming (MILP), or quadratic programming (QP) problems through gpuGEM. They need clear documentation on how to formulate optimization problems using cuOpt and integrate them into their gpuGEM workflow.

**Why this priority**: This is the foundational use case for cuOpt integration. LP/MILP/QP are the core optimization types that cuOpt supports, and developers need guidance on problem formulation and API usage.

**Independent Test**: A developer can follow the documentation to set up and solve a simple LP problem using cuOpt through gpuGEM and verify the solution meets expected constraints.

**Acceptance Scenarios**:

1. **Given** a developer has cuOpt installed, **When** they reference the cuOpt numerical optimization skill, **Then** they can understand how to formulate LP, MILP, and QP problems
2. **Given** a developer follows the API documentation, **When** they call cuOpt through gpuGEM, **Then** their problem is correctly translated to cuOpt's input format
3. **Given** cuOpt returns a solution, **When** a developer inspects the result, **Then** they can understand the solution status and feasibility diagnostics (per gpuGEM's constitution)

---

### User Story 2 - Deploy and interact with cuOpt server (Priority: P2)

A team wants to deploy cuOpt as a service and build client applications that interact with it. They need documentation on server installation, configuration, and how to write client code that communicates with the cuOpt server API.

**Why this priority**: Server deployment is critical for scalable, production-grade optimization workflows. This enables teams to decouple client applications from the optimization engine.

**Independent Test**: A developer can follow the cuOpt server setup documentation and successfully deploy a server, then verify a client can submit and retrieve optimization results.

**Acceptance Scenarios**:

1. **Given** a developer wants to deploy cuOpt as a service, **When** they follow the server installation skill, **Then** they can configure and start a cuOpt server in Python or other environments
2. **Given** a cuOpt server is running, **When** a client submits an optimization request, **Then** the server processes it and returns results
3. **Given** team members need to interact with the server, **When** they reference the server API documentation, **Then** they understand the communication protocol and payload formats

---

### User Story 3 - Solve routing optimization problems (Priority: P3)

A logistics application developer wants to use cuOpt for vehicle routing, pickup-delivery, or other routing-related optimization. They need guidance on how to model routing problems and use cuOpt's routing-specific capabilities.

**Why this priority**: Routing is a specialized optimization domain with its own formulation patterns. It's valuable for supply chain, logistics, and fleet management applications.

**Independent Test**: A developer can follow the routing API documentation to model a simple vehicle routing problem and obtain an optimized route.

**Acceptance Scenarios**:

1. **Given** a developer has a routing problem to solve, **When** they reference the cuOpt routing skill, **Then** they understand how to specify locations, vehicle constraints, and cost objectives
2. **Given** a routing problem is formulated, **When** they call the cuOpt routing API, **Then** the solution includes optimized routes and metrics (time, distance, cost)

---

### User Story 4 - Explore multi-objective optimization tradeoffs (Priority: P4)

A researcher or engineer wants to understand tradeoffs between multiple competing objectives (e.g., cost vs. delivery time). They need documentation on Pareto frontier analysis and multi-objective optimization concepts.

**Why this priority**: Multi-objective optimization is an advanced use case. It adds value for sophisticated applications but is less critical than single-objective setup for initial adoption.

**Independent Test**: A developer can follow the multi-objective exploration skill to set up a problem with competing objectives and extract the Pareto frontier.

**Acceptance Scenarios**:

1. **Given** a problem has multiple objectives, **When** a developer reads the multi-objective skill, **Then** they understand Pareto optimality and tradeoff visualization concepts
2. **Given** cuOpt returns a Pareto frontier, **When** a developer inspects the results, **Then** they can extract and analyze non-dominated solutions

---

### Edge Cases

- What happens when cuOpt is not installed? (Installation guidance should be clear)
- How does gpuGEM handle solver failures or infeasibility from cuOpt? (Feasibility diagnostics must be reported per constitution)
- How are numerical tolerances and scaling handled when cuOpt integrates with gpuGEM? (Must align with gpuGEM's defaults)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A gpuGEM skill MUST be created that documents cuOpt's rules for end users, covering routing, LP, MILP, QP, installation, and server deployment scenarios
- **FR-002**: A skill MUST provide installation instructions for cuOpt in Python, C, and server environments
- **FR-003**: A skill MUST document the cuOpt numerical optimization API (LP, MILP, QP) with examples for Python, C, and CLI interfaces
- **FR-004**: A skill MUST document the Python routing API with examples of how to model and solve vehicle routing problems
- **FR-005**: A skill MUST document the cuOpt server API and deployment workflow for building client-server optimization applications
- **FR-006**: A skill MUST explain multi-objective optimization and Pareto frontier analysis concepts in the context of cuOpt
- **FR-007**: A skill MUST document cuOpt developer workflows for contributors who want to modify or extend cuOpt internals
- **FR-008**: Skills MUST include guidance on how cuOpt integrates with gpuGEM's correctness principles (feasibility reporting, status validation)
- **FR-009**: All skills MUST include practical, runnable examples where feasible
- **FR-010**: Skills documentation MUST reference cuOpt's official documentation and link to the NVIDIA cuOpt repository

### Key Entities

- **cuOpt Skill**: A reusable knowledge module covering a specific cuOpt capability (e.g., installation, routing API)
- **Problem Formulation**: The structured definition of an optimization problem (objective, constraints, variables)
- **Solution Result**: The output from an optimizer including status, solution values, and feasibility diagnostics
- **Pareto Frontier**: The set of non-dominated solutions for multi-objective problems

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At least 8 cuOpt skills are documented and integrated into gpuGEM, covering all areas mentioned in the cuOpt AGENTS.md file
- **SC-002**: Each skill includes at least one runnable example that a developer can use to understand the concept
- **SC-003**: A developer new to cuOpt can successfully set up and solve an LP problem within 15 minutes by following the documentation
- **SC-004**: A developer can deploy a cuOpt server and build a client application following the server skill documentation within 30 minutes
- **SC-005**: 100% of cuOpt documentation references in the skills link to authoritative sources (cuOpt GitHub or official docs)
- **SC-006**: Skill documentation follows gpuGEM's constitution principles: correctness-validated, honest status reporting, and minimal public API surface

## Assumptions

- cuOpt is already installed and available as a dependency (installation guidance is within scope of the skills)
- Developers using these skills have basic optimization knowledge or are willing to learn from provided resources
- The cuOpt AGENTS.md file represents the current authoritative list of cuOpt capabilities (this was fetched as the source of truth)
- Skills will be implemented as markdown documentation files within the Claude Code skills system
- Skills documentation should be platform-agnostic but may include Python-specific examples (since gpuGEM is Python-based)
- Security and authentication for cuOpt server are documented but responsibility for production hardening lies with the deployer
