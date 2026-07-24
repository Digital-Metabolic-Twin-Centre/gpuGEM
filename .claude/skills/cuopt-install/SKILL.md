# cuOpt Installation Guide

> **Skill ID**: `cuopt-install`  
> **Category**: setup  
> **Difficulty**: beginner  
> **Time**: 15 minutes  
> **Prerequisites**: None

---

## Overview

Learn how to install cuOpt for Python, C, and server environments. cuOpt is NVIDIA's GPU-accelerated optimization solver that works seamlessly with gpuGEM.

**Target Audience**: Developers new to cuOpt who need to get it running locally

---

## Concepts

### What is cuOpt?

cuOpt is NVIDIA's GPU-accelerated solver for optimization problems:
- **Linear Programming (LP)**: Minimize/maximize linear objectives subject to linear constraints
- **Mixed-Integer LP (MILP)**: LP with integer variables for combinatorial problems
- **Quadratic Programming (QP)**: Convex quadratic objectives with linear constraints
- **Routing**: Vehicle routing, pickup-delivery, and other logistics problems

### Why GPU Acceleration?

GPU acceleration provides:
- 10-100x speedup on large problems (100k+ constraints)
- Parallel constraint evaluation
- Native support for batched solves

### Requirements

- **NVIDIA GPU** (optional for CPU fallback, recommended for performance)
- **CUDA Toolkit 12.x** (for GPU acceleration)
- **Python 3.8+** (or 3.10+ for gpuGEM compatibility)
- **pip** (Python package manager)

---

## Installation

### Python Installation (Recommended for Most Users)

```bash
# For CUDA 12.x (most common)
pip install cuopt-cu12

# For CUDA 11.x
pip install cuopt-cu11

# For CPU only (no NVIDIA GPU)
pip install cuopt-cpu
```

**Verify installation**:
```bash
python -c "import cuopt; print(f'cuOpt version: {cuopt.__version__}')"
```

Expected output:
```
cuOpt version: 0.4.x
```

### C/C++ Installation

For C/C++ projects, install cuOpt development headers:

```bash
# Option 1: Via conda (recommended for development)
conda install -c nvidia cuopt

# Option 2: From source (advanced)
git clone https://github.com/NVIDIA/cuopt.git
cd cuopt
mkdir build && cd build
cmake .. -DCUDA_TOOLKIT_ROOT_DIR=/path/to/cuda
make install
```

### Server Installation (Docker Recommended)

For production server deployments:

```bash
# Pull official cuOpt server image
docker pull nvcr.io/nvidia/cuopt:latest

# Run with GPU support
docker run --gpus all -p 5000:5000 nvcr.io/nvidia/cuopt:latest
```

Or install directly:

```bash
# Install cuOpt Python + start server
pip install cuopt-cu12
cuopt-server --host 0.0.0.0 --port 5000
```

---

## Troubleshooting

### "CUDA not found" Error

**Problem**: Installation succeeds but import fails with CUDA errors

**Solution**:
1. Check NVIDIA driver: `nvidia-smi`
2. If driver not found, install NVIDIA drivers for your GPU
3. If driver present, verify CUDA version matches your cuopt install (cu12 for CUDA 12.x)
4. Fallback to CPU version: `pip install cuopt-cpu`

### "ModuleNotFoundError: No module named 'cuopt'"

**Problem**: pip install succeeded but Python can't find cuopt

**Solution**:
1. Verify pip location: `which pip`
2. Use explicit Python: `python -m pip install cuopt-cu12`
3. Check virtual environment: `which python` should point to venv
4. Create fresh venv:
   ```bash
   python -m venv cuopt_env
   source cuopt_env/bin/activate
   pip install cuopt-cu12
   ```

### "Version mismatch" or "incompatible CUDA"

**Problem**: cuopt-cu12 installed but system has CUDA 11.x

**Solution**:
1. Check CUDA version: `nvcc --version`
2. Reinstall matching package:
   ```bash
   pip uninstall cuopt-cu12
   pip install cuopt-cu11  # if CUDA 11.x
   ```

---

## Common Patterns

### Check GPU Availability

```python
import cuopt

# cuOpt automatically detects GPU
# No explicit setup needed - just import and use
print(f"cuOpt ready for {cuopt.solver.available_gpus()} GPU(s)")
```

### Use in Virtual Environment (Best Practice)

```bash
# Create isolated environment for cuOpt projects
python -m venv cuopt-env
source cuopt-env/bin/activate  # Linux/Mac
# or: cuopt-env\Scripts\activate  # Windows

pip install cuopt-cu12
# Now use cuOpt without affecting system Python
```

### Verify Installation in Script

```python
#!/usr/bin/env python
import sys
try:
    import cuopt
    print(f"✓ cuOpt {cuopt.__version__} installed")
except ImportError:
    print("✗ cuOpt not installed", file=sys.stderr)
    sys.exit(1)
```

---

## Known Limitations

### No Warm-Start Support (v0.4.x)

**Affected Versions**: cuOpt 0.4.x and earlier

**Issue**: The warm-start API (providing initial solution to solver) is broken in some versions

**Workaround**: Don't pass warm-start solutions; solver will initialize automatically

### PaPILO Presolve Tolerance (v0.4.x)

**Affected Versions**: All cuOpt versions using PaPILO

**Issue**: Presolve hardcodes feasibility tolerance of 1e-6 (tighter than many solvers); may declare feasible problems infeasible

**Workaround**: Disable presolve if models fail:
```python
# When creating model, disable presolve
solver_options = {"presolve": False}
```

**Reference**: [cuOpt GitHub Issues](https://github.com/NVIDIA/cuopt/issues)

### GPU Memory Limitations

**Issue**: Large models must fit in GPU memory (typically 8-80 GB); no spillover to CPU

**Workaround**: For very large models, use CPU-only version or decompose into smaller subproblems

---

## Next Steps

- **Ready to solve?** See `cuopt-numerical-optimization-formulation` to learn LP/MILP/QP concepts
- **Start coding?** See `cuopt-numerical-optimization-api` for Python API reference
- **Deploy at scale?** See `cuopt-server-api-python` for server setup

---

## See Also

- [cuOpt Official Repository](https://github.com/NVIDIA/cuopt)
- [NVIDIA Container Registry](https://nvcr.io/nvidia/cuopt)
- [gpuGEM Documentation](https://github.com/farid-zare/gpuGEM)

---

**Last Updated**: 2026-07-24  
**Status**: published  
**Version**: 1.0.0
