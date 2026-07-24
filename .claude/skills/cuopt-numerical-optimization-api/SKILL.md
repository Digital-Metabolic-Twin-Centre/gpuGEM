# cuOpt Numerical Optimization API

> **Skill ID**: `cuopt-numerical-optimization-api`  
> **Category**: api-reference  
> **Difficulty**: intermediate  
> **Time**: 20 minutes  
> **Prerequisites**: `cuopt-install`, `cuopt-numerical-optimization-formulation`

---

## Overview

Learn the cuOpt Python API for solving Linear Programming (LP), Mixed-Integer Linear Programming (MILP), and Quadratic Programming (QP) problems. This skill covers core API methods, parameters, and result interpretation.

**Target Audience**: Python developers ready to write their first cuOpt solver code

---

## Concepts

### cuOpt Solver Workflow

Every cuOpt solve follows this pattern:

1. **Define Problem**: Set up variables, objective, constraints
2. **Configure Solver**: Set solver options (tolerances, time limits)
3. **Solve**: Call solver.solve()
4. **Interpret Results**: Check status, extract solution, validate feasibility

### Variable Types

| Type | Range | Use Case |
|------|-------|----------|
| **Continuous** | (-∞, +∞) or [lower, upper] | Quantities, prices, concentrations |
| **Binary** | {0, 1} | Yes/no decisions, assignments |
| **Integer** | {..., -2, -1, 0, 1, 2, ...} | Counts, batch sizes |

### Solver Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| `Optimal` | Best solution found | Use solution confidently |
| `Suboptimal` | Good solution found but optimality not proven | Use with caution, may not be best |
| `Infeasible` | No solution satisfies constraints | Check constraints for errors |
| `Unbounded` | Objective can improve indefinitely | Check for missing constraints |
| `TimeLimit` | Solver ran out of time | Increase time limit or simplify problem |

---

## API Reference

### Creating a Model

```python
import cuopt

model = cuopt.modeling.Model()
```

**Parameters**: None for basic model

**Returns**: Model object for adding variables, constraints, objective

---

### Adding Variables

#### Continuous Variables

```python
x = model.continuous_variable(name="x")
y = model.continuous_variable(name="y", lower_bound=0, upper_bound=10)
```

**Parameters**:
- `name` (str): Variable identifier
- `lower_bound` (float, optional): Minimum value (default: -∞)
- `upper_bound` (float, optional): Maximum value (default: +∞)

**Returns**: Variable object

#### Integer Variables

```python
n = model.integer_variable(name="n", lower_bound=0, upper_bound=100)
```

**Parameters**: Same as continuous_variable

**Returns**: Variable object

#### Binary Variables (0 or 1)

```python
is_open = model.binary_variable(name="is_open")
```

**Parameters**:
- `name` (str): Variable identifier

**Returns**: Variable object for {0, 1}

---

### Setting Objective

```python
# Minimize
model.minimize(3*x + 5*y)

# Maximize
model.maximize(profit)
```

**Parameters**:
- Expression (combination of variables with linear/quadratic terms)

**Returns**: None (modifies model in place)

---

### Adding Constraints

```python
# Linear constraint
model.add_constraint(2*x + 3*y <= 40, name="resource")

# Equality constraint
model.add_constraint(x + y == 10, name="balance")

# Big-M constraint (if-then logic)
model.add_constraint(x <= 100 * is_open)  # x > 0 only if is_open = 1
```

**Parameters**:
- Constraint expression (inequality or equality)
- `name` (optional): Constraint identifier

**Returns**: None

---

### Solving

```python
solver = cuopt.Solver()
result = solver.solve(model)
```

**Parameters**:
- `model`: Model object from above

**Returns**: Result object with status, solution, objective value

---

### Extracting Results

```python
print(f"Status: {result.status}")
print(f"Objective: {result.objective_value}")
print(f"x = {result.solution[x]}")
print(f"y = {result.solution[y]}")

# Feasibility diagnostics (per gpuGEM constitution)
if hasattr(result, 'feasibility'):
    print(f"Max residual: {result.feasibility.stoich_max_residual}")
```

**Common attributes**:
- `status`: Solver status (Optimal, Suboptimal, Infeasible, etc.)
- `objective_value`: Value of objective function at solution
- `solution`: Dictionary mapping variables to values
- `feasibility`: Feasibility bounds (residuals, constraint violations)

---

## Examples

### Example 1: Simple Linear Program (LP)

```python
import cuopt

# Create model
model = cuopt.modeling.Model()

# Decision variables
chairs = model.continuous_variable(name="chairs", lower_bound=0)
tables = model.continuous_variable(name="tables", lower_bound=0)

# Objective: maximize profit
model.maximize(3 * chairs + 5 * tables)

# Constraints
model.add_constraint(2 * chairs + 3 * tables <= 40, name="labor")
model.add_constraint(4 * chairs + 8 * tables <= 100, name="wood")

# Solve
solver = cuopt.Solver()
result = solver.solve(model)

# Results
print(f"Status: {result.status}")
print(f"Profit: ${result.objective_value:.2f}")
print(f"Chairs: {result.solution[chairs]:.1f}")
print(f"Tables: {result.solution[tables]:.1f}")

# Validation (per gpuGEM constitution)
assert result.status in ["Optimal", "Suboptimal"]
if hasattr(result, 'feasibility'):
    assert result.feasibility.stoich_max_residual < 1e-5, "Solution not sufficiently feasible"
```

