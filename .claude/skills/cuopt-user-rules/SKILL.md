# cuOpt End-User Guidelines & Best Practices

> **Skill ID**: `cuopt-user-rules`  
> **Category**: setup  
> **Difficulty**: beginner  
> **Time**: 15 minutes  
> **Prerequisites**: `cuopt-install`

---

## Overview

Essential rules, best practices, and common pitfalls for using cuOpt across all problem types (routing, LP, MILP, QP, server). Follow these guidelines to maximize solver effectiveness.

**Target Audience**: All cuOpt users (data scientists, engineers, developers)

---

## Core Rules

### Rule 1: Always Validate Solution Feasibility

```python
# ✓ CORRECT: Check feasibility
result = solver.solve(model)
if result.status == "Optimal":
    if hasattr(result, 'feasibility'):
        # gpuGEM provides feasibility diagnostics
        residuals = result.feasibility.stoich_max_residual
        if residuals < 1e-5:
            # Solution is valid, use it
            use_solution(result.solution)
```

**Why**: Solvers may return "Optimal" despite tolerance violations. Always validate.

### Rule 2: Normalize Problem Scale

```python
# ✗ BAD: Mixed scales (1e-6 to 1e6 coefficients)
model.minimize(1e-6 * x + 1e6 * y + z)

# ✓ GOOD: Normalize to 1e-3 to 1e3 range
model.minimize(0.001 * x + 1000 * y + 1 * z)
```

**Why**: Badly scaled problems cause numerical instability and solver failures.

### Rule 3: Use Appropriate Problem Type

```python
# ✗ WRONG: Use MILP solver for LP
model.add_integer_constraint(x)  # Unnecessary

# ✓ RIGHT: Match solver to problem type
# LP → use LP solver (faster)
# MILP → use MILP solver (handles integers)
```

**Why**: Unnecessary complexity slows solving.

### Rule 4: Document Assumptions & Constraints

```python
# ✓ GOOD: Clear constraint documentation
model.add_constraint(
    supply <= capacity,
    name="warehouse_capacity"  # Clear name
)

# Include assumption comments
# Assumes: demand is deterministic (not stochastic)
# Assumes: no lead times between supply and delivery
```

**Why**: Clarifies scope and prevents model misuse.

### Rule 5: Monitor Solver Progress

```python
# For long-running solves, check progress
solver = cuopt.Solver(log_level=2)  # Verbose logging
result = solver.solve(model, verbose=True)

# Or implement custom callback
def log_progress(iteration, current_obj):
    if iteration % 100 == 0:
        print(f"Iteration {iteration}: obj={current_obj:.2f}")
```

**Why**: Detect solver hangs or slow convergence early.

---

## Best Practices by Problem Type

### Linear Programming (LP)

✓ Use for continuous variables only  
✓ Ensure all constraints are linear  
✓ Scale objective coefficients to 1e-3 to 1e3 range  
✓ Validate solution residuals < 1e-5  

✗ Don't mix integer/continuous without MILP solver  
✗ Don't use LP for inherently discrete problems  

### Mixed-Integer Linear Programming (MILP)

✓ Use for problems requiring integer decisions  
✓ Provide good initial bounds (upper/lower on integer vars)  
✓ Use time limits for large problems  
✓ Validate solution is truly integer (check residuals)  

✗ Don't solve unnecessarily large MILPs (1M+ constraints)  
✗ Don't expect exact solutions for NP-hard problems  

### Quadratic Programming (QP)

✓ Verify objective is convex (Hessian positive semi-definite)  
✓ Use for regression, portfolio, or distance minimization  
✓ Start with small problems; scale gradually  

✗ Don't use QP for non-convex objectives (use approximation)  

### Routing (VRP)

✓ Define realistic time windows and service durations  
✓ Use distance matrix for non-Euclidean problems  
✓ Validate solution respects all constraints (windows, capacity)  

✗ Don't create problems with 10k+ stops without decomposition  

### Server Deployment

✓ Use async API for problems taking >5 seconds  
✓ Implement connection retry logic  
✓ Monitor server GPU memory and queue depth  
✓ Set reasonable time limits on each job  

