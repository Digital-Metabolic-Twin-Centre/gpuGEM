# cuOpt Server API & Deployment

> **Skill ID**: `cuopt-server-api-python`  
> **Category**: deployment  
> **Difficulty**: intermediate  
> **Time**: 30 minutes  
> **Prerequisites**: `cuopt-install`, `cuopt-numerical-optimization-api`

---

## Overview

Deploy cuOpt as a remote optimization service and build client applications that communicate with it. Learn server setup, client APIs, and production deployment patterns.

**Target Audience**: DevOps engineers and backend developers deploying optimization services

---

## Concepts

### Server Architecture

cuOpt Server exposes a simple HTTP API:

1. **Client** submits optimization problem (JSON)
2. **Server** receives request, queues job
3. **Server** solves problem on GPU(s)
4. **Client** polls or waits for result
5. **Server** returns solution (JSON)

**Benefits**:
- Decouple client from GPU requirements
- Share GPU across multiple clients
- Scale horizontally (load balancer + multiple servers)
- Language-agnostic (any HTTP client works)

### Request/Response Format

**Request (JSON)**:
```json
{
  "problem": {
    "objective": "minimize",
    "terms": [{"coeff": 3, "vars": ["x"]}, ...],
    "constraints": [...],
    "variables": [...]
  }
}
```

**Response (JSON)**:
```json
{
  "status": "Optimal",
  "objective_value": 42.5,
  "solution": {"x": 10, "y": 5},
  "solve_time": 0.125
}
```

---

## API Reference

### Starting Server

```bash
# Basic start
cuopt-server --host 0.0.0.0 --port 5000

# With GPU specification
cuopt-server --host 0.0.0.0 --port 5000 --gpus 0,1

# Docker start
docker run --gpus all -p 5000:5000 nvcr.io/nvidia/cuopt:latest
```

### Client: Submit Problem

```python
import requests
import json

problem_json = {
    "objective": "minimize",
    "variables": [
        {"name": "x", "type": "continuous", "bounds": [0, 10]},
        {"name": "y", "type": "continuous", "bounds": [0, 10]}
    ],
    "constraints": [
        {"expression": "x + y <= 15", "name": "limit"}
    ],
    "objective_expr": "3*x + 5*y"
}

response = requests.post(
    "http://localhost:5000/optimize",
    json=problem_json,
    timeout=30
)

result = response.json()
print(f"Status: {result['status']}")
print(f"Solution: {result['solution']}")
```

### Client: Async with Polling

```python
import requests
import time

# Submit job
response = requests.post(
    "http://localhost:5000/optimize/async",
    json=problem_json
)
job_id = response.json()["job_id"]

# Poll for result
while True:
    status_response = requests.get(
        f"http://localhost:5000/jobs/{job_id}"
    )
    job_status = status_response.json()
    
    if job_status["state"] in ["done", "error"]:
        break
    
    time.sleep(1)

print(f"Result: {job_status['result']}")
```

---

## Examples

### Example 1: Server Setup (Docker)

```bash
#!/bin/bash
# Start cuOpt server in container

docker run \
  --name cuopt-server \
  --gpus all \
  -p 5000:5000 \
  -e CUOPT_LOG_LEVEL=info \
  nvcr.io/nvidia/cuopt:latest

# Verify server is running
curl http://localhost:5000/health
# Expected: {"status": "running"}
```

### Example 2: Python Client - Solve LP

