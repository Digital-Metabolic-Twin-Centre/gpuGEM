# Implementation Plan: Integrate cuOpt Skills into gpuGEM

**Branch**: `001-cuopt-skills-integration` | **Date**: 2026-07-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-cuopt-skills-integration/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Create 8+ Claude Code skills that document cuOpt's optimization capabilities (LP, MILP, QP, routing, multi-objective, server deployment) and their integration with gpuGEM. Skills will be delivered as markdown documentation files in `.claude/skills/cuopt-*` directories, each following a consistent template with conceptual explanations, API references, runnable examples, and best practices. The deliverable prioritizes developer onboarding (15–30 min to productive use) while maintaining alignment with gpuGEM's correctness-first principles.

## Technical Context

**Language/Version**: Python 3.10+ (gpuGEM floor; cuOpt supports Python 3.8+, so no version conflict)

**Primary Dependencies**: 
- cuOpt (optimization engine being documented)
- Claude Code skills framework (delivery platform)
- gpuGEM (host project context)

**Storage**: N/A (documentation deliverable)

**Testing**: Skill validation (examples must execute successfully; API references must match cuOpt versions)

**Target Platform**: Claude Code (integrated IDE plugin, web, CLI, desktop)

**Project Type**: Educational documentation & developer skills for Claude Code platform

**Performance Goals**: N/A (documentation; focused on learning velocity: developers productive in 15–30 min per user story)

**Constraints**: 
- Skills must not leak implementation details into documentation (conceptual focus per gpuGEM constitution)
- cuOpt examples must produce feasible, validated solutions (per gpuGEM's correctness principle)
- Documentation must reference authoritative cuOpt sources (GitHub, official docs)

**Scale/Scope**: 8+ skills covering all cuOpt AGENTS.md categories; ~10–50 LOC examples per skill

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Applicable Principles** (from gpuGEM constitution v1.0.0):

1. **Correctness-Validated Defaults** (NON-NEGOTIABLE): Not directly applicable (this feature documents cuOpt, not gpuGEM defaults). However, any cuOpt examples involving solver setup must produce verified, feasible solutions.

2. **Honest Status and Feasibility Reporting**: All cuOpt solver examples must demonstrate solution validation (status inspection, residual bounds, feasibility diagnostics). Skills must not hide or downplay cuOpt's known numerical issues (e.g., PaPILO hardcoded `feastol`, broken warm-start API — per Known Limitations).

3. **Test Coverage for Numerical Behavior**: All solver-facing examples in skills must be validated to produce correct results before shipping. Examples with wrong solutions must be caught and fixed.

4. **Minimal, COBRA-Compatible Surface**: Skills documentation must reinforce that gpuGEM wraps cuOpt thinly and stays COBRA-compatible. Documentation should not encourage users to bypass gpuGEM's validation layer.

5. **Documented Known Limitations**: Any cuOpt limitation discovered during skill development (tolerance issues, solver bugs, unsupported features) must be recorded in the skill's "Known Limitations" section.

**Constitution Check Result**: ✅ PASS (with conditions)
- Condition 1: All solver examples must include solution validation code.
- Condition 2: Skills must document cuOpt's known limitations (per cuOpt's official docs).
- Condition 3: No examples should contradict gpuGEM's thin-wrapper philosophy or correctness principles.

## Project Structure

### Feature Documentation (this feature - specs/001-cuopt-skills-integration/)

```text
specs/001-cuopt-skills-integration/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output: cuOpt capability matrix, API reference findings
├── data-model.md        # Phase 1 output: cuOpt skill template & structure
├── quickstart.md        # Phase 1 output: skill validation & usage guide
├── contracts/
│   └── skill-template.md      # Canonical template for all cuOpt skills
└── tasks.md             # Phase 2 output (/speckit-tasks command)
```

### Deliverable: Claude Code Skills (repository root)

```text
.claude/skills/
├── cuopt-user-rules/
│   ├── SKILL.md              # End-user guidelines (routing, LP, MILP, QP, install, server)
│   └── examples/
│       ├── lp-setup.py       # Example: Linear programming setup
│       ├── routing-example.py # Example: Vehicle routing
│       └── server-client.py   # Example: Server client interaction
├── cuopt-numerical-optimization-formulation/
│   ├── SKILL.md              # Conceptual guide to LP, MILP, QP
│   └── examples/
├── cuopt-numerical-optimization-api/
│   ├── SKILL.md              # API reference for LP, MILP, QP
│   └── examples/
├── cuopt-routing-api-python/
│   ├── SKILL.md              # Routing API guide
│   └── examples/
├── cuopt-server-api-python/
│   ├── SKILL.md              # Server deployment & client guide
│   └── examples/
├── cuopt-multi-objective-exploration/
│   ├── SKILL.md              # Pareto frontier & multi-objective concepts
│   └── examples/
├── cuopt-install/
│   ├── SKILL.md              # Installation for Python, C, server
│   └── examples/
└── cuopt-developer/
    ├── SKILL.md              # Developer workflow & contributing
    └── examples/
```

**Structure Decision**: Skills are organized by cuOpt AGENTS.md categories (one skill per major capability area). Each skill directory contains:
- `SKILL.md`: The skill content (conceptual explanation, API reference, examples, known limitations)
- `examples/`: Executable Python scripts demonstrating the skill in context
- All skills follow the canonical template defined in `contracts/skill-template.md`

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