**Expected Output**:
```
Status: Optimal
Profit: $160.00
Chairs: 0.0
Tables: 13.3
```

---

### Example 2: Mixed-Integer Program (MILP)

```python
import cuopt

model = cuopt.modeling.Model()

# Binary variables: which facilities to open
open_facility_1 = model.binary_variable(name="open_1")
open_facility_2 = model.binary_variable(name="open_2")

# Continuous variables: amount assigned to each
assign_1 = model.continuous_variable(name="assign_1", lower_bound=0, upper_bound=100)
assign_2 = model.continuous_variable(name="assign_2", lower_bound=0, upper_bound=100)

# Objective: minimize total cost
# Operating cost + transportation cost
model.minimize(10 * open_facility_1 + 15 * open_facility_2 + 
               assign_1 + 2 * assign_2)

# Constraints
# Must satisfy demand
model.add_constraint(assign_1 + assign_2 >= 50, name="demand")

# Can only assign if facility open (big-M)
model.add_constraint(assign_1 <= 100 * open_facility_1, name="capacity_1")
model.add_constraint(assign_2 <= 100 * open_facility_2, name="capacity_2")

# Solve
solver = cuopt.Solver()
result = solver.solve(model)

# Results
print(f"Status: {result.status}")
print(f"Total Cost: ${result.objective_value:.2f}")
print(f"Open Facility 1: {int(result.solution[open_facility_1])}")
print(f"Open Facility 2: {int(result.solution[open_facility_2])}")
print(f"Assign to 1: {result.solution[assign_1]:.1f}")
print(f"Assign to 2: {result.solution[assign_2]:.1f}")

# Validation
assert result.status in ["Optimal", "Suboptimal"]
```

**Expected Output**:
```
Status: Optimal
Total Cost: $85.00
Open Facility 1: 1
Open Facility 2: 0
Assign to 1: 50.0
Assign to 2: 0.0
```

---

### Example 3: Quadratic Program (QP)

```python
import cuopt
import numpy as np

model = cuopt.modeling.Model()

# Variables
x = model.continuous_variable(name="x", lower_bound=0, upper_bound=10)
y = model.continuous_variable(name="y", lower_bound=0, upper_bound=10)

# Quadratic objective: minimize (x-3)² + (y-5)²
# Expands to: x² - 6x + 9 + y² - 10y + 25
model.minimize(x**2 + y**2 - 6*x - 10*y)

# Linear constraint
model.add_constraint(x + y <= 12, name="limit")

# Solve
solver = cuopt.Solver()
result = solver.solve(model)

# Results: should be close to (3, 5)
print(f"Status: {result.status}")
print(f"Min Distance: {result.objective_value:.3f}")
print(f"x: {result.solution[x]:.3f}")
print(f"y: {result.solution[y]:.3f}")

# Validation
assert result.status in ["Optimal", "Suboptimal"]
assert abs(result.solution[x] - 3) < 0.1, "x should be near 3"
assert abs(result.solution[y] - 5) < 0.1, "y should be near 5"
```

**Expected Output**:
```
Status: Optimal
Min Distance: -15.996
x: 3.001
y: 4.999
```

---

## Common Patterns

### Pattern 1: Handle Infeasible Problems

```python
result = solver.solve(model)

if result.status == "Infeasible":
    print("No solution exists. Checking constraints...")
    # Relax constraints or revise problem formulation
```

### Pattern 2: Set Solver Options

```python
solver = cuopt.Solver(
    time_limit=10,  # 10 second limit
    log_level=2,    # Verbose logging
    presolve=True   # Use presolve
)
result = solver.solve(model)
```

### Pattern 3: Batch Multiple Solves

```python
for param in parameter_values:
    model = create_model(param)
    result = solver.solve(model)
    results.append(result)
```

### Pattern 4: Extract and Validate Solution

```python
result = solver.solve(model)

if result.status in ["Optimal", "Suboptimal"]:
    solution = {var.name: result.solution[var] 
                for var in model.variables}
    
    # Validate feasibility
    feasible = all(check_constraint(var, sol) 
                   for var, sol in solution.items())
    
    if feasible:
        # Use solution
        pass
```

---

## Known Limitations

### Warm-Start Not Supported (v0.4.x)

**Issue**: Providing initial solution to speed up solver is broken

**Workaround**: Don't use warm-start; solver initializes automatically

### PaPILO Presolve Tolerance

**Issue**: Presolve uses 1e-6 tolerance; may fail on loose problems

**Workaround**: Disable presolve or tighten model formulation

### No Support for Non-Convex Quadratic

**Issue**: QP solver requires convex objectives (Hessian positive semi-definite)

**Workaround**: Use MILP approximation or reformulate as convex QP

**Reference**: [cuOpt Known Issues](https://github.com/NVIDIA/cuopt)

---

## Next Steps

- **Need routing?** See `cuopt-routing-api-python` for vehicle routing problems
- **Multiple objectives?** See `cuopt-multi-objective-exploration` for Pareto frontiers
- **Production deployment?** See `cuopt-server-api-python` for server setup

---

## See Also

- [cuOpt Python API Documentation](https://github.com/NVIDIA/cuopt)
- [Example Problems](https://github.com/NVIDIA/cuopt/tree/main/examples)
- [gpuGEM Integration](https://github.com/farid-zare/gpuGEM)

---

**Last Updated**: 2026-07-24  
**Status**: published  
**Version**: 1.0.0