```python
import requests
import json

def solve_problem_via_server(host="localhost", port=5000):
    """Submit LP problem to cuOpt server and get solution."""
    
    problem = {
        "problem_type": "LP",
        "objective": "maximize",
        "objective_expr": "3*x + 5*y",
        "variables": [
            {"name": "x", "type": "continuous", "lower_bound": 0},
            {"name": "y", "type": "continuous", "lower_bound": 0}
        ],
        "constraints": [
            {"expression": "2*x + 3*y <= 40", "name": "labor"},
            {"expression": "4*x + 8*y <= 100", "name": "wood"}
        ]
    }
    
    url = f"http://{host}:{port}/optimize"
    try:
        response = requests.post(url, json=problem, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        # Validate result
        assert result["status"] in ["Optimal", "Suboptimal"], \
            f"Solver failed: {result['status']}"
        
        print(f"✓ Status: {result['status']}")
        print(f"  Objective: {result['objective_value']:.2f}")
        print(f"  Solution: {result['solution']}")
        
        return result
        
    except requests.exceptions.ConnectionError:
        print(f"✗ Cannot connect to server at {url}")
        return None

# Usage
if __name__ == "__main__":
    solve_problem_via_server()
```

### Example 3: Async Client with Error Handling

```python
import requests
import time

def solve_async(problem, host="localhost", port=5000, timeout=60):
    """Submit job asynchronously and poll for result."""
    
    url = f"http://{host}:{port}/optimize/async"
    
    # Submit job
    response = requests.post(url, json=problem, timeout=10)
    response.raise_for_status()
    
    job_id = response.json()["job_id"]
    print(f"Job {job_id} submitted")
    
    # Poll for result
    start_time = time.time()
    while time.time() - start_time < timeout:
        status_url = f"http://{host}:{port}/jobs/{job_id}"
        status_response = requests.get(status_url, timeout=10)
        status_response.raise_for_status()
        
        job_status = status_response.json()
        
        if job_status["state"] == "running":
            print(f"  Still solving... ({time.time() - start_time:.1f}s)")
            time.sleep(2)
        
        elif job_status["state"] == "done":
            result = job_status["result"]
            print(f"✓ Solved in {result.get('solve_time', 0):.3f}s")
            return result
        
        elif job_status["state"] == "error":
            print(f"✗ Error: {job_status['error']}")
            return None
    
    print(f"✗ Timeout after {timeout}s")
    return None
```

---

## Common Patterns

### Pattern 1: Load Balancing

```python
# Round-robin across multiple servers
servers = ["server1:5000", "server2:5000", "server3:5000"]
selected_server = servers[job_count % len(servers)]

response = requests.post(
    f"http://{selected_server}/optimize",
    json=problem
)
```

### Pattern 2: Result Caching

```python
import hashlib

def get_solution(problem):
    # Check cache
    problem_hash = hashlib.md5(
        str(problem).encode()
    ).hexdigest()
    
    cached = cache.get(problem_hash)
    if cached:
        return cached
    
    # Solve and cache
    result = solve_via_server(problem)
    cache.set(problem_hash, result)
    return result
```

### Pattern 3: Connection Retry

```python
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def create_session_with_retries():
    session = requests.Session()
    
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504]
    )
    
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    
    return session

# Usage
session = create_session_with_retries()
response = session.post("http://server:5000/optimize", json=problem)
```

---

## Known Limitations

### No Built-in Authentication (v0.4.x)

**Issue**: cuOpt server has no authentication; any client can submit jobs

**Workaround**: 
- Use network firewall to restrict access
- Deploy behind reverse proxy (nginx) with authentication
- Use VPN for secure network access

### Memory Limits

**Issue**: Server shares GPU memory across concurrent jobs

**Workaround**: 
- Monitor server load
- Implement request queue with max concurrency
- Use multiple server instances for scaling

### Timeout Handling

**Issue**: Long-running problems may timeout; connection may be lost

**Workaround**: 
- Use async API with polling for long problems
- Increase timeout settings
- Implement automatic retry logic on client

---

## Next Steps

- **Want routing?** See `cuopt-routing-api-python` for routing server jobs
- **Production monitoring?** Implement health checks and logging
- **Scaling?** Use Kubernetes for container orchestration

---

**Last Updated**: 2026-07-24  
**Status**: published  
**Version**: 1.0.0
