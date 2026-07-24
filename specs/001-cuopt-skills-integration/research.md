# Research Findings: cuOpt Skills for gpuGEM

**Date**: 2026-07-24  
**Source**: NVIDIA cuOpt AGENTS.md + project context  
**Scope**: Capabilities, integration patterns, best practices for Claude Code skills

## 1. cuOpt Capability Matrix

### Optimization Problem Types

| Problem Type | Supported | API | Python? | C? | CLI? | Notes |
|--------------|-----------|-----|---------|----|----|-------|
| Linear Programming (LP) | ✓ | Native | ✓ | ✓ | ✓ | Core capability |
| Mixed-Integer LP (MILP) | ✓ | Native | ✓ | ✓ | ✓ | Combinatorial optimization |
| Quadratic Programming (QP) | ✓ | Native | ✓ | ✓ | ✓ | Convex QP support |
| Routing (VRP, PDVRP) | ✓ | High-level | ✓ | - | - | Python-first API |
| Multi-objective | ✓ | Via solvers | ✓ | ✓ | - | Pareto frontier extraction |

### Deployment Models

| Model | Use Case | Setup Complexity | Suggested For |
|-------|----------|-----------------|---------------|
| In-Process (Python API) | Single-machine, interactive | Low | Development, research, small-scale |
| Server (Remote) | Scalable, multi-client, production | Medium | Production services, team workflows |
| C API | High-performance, embedded | Medium | Performance-critical applications |
| CLI | Scripting, integration | Low | Batch processing, CI/CD pipelines |

### Installation Complexity

- **Python**: Straightforward via `pip install cuopt-cu12` (CUDA 12.x). Version-pinned to match GPU driver.
- **C**: Requires CUDA SDK; Linux primary support (Windows via WSL).
- **Server**: Docker container or direct installation; requires resource allocation (GPU access).

## 2. Integration with gpuGEM

### Thin-Wrapper Philosophy

cuOpt is GPU-accelerated but exposes raw solver behavior (status codes, tolerance violations). gpuGEM's constitution requires:

1. **Honest status reporting**: Don't map tolerance-violating solutions to "Optimal"
2. **Feasibility diagnostics**: Always compute stoichiometric residuals and bounds
3. **Known limitations transparency**: Document solver quirks (e.g., PaPILO hardcoded `feastol=1e-6`)

**Implication for skills**: Examples must include solution validation and demonstrate how to interpret gpuGEM result objects (which wrap cuOpt's output).

### API Alignment

gpuGEM exposes:
- `solve(model, solver="cuopt", ...)` → low-level interface
- `solve_cobra(model, solver="cuopt", ...)` → COBRA-compatible
- `FBASolver` class → persistent solver instance

Skills should reference these high-level APIs but also show cuOpt's native API for users who need direct access.

## 3. Known cuOpt Limitations

These must be documented in each relevant skill:

1. **PaPILO presolve**: Hardcoded feasibility tolerance of 1e-6 (tighter than many solvers). May declare problems infeasible that are actually feasible at looser tolerance.
2. **Warm-start API**: Broken in some versions; workaround required or documented as unsupported.
3. **QP solver**: Limited to convex QP; non-convex problems will error or timeout.
4. **Scaling**: No built-in scaling routine; manual scaling required for badly-conditioned problems.
5. **GPU memory**: Large models must fit GPU memory; no spillover to CPU.

## 4. Example Archetypes

Each skill should include 1–2 runnable examples following this pattern:

### Minimal Viable Example (LP)
```python
import cuopt
# Set up small LP
# Solve
# Inspect result (status, objective, solution)
# Check feasibility (residuals)
```

### Integration Example (with gpuGEM)
```python
import gpuGEM
from gpuGEM import solve_cobra
# Create COBRA model
result = solve_cobra(model, solver="cuopt")
# Demonstrate gpuGEM's feasibility validation
print(result.feasibility)
```

### Server Example
```python
# Server: cuopt-server --host 0.0.0.0 --port 5000
# Client: HTTP POST with problem JSON
# Retrieve result via polling or callback
```

## 5. Learning Path & Prioritization

Recommended skill order for new users:

1. **cuopt-install** — Get started (15 min)
2. **cuopt-numerical-optimization-formulation** — Learn LP/MILP/QP concepts (20 min)
3. **cuopt-numerical-optimization-api** — Write first solver code (20 min)
4. **cuopt-routing-api-python** (optional) — Specialized domain (15 min)
5. **cuopt-multi-objective-exploration** (advanced) — Tradeoff analysis (20 min)
6. **cuopt-server-api-python** (production) — Deploy at scale (30 min)

## 6. Skill Template Requirements

Each SKILL.md file must include:

- **Overview**: 1 para on what this covers
- **Prerequisites**: List of skills/knowledge needed
- **Concepts**: Explanation of key ideas (no code yet)
- **API Reference**: Methods, parameters, return types
- **Example**: Runnable code (10–50 LOC)
- **Common Patterns**: Tips & best practices
- **Known Limitations**: Link to cuOpt docs + gpuGEM-specific notes
- **Next Steps**: Pointer to related skills or advanced topics

## 7. Decision: cuOpt Version Support

**Decision**: Target cuOpt 0.4.x (latest stable as of research date) with version checks in examples.

**Rationale**: 
- Simplifies skill examples and maintenance
- Most recent version has bug fixes and feature completeness
- Can add version compat notes if cuOpt 0.3.x support needed later

**Implementation**:
- Examples include cuOpt version in requirements or via inline check
- Docs note which examples apply to which versions
- Known Limitations section references version-specific issues
