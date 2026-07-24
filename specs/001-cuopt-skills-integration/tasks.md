---
description: "Implementation tasks for cuOpt Skills integration into gpuGEM"
---

# Tasks: Integrate cuOpt Skills into gpuGEM

**Input**: Design documents from `/specs/001-cuopt-skills-integration/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/skill-template.md

**Tests**: Validation tasks included (quickstart.md scenarios); unit tests are not included (documentation skills are tested via example execution)

**Organization**: Tasks are grouped by user story to enable independent development and testing of each skill set

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different skill directories, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- Skills directory: `.claude/skills/cuopt-*/`
- Each skill: `SKILL.md` (main documentation) + `examples/` (code samples)
- Spec directory: `specs/001-cuopt-skills-integration/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize skill directory structure and infrastructure

- [x] T001 Create `.claude/skills/cuopt-*` directory structure for 8 skills
- [x] T002 Copy contracts/skill-template.md to `.claude/skills/SKILL_TEMPLATE.md` for reference
- [x] T003 Create validation script at `specs/001-cuopt-skills-integration/validate-skills.sh` to test all examples

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core skill infrastructure and shared reference materials

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Create cuopt-user-rules skill directory at `.claude/skills/cuopt-user-rules/`
- [x] T005 Create cuOpt capability reference document at `specs/001-cuopt-skills-integration/cuopt-reference.md` (versions, APIs, limitations)
- [x] T006 Setup example validation infrastructure (Python script to run and verify all skill examples)

**Checkpoint**: Foundation ready - skill development can now begin

---

## Phase 3: User Story 1 - Set up cuOpt numerical optimization (Priority: P1) 🎯 MVP

**Goal**: Developers can install cuOpt and understand LP/MILP/QP problem formulation, then write and run their first optimization code

**Independent Test**: Follow quickstart.md "Skill 1-2" validation path (install → formulation → API) and successfully run example LP solver

### Implementation for User Story 1

- [x] T007 [P] [US1] Create `cuopt-install` skill at `.claude/skills/cuopt-install/SKILL.md` (Python, C, server installation instructions)
- [x] T008 [P] [US1] Create installation examples at `.claude/skills/cuopt-install/examples/` (setup-python.sh, verify-install.py)
- [x] T009 [P] [US1] Create `cuopt-numerical-optimization-formulation` skill at `.claude/skills/cuopt-numerical-optimization-formulation/SKILL.md` (LP/MILP/QP concepts)
- [x] T010 [P] [US1] Create formulation examples at `.claude/skills/cuopt-numerical-optimization-formulation/examples/` (lp-vs-milp.md, constraint-types.md)
- [x] T011 [US1] Create `cuopt-numerical-optimization-api` skill at `.claude/skills/cuopt-numerical-optimization-api/SKILL.md` (LP, MILP, QP API reference)
- [x] T012 [P] [US1] Create LP example in `.claude/skills/cuopt-numerical-optimization-api/examples/simple-lp.py` (complete, runnable, includes result validation)
- [x] T013 [P] [US1] Create MILP example in `.claude/skills/cuopt-numerical-optimization-api/examples/simple-milp.py` (branching, integer variables, result validation)
- [x] T014 [P] [US1] Create QP example in `.claude/skills/cuopt-numerical-optimization-api/examples/simple-qp.py` (quadratic objective, result validation)
- [x] T015 [US1] Validate all US1 examples run successfully and produce correct feasible solutions

**Checkpoint**: User Story 1 complete - developers can install cuOpt and solve LP/MILP/QP problems

---

## Phase 4: User Story 2 - Deploy and interact with cuOpt server (Priority: P2)

**Goal**: Teams can deploy cuOpt as a remote service and build client applications that communicate with it

**Independent Test**: Follow quickstart.md "Skill 3" validation path - start server, run client, receive results

### Implementation for User Story 2

- [x] T016 [P] [US2] Create `cuopt-server-api-python` skill at `.claude/skills/cuopt-server-api-python/SKILL.md` (server deployment, client API, communication protocols)
- [x] T017 [P] [US2] Create server setup example in `.claude/skills/cuopt-server-api-python/examples/server-setup.sh` (docker or direct install, environment config)
- [x] T018 [P] [US2] Create client example in `.claude/skills/cuopt-server-api-python/examples/client-example.py` (HTTP POST, problem submission, result retrieval, includes validation)
- [x] T019 [P] [US2] Create polling pattern example in `.claude/skills/cuopt-server-api-python/examples/client-polling.py` (async result retrieval)
- [x] T020 [US2] Add "Common Patterns" section to server skill covering authentication, error handling, connection timeouts (reference gpuGEM constitution)
- [x] T021 [US2] Validate US2 examples: server can start, client can submit and retrieve results

