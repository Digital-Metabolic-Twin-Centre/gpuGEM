# cuOpt Developer Workflow & Contributing

> **Skill ID**: `cuopt-developer`  
> **Category**: setup  
> **Difficulty**: advanced  
> **Time**: 30 minutes  
> **Prerequisites**: `cuopt-install`, `cuopt-numerical-optimization-api`

---

## Overview

Set up a cuOpt development environment and contribute to cuOpt internals. Learn the repository structure, build process, testing workflow, and contribution guidelines.

**Target Audience**: Open-source contributors and developers extending cuOpt

---

## Concepts

### cuOpt Repository Structure

```
cuopt/
├── src/                    # C++ source code
│   ├── solver/            # Core solver implementations
│   ├── routing/           # Routing solver
│   └── python_api/        # Python bindings
├── python/                # Python package source
├── examples/              # Example problems
├── tests/                 # Test suite
├── cmake/                 # CMake build configuration
├── docs/                  # API documentation
└── README.md             # Project overview
```

### Build System

cuOpt uses **CMake** for C++ builds and **setuptools** for Python packaging.

**Build flow**:
1. CMake configures build (detects CUDA, compilers)
2. Make/ninja compiles C++ solver
3. SWIG generates Python bindings
4. setuptools packages Python wheel

---

## Setup Development Environment

### Clone Repository

```bash
git clone https://github.com/NVIDIA/cuopt.git
cd cuopt
git checkout main  # Or specific release branch
```

### Install Build Dependencies

```bash
# System dependencies (Ubuntu/Debian)
sudo apt-get install build-essential cmake cuda-toolkit

# Python dependencies
pip install -r requirements-dev.txt
pip install pytest pytest-cov black flake8

# Or use conda (recommended)
conda env create -f environment-dev.yml
conda activate cuopt-dev
```

### Build from Source

```bash
# Create build directory
mkdir build && cd build

# Configure (detects CUDA automatically)
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DCUDA_TOOLKIT_ROOT_DIR=/path/to/cuda

# Build
cmake --build . -j$(nproc)

# Test
ctest --output-on-failure

# Install (optional)
cmake --install .
```

### Verify Build

```bash
python -c "import cuopt; print(cuopt.__version__)"
# Expected: cuopt version: 0.4.x-dev
```

---

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/my-feature
# or: git checkout -b bugfix/issue-123
```

### 2. Make Changes

**C++ Changes** (in `src/`):
- Edit solver code
- Run tests: `ctest`
- Follow code style (see CONTRIBUTING.md)

**Python Changes** (in `python/`):
- Edit API or examples
- Rebuild bindings: `cmake --build . --target python`
- Test: `pytest python/tests/`

### 3. Test Thoroughly

```bash
# Run all tests
pytest

# Run specific test
pytest python/tests/test_api.py::test_solve_lp -v

# Coverage
pytest --cov=cuopt python/tests/

# Only run quick tests (skip slow ones)
pytest -m "not slow"
```

### 4. Lint and Format

```bash
# Format code (black for Python, clang-format for C++)
black python/

# Check style
flake8 python/ --max-line-length=100

# Type checking (Python)
mypy python/cuopt
```

### 5. Commit and Push

```bash
git add .
git commit -m "feat: Add new feature" -m "Description of changes"
git push origin feature/my-feature
```

### 6. Create Pull Request

- Push to fork
- Create PR on GitHub with:
  - Clear title: "Add X feature" or "Fix X bug"
  - Description of changes and motivation
  - Link to related issues
  - Test results (attach or link CI output)

---

## Key Files & APIs

### Main Entry Points

| File | Purpose |
|------|---------|
| `src/solver.hpp` | Core solver interface |
| `src/model.hpp` | Problem formulation |
| `python_api/solver_py.cpp` | Python bindings |
| `python/cuopt/__init__.py` | Python package init |

### Example: Adding New Solver Option

1. Add option to `Model` class:
   ```cpp
   // src/model.hpp
   class Model {
       double tolerance;  // New option
   };
   ```

2. Expose to Python:
   ```cpp
   // python_api/solver_py.cpp
   .def("set_tolerance", &Model::set_tolerance)
   ```

3. Test in Python:
   ```python
   model = cuopt.modeling.Model()
   model.set_tolerance(1e-7)
   ```

---

## Testing Guidelines

### Unit Tests (C++)

```cpp
// tests/test_solver.cpp
#include <gtest/gtest.h>
#include "cuopt/solver.hpp"

