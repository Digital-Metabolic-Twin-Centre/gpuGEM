# Multi-Objective Optimization & Pareto Frontiers

> **Skill ID**: `cuopt-multi-objective-exploration`  
> **Category**: advanced  
> **Difficulty**: advanced  
> **Time**: 20 minutes  
> **Prerequisites**: `cuopt-numerical-optimization-api`

---

## Overview

Explore tradeoffs between competing objectives using Pareto frontier analysis. Understand how to formulate multi-objective problems and extract non-dominated solutions.

**Target Audience**: Researchers and engineers optimizing multiple conflicting objectives

---

## Concepts

### Multi-Objective Problem

Problems with 2+ objectives that conflict:

```
minimize: 
  - f₁(x) = time
  - f₂(x) = cost
  - f₃(x) = emissions
```

**Challenge**: No single "best" solution; improving one objective worsens others

**Solution**: Pareto frontier (set of non-dominated solutions)

### Pareto Dominance

**Solution A dominates Solution B if**:
- A is better or equal in ALL objectives
- A is strictly better in at least ONE objective

**Example**:
- Solution A: cost $100, time 5 hours → NOT dominated (good cost)
- Solution B: cost $120, time 4 hours → NOT dominated (good time)
- Solution C: cost $150, time 6 hours → DOMINATED (worse at both)

### Pareto Frontier

Set of all non-dominated solutions. Decision-maker chooses based on preferences.

---

## API Reference

### Weighted Scalarization

Convert 2+ objectives to single weighted objective:

```python
# minimize: w₁*cost + w₂*time + w₃*emissions
objective = 0.5 * cost + 0.3 * time + 0.2 * emissions

model.minimize(objective)
```

**Weight interpretation**:
- w₁ = 0.5 → cost is 50% important
- w₂ = 0.3 → time is 30% important
- w₃ = 0.2 → emissions is 20% important

**Trade-off**: Weights are subjective; different weights → different solutions

### Epsilon-Constraint Method

Fix one objective, optimize others:

```python
# Minimize time, keeping cost ≤ budget
model.add_constraint(cost <= 500)
model.minimize(time)

solution_1 = solver.solve(model)

# Try different budgets
for budget in [300, 400, 500, 600]:
    model.add_constraint(cost <= budget)
    solution = solver.solve(model)
    frontier.append(solution)
```

---

## Examples

### Example 1: Two-Objective (Cost vs Time)

```python
import cuopt

def get_pareto_frontier(locations, vehicles, weights_list):
    """Solve VRP for different cost/time tradeoffs."""
    
    frontier = []
    
    for weight_cost, weight_time in weights_list:
        model = cuopt.routing.RoutingModel()
        
        # Setup (add locations, vehicles, etc.)
        # ...
        
        # Multi-objective: weighted sum
        objective = (
            weight_cost * model.total_cost +
            weight_time * model.total_time
        )
        model.minimize(objective)
        
        # Solve
        solver = cuopt.routing.RoutingSolver()
        solution = solver.solve(model)
        
        frontier.append({
            "weights": (weight_cost, weight_time),
            "cost": solution.total_cost,
            "time": solution.total_time,
            "solution": solution
        })
    
    return frontier

# Explore tradeoff space
weights = [
    (1.0, 0.0),  # Pure cost minimization
    (0.8, 0.2),
    (0.5, 0.5),  # Balanced
    (0.2, 0.8),
    (0.0, 1.0)   # Pure time minimization
]

frontier = get_pareto_frontier(locs, vehicles, weights)

# Results
for point in frontier:
    w_c, w_t = point["weights"]
    print(f"w_cost={w_c:.1f}, w_time={w_t:.1f}: " +
          f"cost=${point['cost']:.0f}, time={point['time']:.0f}h")

# Validation: is each point non-dominated?
for i, p1 in enumerate(frontier):
    for j, p2 in enumerate(frontier):
        if i != j:
            # p1 should not dominate p2
            worse_cost = p1["cost"] >= p2["cost"]
            worse_time = p1["time"] >= p2["time"]
            assert not (worse_cost and worse_time), "Dominated solution found"
```

### Example 2: Three-Objective with Normalization

