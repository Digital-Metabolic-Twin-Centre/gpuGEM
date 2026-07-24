# Quickstart: Validating and Using cuOpt Skills

**Date**: 2026-07-24  
**Purpose**: End-to-end validation that cuOpt skills are working and usable  
**Time**: 30 minutes  
**Prerequisites**: Claude Code installed (IDE plugin, web, or CLI), Python 3.10+

---

## Setup

### 1. Prerequisites Check

Before starting, ensure you have:

```bash
# Check Python version (must be 3.10+)
python --version

# Check pip is available
pip --version

# (Optional) Check CUDA/GPU availability
nvidia-smi  # If NVIDIA GPU present; skip if CPU-only
```

### 2. Install cuOpt

Follow the **cuopt-install** skill to install cuOpt for your environment:

```bash
# For Python with CUDA 12.x (typical)
pip install cuopt-cu12

# Verify installation
python -c "import cuopt; print(cuopt.__version__)"
```

Expected output: `cuopt version: 0.4.x` (or later)

---

## Validation Path

### Skill 1: cuopt-numerical-optimization-formulation

**Goal**: Verify you understand LP, MILP, QP concepts

**Validation**:
1. Open the **cuopt-numerical-optimization-formulation** skill in Claude Code
2. Read the Concepts section
3. Answer mentally: "What's the difference between LP and MILP?" and "Why do I need constraints?"
4. If answers are clear, ✅ move to Skill 2

**Time**: 10 minutes

---

### Skill 2: cuopt-numerical-optimization-api

**Goal**: Write and run your first cuOpt LP solver code

**Validation**:
1. Open the **cuopt-numerical-optimization-api** skill
2. Find the "Simple LP Setup" example
3. Copy the code into a file: `test_lp.py`
4. Run it:
   ```bash
   python test_lp.py
   ```
5. Verify output matches "Expected Output" section
6. Modify the example (e.g., change objective from minimize to maximize) and run again
7. If modified version runs and outputs change appropriately, ✅ move to next skill

**Time**: 10 minutes

---

### Skill 3: cuopt-server-api-python (optional, for production)

**Goal**: Verify cuOpt server can be deployed

**Validation** (if you plan to deploy cuOpt as a service):
1. Open the **cuopt-server-api-python** skill
2. Follow the server deployment example in "Example: Server Setup & Client Interaction"
3. Start cuOpt server in one terminal:
   ```bash
   cuopt-server --host 127.0.0.1 --port 5000
   ```
4. In another terminal, run the client example:
   ```bash
   python client_example.py
   ```
5. Verify client receives solution results from server
6. If successful, ✅ server integration works

**Time**: 10 minutes

---

## Skill Success Criteria

### Each skill must satisfy:

| Criterion | Check |
|-----------|-------|
| **No runtime errors** | Examples run without crashing | ✓ |
| **Correct output** | Output matches "Expected Output" section | ✓ |
| **Feasibility validation** | Examples include result validation (status check) | ✓ |
| **Clear explanation** | Concepts section makes sense after reading | ✓ |
| **Runnable code** | Can copy, paste, and execute example code | ✓ |

---

## Integration with gpuGEM

### Bonus Validation: Use cuOpt through gpuGEM

If you have gpuGEM installed, validate the integration:

```python
from gpuGEM import solve_cobra
import cobra.test

# Load example COBRA model
model = cobra.test.create_test_model("textbook")

# Solve using cuOpt via gpuGEM
result = solve_cobra(model, solver="cuopt")

# Verify gpuGEM's feasibility diagnostics
print(f"Status: {result.status}")
print(f"Feasibility: {result.feasibility}")
print(f"Objective: {result.objective_value}")
```

**Expected Behavior**:
- Status is "Optimal" or "Suboptimal" (not masked errors)
- Feasibility object has `stoich_max_residual` and other diagnostics
- Objective value matches cuOpt's reported solution

If this works, ✅ cuOpt integrates correctly with gpuGEM's validation layer.

---

## Troubleshooting

### "cuopt not found" / Import error

```
ModuleNotFoundError: No module named 'cuopt'
```

**Solution**: Reinstall cuOpt using the **cuopt-install** skill. Verify CUDA/GPU availability matches your environment.

### "CUDA not found" / Runtime error

```
RuntimeError: CUDA device not available
```

**Solution**: 
- If you have GPU: Check NVIDIA driver version (should match cuopt-cu12 requirement)
- If CPU-only: Verify cuOpt CPU-fallback is enabled (check with cuopt-install skill)

### Example output doesn't match

**Solution**: 
- Check cuOpt version (should match skill's documented version)
- Try with a fresh Python environment: `python -m venv test_env && source test_env/bin/activate`
- Check that you're not modifying the example (compare against "Expected Output" literally)

### Server won't start / connection refused

**Solution**:
- Verify server is running before calling client code
- Check port 5000 isn't in use: `lsof -i :5000` (Linux/Mac)
- If firewall blocks: open port 5000 or use localhost (127.0.0.1)

---

## Success Checklist

After completing this quickstart, you should be able to:

- [ ] Install cuOpt for your environment
- [ ] Understand LP, MILP, and QP concepts
- [ ] Write and run a simple LP solver in Python
- [ ] Interpret solver status and feasibility diagnostics
- [ ] Deploy cuOpt as a server (if relevant to your use case)
- [ ] Integrate cuOpt with gpuGEM for COBRA-compatible solving

---

## Next Steps

- **For routing problems**: See **cuopt-routing-api-python** skill
- **For multi-objective optimization**: See **cuopt-multi-objective-exploration** skill
- **For advanced techniques**: See **cuopt-developer** skill for contributing/extending cuOpt
- **For production deployments**: See **cuopt-server-api-python** skill for scaling and monitoring guidance

---

## Feedback

If you encounter issues or have suggestions for improving the skills:

1. Note which skill had the problem
2. Document the error and steps to reproduce
3. Share feedback via: [Claude Code feedback link]

---

## Additional Resources

- [cuOpt Official Documentation](https://github.com/NVIDIA/cuopt)
- [gpuGEM Documentation](https://github.com/farid-zare/gpuGEM)
- [COBRA.py Documentation](https://opencobra.github.io/cobrapy/)