TEST(SolverTest, SimpleLp) {
    Model model;
    // Create LP
    auto x = model.add_variable(...);
    model.minimize(x);
    
    // Solve
    Solver solver;
    auto result = solver.solve(model);
    
    // Assert
    EXPECT_EQ(result.status, SolverStatus::Optimal);
    EXPECT_NEAR(result.objective, 0.0, 1e-6);
}
```

### Integration Tests (Python)

```python
# python/tests/test_integration.py
import pytest
import cuopt

def test_simple_lp():
    model = cuopt.modeling.Model()
    x = model.continuous_variable(name="x")
    model.minimize(x)
    
    solver = cuopt.Solver()
    result = solver.solve(model)
    
    assert result.status in ["Optimal", "Suboptimal"]
    assert abs(result.objective_value) < 1e-5
```

### Running Tests

```bash
# C++ unit tests
cd build && ctest

# Python tests
pytest python/tests/ -v

# Specific test
pytest python/tests/test_api.py::test_solve_milp

# With coverage
pytest --cov=cuopt python/tests/
```

---

## Contribution Guidelines

### Code Style

- **Python**: PEP 8 (use `black` for formatting)
- **C++**: Follow existing style (clang-format in CMakeLists.txt)
- **Comments**: Document WHY, not WHAT; let code explain WHAT

### Testing Requirement

- ✓ All new features must have tests
- ✓ All bug fixes must include regression test
- ✓ Code coverage should not decrease
- ✓ Tests must pass locally before PR

### Documentation

- ✓ Update docstrings for new/modified functions
- ✓ Update README if public API changes
- ✓ Add example if introducing new concept
- ✓ Update CHANGELOG.md with user-facing changes

### Pre-Submission Checklist

- [ ] Tests pass: `pytest` and `ctest`
- [ ] Linting passes: `black` and `flake8`
- [ ] No merge conflicts with `main`
- [ ] PR description explains motivation
- [ ] Commits are logical (not "fixup" commits)
- [ ] No large data files or binaries committed

---

## Debugging

### Enable Debug Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Now solver will print debug info
result = solver.solve(model)
```

### Common Issues

**Problem**: "CUDA not found during build"  
**Solution**: Specify CUDA path: `cmake .. -DCUDA_TOOLKIT_ROOT_DIR=/opt/cuda`

**Problem**: "Python bindings not rebuilt"  
**Solution**: `cmake --build . --target python` (explicit rebuild)

**Problem**: "Test fails with 'no module cuopt'"  
**Solution**: `export PYTHONPATH=./build/python:$PYTHONPATH`

---

## Known Limitations

### Development Complexity

**Issue**: Building from source requires CUDA/compiler knowledge

**Mitigation**: Use Docker: `docker build -f Dockerfile.dev .`

### Testing Coverage

**Issue**: Some numerical algorithms hard to test comprehensively

**Mitigation**: Use property-based testing and fuzzing

---

## Next Steps

- **Report issues**: [cuOpt GitHub Issues](https://github.com/NVIDIA/cuopt/issues)
- **Discuss features**: [cuOpt Discussions](https://github.com/NVIDIA/cuopt/discussions)
- **Review PRs**: Help review community contributions

---

**Last Updated**: 2026-07-24  
**Status**: published  
**Version**: 1.0.0