```python
import cuopt
import numpy as np

class ParetoExplorer:
    def __init__(self, model):
        self.model = model
        self.frontier = []
    
    def explore_weighted(self, objectives, num_points=10):
        """Explore using weighted scalarization."""
        
        # Normalize weights to sum=1
        weights_list = np.random.dirichlet(
            np.ones(len(objectives)),
            num_points
        )
        
        for weights in weights_list:
            weighted_obj = sum(
                w * obj for w, obj in zip(weights, objectives)
            )
            
            self.model.minimize(weighted_obj)
            solver = cuopt.Solver()
            solution = solver.solve(self.model)
            
            if solution.status in ["Optimal", "Suboptimal"]:
                # Evaluate all objectives
                obj_values = [obj.evaluate(solution) 
                             for obj in objectives]
                
                self.frontier.append({
                    "weights": weights,
                    "objectives": obj_values,
                    "solution": solution
                })
        
        return self.frontier
    
    def is_dominated(self, solution_a, solution_b):
        """Check if A is dominated by B."""
        objs_a = solution_a["objectives"]
        objs_b = solution_b["objectives"]
        
        # B dominates A if:
        # - B better or equal in ALL objectives
        # - B strictly better in at least ONE
        better_or_equal = all(b <= a for a, b in zip(objs_a, objs_b))
        strictly_better = any(b < a for a, b in zip(objs_a, objs_b))
        
        return better_or_equal and strictly_better
    
    def remove_dominated(self):
        """Keep only non-dominated solutions."""
        non_dominated = []
        
        for i, sol in enumerate(self.frontier):
            is_dominated = False
            for j, other in enumerate(self.frontier):
                if i != j and self.is_dominated(sol, other):
                    is_dominated = True
                    break
            
            if not is_dominated:
                non_dominated.append(sol)
        
        self.frontier = non_dominated
        return self.frontier

# Usage
explorer = ParetoExplorer(model)
frontier = explorer.explore_weighted(
    objectives=[cost, time, emissions],
    num_points=20
)

non_dominated = explorer.remove_dominated()
print(f"Explored 20 points, {len(non_dominated)} non-dominated")
```

### Example 3: Portfolio Optimization (Cost vs Risk)

```python
import cuopt

model = cuopt.modeling.Model()

# Decision variables: allocation to assets
allocations = {
    asset: model.continuous_variable(
        name=asset,
        lower_bound=0,
        upper_bound=0.4  # Max 40% in one asset
    )
    for asset in ["stocks", "bonds", "commodities"]
}

# Expected return for each asset
returns = {"stocks": 0.12, "bonds": 0.04, "commodities": 0.06}

# Variance (risk) for each asset
variance = {"stocks": 0.25, "bonds": 0.01, "commodities": 0.10}

# Constraint: fully invested
model.add_constraint(
    sum(allocations.values()) == 1.0,
    name="budget"
)

# Multi-objective: maximize return, minimize risk
# (weighted scalarization)
return_obj = sum(returns[a] * allocations[a] for a in allocations)
risk_obj = sum(variance[a] * (allocations[a]**2) for a in allocations)

# Try different risk aversions
for risk_aversion in [0.5, 1.0, 2.0, 5.0]:
    model.maximize(return_obj - risk_aversion * risk_obj)
    
    solver = cuopt.Solver()
    result = solver.solve(model)
    
    # Validate solution
    assert result.status in ["Optimal", "Suboptimal"]
    
    total_alloc = sum(result.solution[allocations[a]] for a in allocations)
    assert abs(total_alloc - 1.0) < 1e-5, "Budget constraint violated"
    
    print(f"Risk aversion {risk_aversion}:")
    for asset in allocations:
        print(f"  {asset}: {result.solution[allocations[asset]]:.1%}")
```

---

## Common Patterns

### Pattern 1: Visualization

```python
import matplotlib.pyplot as plt

# 2D Pareto frontier
costs = [p["cost"] for p in frontier]
times = [p["time"] for p in frontier]

plt.scatter(costs, times, label="Solutions", s=100)
plt.xlabel("Cost ($)")
plt.ylabel("Time (hours)")
plt.title("Pareto Frontier: Cost vs Time Tradeoff")
plt.grid()
plt.show()
```

### Pattern 2: Preference-Based Selection

```python
def select_solution(frontier, preference):
    """Select solution matching user preference."""
    
    # preference = (importance of cost, importance of time)
    w_cost, w_time = preference
    
    scores = [
        w_cost * p["cost"] + w_time * p["time"]
        for p in frontier
    ]
    
    best_idx = scores.index(min(scores))
    return frontier[best_idx]

# User prefers fast delivery (time = 0.7)
user_pref = (0.3, 0.7)  # cost=30%, time=70%
selected = select_solution(frontier, user_pref)
```

---

## Known Limitations

### Computational Complexity

**Issue**: Exploring full Pareto frontier is computationally expensive (many solves)

**Workaround**: Use small sample of weights; focus on interesting regions

### Non-Convex Problems

**Issue**: Solver may not find true Pareto optimal for non-convex problems

**Workaround**: Use multiple starting points; verify with high-precision solve

---

## Next Steps

- **Want visualization code?** See matplotlib/plotly docs
- **Advanced MOO?** Use epsilon-constraint or augmented Tchebycheff methods

---

**Last Updated**: 2026-07-24  
**Status**: published  
**Version**: 1.0.0
