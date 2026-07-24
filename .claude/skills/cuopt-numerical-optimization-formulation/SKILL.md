# cuOpt Numerical Optimization Fundamentals

> **Skill ID**: `cuopt-numerical-optimization-formulation`  
> **Category**: concepts  
> **Difficulty**: beginner  
> **Time**: 20 minutes  
> **Prerequisites**: `cuopt-install`

---

## Overview

Understand the mathematical foundations of optimization problems that cuOpt solves: Linear Programming, Mixed-Integer Linear Programming, and Quadratic Programming. Learn to recognize problem structures and formulate them for cuOpt.

**Target Audience**: Developers new to optimization who need to understand problem formulation before writing solver code

---

## Concepts

### What is Linear Programming (LP)?

A Linear Programming problem has:

**Objective**: Minimize or maximize a linear function
```
minimize: c₁x₁ + c₂x₂ + ... + cₙxₙ
```

**Constraints**: Linear inequalities and equalities
```
a₁₁x₁ + a₁₂x₂ + ... ≤ b₁
a₂₁x₁ + a₂₂x₂ + ... = b₂
xᵢ ≥ 0 (or other bounds)
```

**Example**: Production planning
- Maximize: profit = 3×chairs + 5×tables
- Subject to: labor ≤ 40 hours, wood ≤ 100 boards, etc.

### What is Mixed-Integer Linear Programming (MILP)?

MILP extends LP by allowing **integer variables**:

```
minimize: 3x + 5y  (linear objective)
subject to:
  x + y ≤ 10      (linear constraint)
  x ≥ 0, y ≥ 0
  x is integer    (INTEGER CONSTRAINT)
```

**Why integers matter**: Model discrete decisions
- x = number of production batches (can't produce 2.7 batches)
- y = whether to open a facility (0 = no, 1 = yes)
- z = assignment (which truck to route)

**Complexity**: MILP is NP-hard (exponentially harder than LP), but GPU acceleration helps

### What is Quadratic Programming (QP)?

QP allows **quadratic terms** in the objective:

```
minimize: x² + 2xy + 3y² + x + 2y  (quadratic objective)
subject to:
  x + y ≤ 10     (still linear constraints)
  x, y ≥ 0
```

**Use cases**:
- Regression: Minimize sum of squared errors
- Portfolio optimization: Minimize portfolio variance
- Quadratic penalties: Minimize distance to some point

**cuOpt support**: Convex QP only (solver may not handle non-convex)

---

### Key Terminology

| Term | Meaning |
|------|---------|
| **Objective** | Function to minimize or maximize (profit, cost, time) |
| **Constraint** | Requirement that must be satisfied (capacity, budget, time window) |
| **Decision Variable** | Unknown value to determine (quantity, assignment, yes/no) |
| **Feasible Solution** | Any solution satisfying all constraints |
| **Optimal Solution** | Feasible solution with best objective value |
| **Infeasible** | No solution satisfies all constraints |
| **Unbounded** | Objective can be improved indefinitely (constraint error) |

---

## How to Recognize Problem Types

### Is it an LP problem?

✓ All relationships are linear (no x², xy, √x, etc.)
✓ Continuous variables (can be fractional)
✓ Single objective
✓ Examples: blending, scheduling, network flow, resource allocation

**→ Use LP solver in cuOpt**

### Is it a MILP problem?

✓ Linear relationships (like LP)
✓ Some variables must be integers (batches, yes/no decisions, counts)
✓ Examples: vehicle routing, facility location, production scheduling, crew assignment

**→ Use MILP solver in cuOpt**

### Is it a QP problem?

✓ Quadratic objective (x², xy terms)
✓ Linear constraints
✓ Examples: least squares, portfolio optimization, regression

**→ Use QP solver in cuOpt**

---

## Problem Formulation Checklist

Before writing code, ask:

1. **What are we optimizing?** (profit, cost, time, distance)
2. **What are the constraints?** (capacity, budget, time, rules)
3. **What are decision variables?** (quantities, assignments, yes/no)
4. **Are variables continuous or integer?**
5. **Is the objective linear or quadratic?**
6. **Can we express everything mathematically?**

---

## Common Patterns

### Pattern 1: Production/Blending Problems

**Goal**: Maximize profit subject to resource limits

```
Products: chairs (profit $3), tables (profit $5)
Resources: 40 labor hours, 100 wood units
Requirements: chair needs 2 labor + 4 wood; table needs 3 labor + 8 wood

Formulation:
  maximize: 3c + 5t        (profit)
  subject to:
    2c + 3t ≤ 40          (labor)
    4c + 8t ≤ 100         (wood)
    c, t ≥ 0
```

### Pattern 2: Assignment/Allocation

**Goal**: Assign people/resources to tasks minimizing cost

```
Decision: xᵢⱼ = 1 if assign person i to task j, 0 otherwise

Formulation:
  minimize: Σ costᵢⱼ × xᵢⱼ
  subject to:
    Σⱼ xᵢⱼ = 1 for each person i  (each person gets one task)
    xᵢⱼ ∈ {0, 1}                   (binary decision)
```

### Pattern 3: Scheduling

**Goal**: Schedule activities respecting time windows and resources

```
Decision: Assign activity i to time slot t

Constraints:
  - Each activity assigned to exactly one time slot
  - Resource capacity not exceeded in any time slot
  - Activity duration considered (may span multiple slots)
  - Precedence constraints (task B after task A)
```

---

## Known Limitations

### Solver Precision

**Limitation**: Solvers work with numerical precision (typically 1e-8 to 1e-6), not exact arithmetic

**Impact**: Solutions may violate constraints by small amounts (1e-5 or tighter)

**Mitigation**: 
- Use `result.feasibility` to check residual bounds (gpuGEM reports this)
- Scale problems to avoid very large/small coefficients
- Use appropriate tolerances (don't expect 1e-15 precision)

### Non-convex Problems

**Limitation**: cuOpt QP solver requires convex quadratic objectives (not non-convex, non-linear)

**Impact**: Non-convex problems may fail or return suboptimal solutions

**Check**: If Hessian matrix is positive semi-definite → convex ✓

### Large Problem Size

**Limitation**: GPU memory limits problem size (typically thousands to millions of constraints)

**Impact**: Very large problems (100M+ constraints) may not fit

**Mitigation**: Decompose into smaller subproblems or use specialized solvers

---

## Next Steps

- **Ready to code?** See `cuopt-numerical-optimization-api` to learn how to express these formulations in Python
- **Routing problems?** See `cuopt-routing-api-python` for specialized formulations
- **Multi-objective?** See `cuopt-multi-objective-exploration` for handling multiple objectives

---

## See Also

- [cuOpt Official API Reference](https://github.com/NVIDIA/cuopt)
- [Mathematical Programming Overview (Wikipedia)](https://en.wikipedia.org/wiki/Mathematical_optimization)
- [Linear Programming (Introduction)](https://en.wikipedia.org/wiki/Linear_programming)

---

**Last Updated**: 2026-07-24  
**Status**: published  
**Version**: 1.0.0