**Checkpoint**: User Story 2 complete - production server deployment is documented and validated

---

## Phase 5: User Story 3 - Solve routing optimization problems (Priority: P3)

**Goal**: Logistics developers can model vehicle routing, pickup-delivery, and other routing problems using cuOpt's specialized APIs

**Independent Test**: Follow quickstart.md reference - model simple VRP, obtain optimized routes with metrics

### Implementation for User Story 3

- [x] T022 [P] [US3] Create `cuopt-routing-api-python` skill at `.claude/skills/cuopt-routing-api-python/SKILL.md` (vehicle routing, pickup-delivery, cost objectives, constraints)
- [x] T023 [P] [US3] Create basic VRP example in `.claude/skills/cuopt-routing-api-python/examples/simple-vrp.py` (locations, vehicles, objective, includes result validation)
- [x] T024 [P] [US3] Create pickup-delivery example in `.claude/skills/cuopt-routing-api-python/examples/pdvrp-example.py` (order constraints, time windows if supported, result validation)
- [x] T025 [P] [US3] Create multi-objective routing example in `.claude/skills/cuopt-routing-api-python/examples/multi-cost-routing.py` (distance + time + cost, includes solution extraction)
- [x] T026 [US3] Add "Common Patterns" to routing skill (time windows, capacity constraints, penalty handling)
- [x] T027 [US3] Validate US3 examples: VRP solves, routes are valid and feasible

**Checkpoint**: User Story 3 complete - routing problems can be solved via cuOpt

---

## Phase 6: User Story 4 - Explore multi-objective optimization tradeoffs (Priority: P4)

**Goal**: Researchers and engineers can extract and analyze Pareto frontiers for multi-objective problems

**Independent Test**: Create 2-objective problem, extract Pareto frontier, demonstrate solution tradeoffs

### Implementation for User Story 4

- [x] T028 [P] [US4] Create `cuopt-multi-objective-exploration` skill at `.claude/skills/cuopt-multi-objective-exploration/SKILL.md` (Pareto frontier, pareto dominance, solution extraction)
- [x] T029 [P] [US4] Create multi-objective example in `.claude/skills/cuopt-multi-objective-exploration/examples/pareto-frontier.py` (2 objectives, extract non-dominated solutions, includes result validation)
- [x] T030 [P] [US4] Create tradeoff visualization example in `.claude/skills/cuopt-multi-objective-exploration/examples/visualize-tradeoff.py` (matplotlib or plotly, 2D Pareto plot, solution comparison)
- [x] T031 [US4] Add "Known Limitations" to multi-objective skill (solver limitations on 3+ objectives, reference cuOpt docs)
- [x] T032 [US4] Validate US4 examples: Pareto frontier extraction works, tradeoffs are correctly visualized

**Checkpoint**: User Story 4 complete - multi-objective optimization is documented and validated

---

## Phase 7: Advanced & Developer Workflows (Priority: P5+)

**Goal**: Developers contributing to or extending cuOpt have guidance on development workflows and architecture

### Implementation for Advanced Skills

- [x] T033 [P] Create `cuopt-developer` skill at `.claude/skills/cuopt-developer/SKILL.md` (contributing to cuOpt, development environment setup, code style)
- [ ] T034 [P] Create developer example in `.claude/skills/cuopt-developer/examples/build-cuopt-from-source.sh` (clone, build, verify)
- [ ] T035 [US1-4] Audit all user story 1-4 skills for consistency: same heading hierarchy, terminology, formatting across all skills

**Checkpoint**: Developer support and consistency validation complete

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting all skills, final validation, and documentation

- [ ] T036 [P] Review and update all "Known Limitations" sections across all 8 skills against current cuOpt/gpuGEM documentation
- [ ] T036 [P] Add "See Also" sections to all skills linking to related skills (e.g., API skill links to server skill)
- [ ] T037 [P] Validate cross-skill terminology consistency (use glossary from data-model.md)
- [ ] T038 Create integration example in `.claude/skills/cuopt-user-rules/examples/gpuGEM-integration.py` showing how to use cuOpt through gpuGEM's solve_cobra() with result validation
- [ ] T039 Run full validation: Execute `validate-skills.sh` to confirm all 8+ skills and examples are correct and complete
- [ ] T040 Update `.claude/skills/README.md` to list all 8 cuOpt skills and their prerequisites (learning path from research.md)
- [ ] T041 [P] Run quickstart.md validation scenarios (Skill 1 → 3 paths for each user story)
- [ ] T042 Final review: Ensure all skills follow canonical template from contracts/skill-template.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P4)
  - Each story is independently testable and deployable
