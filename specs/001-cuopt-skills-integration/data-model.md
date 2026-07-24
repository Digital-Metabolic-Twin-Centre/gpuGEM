# Data Model: cuOpt Skills Structure

**Date**: 2026-07-24  
**Scope**: Information structure and components of a cuOpt Claude Code skill  
**Validation**: All skills must conform to this model for consistency and maintainability

## 1. Core Entities

### Skill

**Represents**: A reusable knowledge module covering one cuOpt capability or workflow area.

**Structure**:
- **Name** (string): Unique identifier (e.g., "cuopt-numerical-optimization-api")
- **Title** (string): Human-readable title (e.g., "cuOpt Numerical Optimization API")
- **Category** (enum): One of [setup, concepts, api-reference, deployment, advanced]
- **Prerequisites** (array of strings): Skills or knowledge required before using this one
- **Difficulty** (enum): beginner | intermediate | advanced
- **Time** (integer, minutes): Estimated time to work through the skill
- **Contents** (object): See Skill Contents below
- **Examples** (array of Example objects): Code samples and walkthroughs
- **Status** (enum): draft | published
- **Version** (string): Semantic version (1.0.0 format)

### Skill Contents

**Represents**: The internal structure of a skill's documentation.

**Sections** (each mandatory unless noted):

1. **Overview** (mandatory)
   - 1–2 sentences on what the skill covers
   - Target audience (e.g., "for developers new to optimization")

2. **Concepts** (mandatory)
   - Explanation of key ideas without code
   - Examples: explain LP vs MILP, explain objective vs constraints
   - Visual aids or diagrams encouraged

3. **API Reference** (mandatory for API skills, optional for conceptual)
   - Methods/functions with signatures
   - Parameters (type, required/optional, description)
   - Return values (type, description)
   - Exceptions/error codes
   - Format: reference table or structured list

4. **Examples** (mandatory)
   - At least one complete, runnable example
   - See Example entity below

5. **Common Patterns** (mandatory)
   - Tips, best practices, anti-patterns
   - Problem/solution pairs (e.g., "What if my solver times out?")

6. **Known Limitations** (mandatory)
   - cuOpt-specific quirks or bugs
   - gpuGEM-specific constraints
   - Workarounds where applicable
   - Links to official cuOpt docs for severity/status

7. **Next Steps** (mandatory)
   - Links to follow-on skills (e.g., "Ready for routing? See cuopt-routing-api-python")
   - Advanced topics or related domains

### Example

**Represents**: A concrete code sample demonstrating skill concepts.

**Attributes**:
- **Title** (string): Short description (e.g., "Simple LP Setup")
- **Language** (string): Programming language (python, c, bash, etc.)
- **Code** (string, 10–50 LOC): Executable, runnable code
- **Expected Output** (string): What a user should see when running
- **Notes** (string, optional): Explanation of tricky lines or assumptions
- **Prerequisites** (array of strings): Tools/libraries needed
- **Runnable** (boolean): true if example is complete and can execute standalone

**Validation Rules**:
- Example code must be syntactically correct
- Example must be testable without external data downloads
- Any solver call must include result validation (status check, feasibility check)
- Example output must be reproducible (no non-deterministic elements)

### API Reference Entry

**Represents**: Documentation for a single cuOpt function or method.

**Attributes**:
- **Signature** (string): Function/method definition with parameters
- **Description** (string): What it does, 1–3 sentences
- **Parameters** (array of Parameter objects)
  - **Name** (string)
  - **Type** (string): Type annotation or description
  - **Required** (boolean)
  - **Description** (string)
- **Returns** (string): Type and description of return value
- **Raises** (array of Exception objects, optional)
  - **Exception** (string): Exception type or error code
  - **When** (string): Condition that triggers this exception
- **Example** (string, optional): Inline code snippet showing typical usage
- **See Also** (array of strings, optional): Related functions or skills

## 2. Relationships

