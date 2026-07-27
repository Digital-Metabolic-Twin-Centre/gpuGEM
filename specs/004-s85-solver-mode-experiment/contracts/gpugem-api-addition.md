# Public API contract addition: `FBAResult.solved_by`

The one change this feature makes inside `gpugem/` itself (Constitution Principle IV — justified
new surface, see plan.md's Constitution Check).

## Before

```python
@dataclass
class FBAResult:
    status: str
    objective: Optional[float]
    fluxes: Optional[np.ndarray]
    wall_time_s: float
    solver_settings: dict = field(default_factory=dict)
    feasibility: dict = field(default_factory=dict)
    n_iterations: Optional[int] = None
    solver_stats: dict = field(default_factory=dict)
```

## After

```python
@dataclass
class FBAResult:
    status: str
    objective: Optional[float]
    fluxes: Optional[np.ndarray]
    wall_time_s: float
    solver_settings: dict = field(default_factory=dict)
    feasibility: dict = field(default_factory=dict)
    n_iterations: Optional[int] = None
    solver_stats: dict = field(default_factory=dict)
    solved_by: Optional[str] = None
    """Which underlying method produced the solution (``'PDLP'``, ``'DualSimplex'``,
    ``'Barrier'``, ``'Concurrent'``, ``'Unset'``), from cuOpt's ``sol.get_solved_by()``.
    Most informative when ``method=Concurrent`` was requested, since cuOpt races multiple
    methods and the winner can vary; ``None`` if the installed cuOpt version doesn't expose it."""
```

## Contract

- **Backward compatible**: new field has a default (`None`), so every existing call site
  (`gpugem.solve`, `gpugem.solve_cobra`, `FBASolver.solve`, and all of `002`/`003`'s benchmark
  code) continues to work unchanged and unaffected.
- **Populated in `gpugem/solver.py`**: immediately after `sol = Solve(dm, settings)`, wrapped in
  the same defensive `try/except` style already used for `get_lp_stats()` — if
  `sol.get_solved_by()` raises or isn't available, `solved_by` stays `None` rather than failing
  the whole solve.
- **No behavior change**: does not affect what settings are applied, what status is returned, or
  any existing feasibility/objective computation — purely additive information surfaced from data
  cuOpt already computes internally.
