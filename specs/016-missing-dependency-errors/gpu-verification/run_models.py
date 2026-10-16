import json, sys, time
sys.path.insert(0, ".")
import numpy as np, scipy.sparse as sp
import gpugem
from benchmarks import models as M, residual as R
assert "site-packages" in gpugem.__file__, gpugem.__file__
print("gpugem", gpugem.__version__, gpugem.__file__, flush=True)
out = []
for name in sys.argv[1:]:
    ref = json.load(open("benchmarks/results/%s.json" % name))
    obj_tol, res_tol = ref["obj_tol"], ref["res_tol"]
    gref = ref["gurobi"]["objective"]; cref = ref["cuopt"].get("objective")
    lp, prov = M.build_lp(name)
    S = sp.csr_matrix(lp["S"]); b = np.asarray(lp["b"], float)
    args = {k: lp[k] for k in ("S","b","lb","ub","c","maximize","C","d_lb","d_ub") if lp.get(k) is not None}
    t = time.time()
    r = gpugem.solve(time_limit=300.0, check_feasibility=True, **args)
    wall = time.time() - t
    resid = R.feasibility_residual(S, b, r.fluxes) if r.fluxes is not None else None
    rel = None if r.objective is None else abs(r.objective - gref) / max(1.0, abs(r.objective), abs(gref))
    ok = (r.status == "Optimal" and rel is not None and rel <= obj_tol and resid is not None and resid <= res_tol)
    rec = dict(model=name, n_cols=S.shape[1], n_rows=S.shape[0], status=r.status, objective=r.objective,
               gurobi_ref=gref, committed_cuopt_ref=cref, obj_rel_diff=rel, obj_tol=obj_tol,
               residual_inf=resid, res_tol=res_tol, solve_s=round(float(r.wall_time_s), 3),
               solved_by=str(getattr(r, "solved_by", None)), PASS=bool(ok),
               feasibility=r.feasibility, settings=dict(r.solver_settings))
    out.append(rec)
    print(json.dumps({k: rec[k] for k in ("model","n_rows","n_cols","status","objective","gurobi_ref","obj_rel_diff","obj_tol","residual_inf","res_tol","solve_s","PASS")}), flush=True)
json.dump(out, open("/home/farid/gpugem-gputest/model_results.json", "w"), indent=1, default=str)
print("ALL PASS" if all(o["PASS"] for o in out) else "SOME FAILED", flush=True)