✗ Don't send unbounded solve requests (always set time limit)  

---

## Troubleshooting Checklist

### Problem: "Infeasible" Solution

**Checklist**:
1. ✓ Verify constraints can be satisfied simultaneously
   ```python
   # Can capacity >= demand AND lower_bound <= upper_bound?
   model.add_constraint(demand <= capacity)
   ```
2. ✓ Check bound assumptions
   ```python
   # Impossible bound ranges?
   x = model.continuous_variable(lower_bound=100, upper_bound=50)
   ```
3. ✓ Relax constraints temporarily to find culprit
   ```python
   for i, constraint in enumerate(model.constraints):
       # Try solving without this constraint
       pass
   ```

### Problem: "Unbounded" Solution

**Checklist**:
1. ✓ Verify objective has correct direction
   ```python
   # Should minimize cost, not maximize it?
   model.minimize(cost)
   ```
2. ✓ Check variable bounds exist
   ```python
   # Variables must be bounded for bounded solution
   x = model.continuous_variable(upper_bound=1000)
   ```
3. ✓ Verify constraints limit objective
   ```python
   model.add_constraint(x + y <= 100)  # Limits growth
   ```

### Problem: "Slow" Solve or Timeout

**Checklist**:
1. ✓ Increase time limit (if reasonable)
   ```python
   solver = cuopt.Solver(time_limit=60)  # 60 seconds
   ```
2. ✓ Simplify problem (remove detail, aggregate)
   ```python
   # Use weekly aggregation instead of daily detail
   ```
3. ✓ Presolve can help or hurt—try disabling
   ```python
   solver = cuopt.Solver(presolve=False)
   ```
4. ✓ Check scaling (badly scaled = slow)
   ```python
   # Normalize coefficients to 1e-3–1e3 range
   ```

### Problem: "Suboptimal" Solution (Not Optimal)

**Checklist**:
1. ✓ Is time limit too short?
   ```python
   # Increase solver time
   solver = cuopt.Solver(time_limit=120)
   ```
2. ✓ Is problem actually MILP? (harder to solve exactly)
   ```python
   # MILP is NP-hard; may not reach optimal
   # Accept suboptimal or use time/gap tolerance
   ```
3. ✓ Check solution quality gap
   ```python
   gap = (upper_bound - lower_bound) / lower_bound
   if gap < 0.05:  # Within 5% of optimal
       use_solution(result)
   ```

---

## Integration with gpuGEM

### Using cuOpt via gpuGEM

```python
from gpuGEM import solve_cobra

# gpuGEM provides feasibility validation
result = solve_cobra(model, solver="cuopt")

# result.feasibility includes:
# - stoich_max_residual: constraint violation bound
# - Lower bound on actual optimization gap
# Use these to validate solution quality
```

### Key Differences (cuOpt native vs gpuGEM wrapper)

| Aspect | cuOpt Native | gpuGEM Wrapper |
|--------|-------------|----------------|
| **Control** | Full | Limited (safety first) |
| **Feasibility validation** | Manual | Automatic (included) |
| **API** | cuOpt-specific | COBRA-compatible |
| **Result interpretation** | User responsibility | Framework handles it |

---

## Known Limitations Summary

| Issue | Workaround |
|-------|-----------|
| Warm-start broken | Don't use warm-start |
| PaPILO 1e-6 tolerance | Disable presolve if needed |
| No non-convex QP | Use MILP approximation |
| GPU memory limits | Use smaller models or decompose |
| No built-in auth (server) | Use firewall or reverse proxy |

---

## Learning Path

1. **Start**: `cuopt-install` (setup)
2. **Learn**: `cuopt-numerical-optimization-formulation` (concepts)
3. **Code**: `cuopt-numerical-optimization-api` (LP/MILP/QP)
4. **Specialize**: 
   - `cuopt-routing-api-python` (routing)
   - `cuopt-multi-objective-exploration` (MOO)
5. **Deploy**: `cuopt-server-api-python` (production)
6. **Extend**: `cuopt-developer` (contributing)

---

**Last Updated**: 2026-07-24  
**Status**: published  
**Version**: 1.0.0