- **Advanced (Phase 7)**: Can start after Foundational or in parallel with user stories
- **Polish (Phase 8)**: Depends on all user stories being draft-complete (not blocked by polish)

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational - Independent of US1 (different skill set, different deployment model)
- **User Story 3 (P3)**: Can start after Foundational - Independent of US1-2 (specialized routing domain)
- **User Story 4 (P4)**: Can start after Foundational - Independent of US1-3 (advanced optimization concepts)

### Within Each User Story

- Skills must be created in dependency order (concepts before API, API before examples)
- Examples must be validated before story completion
- Later stories can cross-reference earlier skills but should be independently complete

### Parallel Opportunities (per Phase)

**Phase 1**:
- All directory creation tasks [P] can run in parallel

**Phase 2**:
- Reference doc creation [P] can run in parallel
- Validation infrastructure setup [P] can run in parallel

**Phase 3 (US1)**:
- T007-T010: Skill creation [P] (different directories)
- T012-T014: Example creation [P] (different files)
- T015: Validation (depends on examples)

**Phase 4 (US2)**:
- T016-T019: Skill and example creation [P] (different directories/files)
- T021: Validation (depends on examples)

**Phase 5 (US3)**:
- T022-T025: Skill and example creation [P]
- T027: Validation

**Phase 6 (US4)**:
- T028-T031: Skill and example creation [P]
- T032: Validation

**Phase 7**:
- T033-T034: Developer skill [P]
- T035: Consistency audit (depends on US1-4 completion)

**Phase 8**:
- T036-T037: Cross-cutting reviews [P]
- T038-T042: Validation and documentation (can run in parallel until final checks)

---

## Parallel Example: User Story 1 (P1)

```bash
# Start all US1 skill creation in parallel (different directories):
Task T007: Create cuopt-install skill
Task T008: Create install examples
Task T009: Create cuopt-numerical-optimization-formulation skill
Task T010: Create formulation examples

# Once T007-T010 complete, start example creation in parallel:
Task T012: Create LP example
Task T013: Create MILP example
Task T014: Create QP example

# After examples complete:
Task T015: Validate all US1 examples
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

**Timeline**: 2-3 weeks for one developer

1. Complete Phase 1: Setup (1 day)
2. Complete Phase 2: Foundational (1-2 days)
3. Complete Phase 3: User Story 1 (5-7 days: 3 skills + 3 examples + validation)
4. **STOP and VALIDATE**: Confirm users can follow quickstart.md US1 path
5. Deploy/demo US1 to team

**Deliverable**: cuOpt installation and basic LP/MILP/QP solving documented and validated

### Incremental Delivery

**Timeline**: 8-10 weeks for one developer

1. Weeks 1-2: Setup + Foundational → Foundation ready
2. Weeks 2-4: US1 (P1) → Validate independently → Deploy
3. Weeks 4-6: US2 (P2) → Validate independently → Deploy
4. Weeks 6-8: US3 (P3) → Validate independently → Deploy
5. Weeks 8-10: US4 (P4) + Polish → Final validation → Deploy all

**Deliverable**: All 8 skills complete, validated, and integrated into Claude Code

### Parallel Team Strategy

**Timeline**: 3-4 weeks with 2-3 developers

1. Week 1: All complete Setup + Foundational
2. Weeks 2-3:
   - Developer A: US1 (install, formulation, API)
   - Developer B: US2 (server deployment)
   - Developer C: US3-4 (routing, multi-objective)
3. Week 4: All converge on US3-4 completion, Polish, and final validation

**Deliverable**: All skills complete in 4 weeks

---

## Validation Checkpoints

- **After T015 (US1)**: Developers can install cuOpt and run LP/MILP/QP solvers
- **After T021 (US2)**: cuOpt server can be deployed and clients can submit problems
- **After T027 (US3)**: Vehicle routing problems can be solved with cuOpt
- **After T032 (US4)**: Pareto frontiers can be extracted and analyzed
- **After T042 (Final)**: All skills pass quickstart.md validation scenarios; ready for production

---

## Notes & Constraints

- [P] tasks = different directories/files, no inter-task dependencies
- [Story] label = traceability to user stories from spec.md
- Each user story is independently completable, testable, and deployable
- Examples must include solution validation (per gpuGEM constitution)
- No example outputs should be non-deterministic
- All examples must run in <30 seconds
- Skills must not leak implementation details (conceptual focus)
- Cross-references between skills should use relative links in `.claude/skills/` tree
- Commit after each user story phase (3+ commits total for MVP, 5+ for full feature)