### Skill Dependencies (Prerequisite Chain)

```
cuopt-install
  └─→ cuopt-numerical-optimization-formulation
       └─→ cuopt-numerical-optimization-api
            ├─→ cuopt-routing-api-python
            └─→ cuopt-multi-objective-exploration
       └─→ cuopt-server-api-python
```

- Skills may have multiple prerequisites
- Circular dependencies are forbidden
- All prerequisites must be documented

### Content Cross-References

- API Reference sections should link to relevant Examples
- Known Limitations should reference gpuGEM constitution sections
- Next Steps should link to dependent skills

## 3. State & Lifecycle

### Skill Lifecycle

```
draft
  ├─→ review (content reviewed by core team)
  ├─→ published (available to users)
  └─→ deprecated (phased out, link to replacement)
```

### Content Versioning

- Skills use semantic versioning (MAJOR.MINOR.PATCH)
- MAJOR: Breaking changes (API shift, new prerequisites)
- MINOR: New content added (new examples, clarifications)
- PATCH: Bug fixes, wording improvements
- All skills in this feature start at 1.0.0

## 4. Validation Rules

### Structural Validation

- [ ] All mandatory sections present in each skill
- [ ] No orphaned examples (all examples referenced from content)
- [ ] No circular skill dependencies
- [ ] All links (cross-references, external URLs) are valid

### Content Validation

- [ ] Examples are syntactically correct Python/C/etc.
- [ ] Every solver call in examples includes result validation
- [ ] No example output contradicts gpuGEM constitution
- [ ] Known Limitations references are current and accurate
- [ ] Concepts section is free of implementation details

### Consistency Validation

- [ ] All skills use same heading hierarchy and formatting
- [ ] Technical terminology is consistent across skills (glossary)
- [ ] No conflicting advice across skills
- [ ] Examples follow same code style (naming, formatting)

## 5. Glossary

**Canonical terms** used consistently across all skills:

| Term | Definition |
|------|-----------|
| **Problem Formulation** | The structured definition of an optimization problem (objective, constraints, variables, bounds) |
| **Solution Result** | The output from cuOpt including status, objective value, variable values, and feasibility diagnostics |
| **Solver Status** | The result state (Optimal, Suboptimal, Infeasible, Unbounded, TimeLimit) |
| **Feasibility Diagnostic** | Computed bounds (residuals, constraint violations) indicating how well a solution satisfies constraints |
| **Warm Start** | Providing initial variable values to the solver to speed convergence (may not work in all versions) |
| **Presolve** | Solver preprocessing to simplify the problem (e.g., PaPILO); may tighten or change tolerances |
| **Pareto Frontier** | The set of non-dominated solutions in a multi-objective problem (no solution strictly better in all objectives) |

## 6. Example: Instantiation of Data Model

### Skill: cuopt-numerical-optimization-api

- **Name**: cuopt-numerical-optimization-api
- **Title**: cuOpt Numerical Optimization API
- **Category**: api-reference
- **Prerequisites**: [cuopt-install, cuopt-numerical-optimization-formulation]
- **Difficulty**: intermediate
- **Time**: 20
- **Contents**: 
  - Overview: "Learn the core cuOpt Python API for LP, MILP, and QP."
  - Concepts: Problem formulation, status codes, tolerances
  - API Reference: solve(), Model(), Variable(), Constraint(), ...
  - Examples:
    - SimpleLP (10 LOC, covers basic LP)
    - MILPWithBranching (20 LOC, covers MILP specifics)
  - Common Patterns: Handling infeasibility, scaling badly-conditioned problems
  - Known Limitations: PaPILO 1e-6 tolerance, no warm-start (if version affected)
  - Next Steps: cuopt-routing-api-python, cuopt-server-api-python
- **Examples**:
  - Example(Title="Simple LP", Language="python", Code="...", Runnable=true)
- **Status**: draft (will be published after Phase 1)
- **Version**: 1.0.0
