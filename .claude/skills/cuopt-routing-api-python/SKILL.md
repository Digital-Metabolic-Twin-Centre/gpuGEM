# cuOpt Routing API (Vehicle Routing Problems)

> **Skill ID**: `cuopt-routing-api-python`  
> **Category**: api-reference  
> **Difficulty**: intermediate  
> **Time**: 20 minutes  
> **Prerequisites**: `cuopt-install`, `cuopt-numerical-optimization-formulation`

---

## Overview

Solve vehicle routing problems (VRP), pickup-delivery, and logistics optimization using cuOpt's specialized routing solver. Learn to model locations, vehicles, time windows, and constraints.

**Target Audience**: Logistics and supply chain developers building routing solutions

---

## Concepts

### Vehicle Routing Problem (VRP)

**Goal**: Visit all locations with minimum cost (distance, time, vehicles)

**Components**:
- **Locations**: Warehouse, customers, delivery points (lat/lon)
- **Vehicles**: Trucks with capacity and constraints
- **Routes**: Assignment of locations to vehicles
- **Objective**: Minimize total distance, time, or vehicle count

### Common VRP Variants

| Type | Description | Use Case |
|------|-------------|----------|
| **VRP** | Visit all locations once | Delivery routes |
| **CVRP** | VRP with vehicle capacity | Truck loading limits |
| **PDVRP** | Pickup-delivery pairs | Package forward/return |
| **VRPTW** | VRP with time windows | Scheduled deliveries |
| **MDVRP** | Multiple depot locations | Regional distribution |

---

## API Reference

### Creating Routing Model

```python
import cuopt

model = cuopt.routing.RoutingModel()
```

### Adding Locations

```python
# Add customers with coordinates
locations = [
    (40.7128, -74.0060),  # NYC
    (34.0522, -118.2437), # LA
    (41.8781, -87.6298)   # Chicago
]

for i, (lat, lon) in enumerate(locations):
    model.add_location(
        name=f"customer_{i}",
        latitude=lat,
        longitude=lon
    )
```

### Adding Vehicles

```python
# Add vehicle with capacity
model.add_vehicle(
    name="truck_1",
    capacity=1000,  # kg
    fixed_cost=50,  # daily cost
    variable_cost=0.5  # per km
)
```

### Setting Time Windows

```python
model.add_time_window(
    location="customer_1",
    start_time=8,  # 8 AM
    end_time=12    # 12 PM
)
```

### Solving

```python
solver = cuopt.routing.RoutingSolver()
solution = solver.solve(model)

# Extract solution
for vehicle_id, route in solution.routes.items():
    print(f"{vehicle_id}: {' -> '.join(route)}")
    print(f"  Distance: {solution.distance[vehicle_id]} km")
    print(f"  Time: {solution.duration[vehicle_id]} min")
```

---

## Examples

### Example 1: Simple VRP (3 Vehicles, 10 Customers)

```python
import cuopt
from cuopt.routing import RoutingModel, RoutingSolver

# Create model
model = RoutingModel()

# Add locations (lat, lon)
locations = {
    "warehouse": (40.7128, -74.0060),
    "c1": (40.7150, -74.0050),
    "c2": (40.7160, -74.0040),
    "c3": (40.7170, -74.0030),
    # ... more customers
}

for name, (lat, lon) in locations.items():
    model.add_location(name=name, latitude=lat, longitude=lon)

# Add 3 vehicles
for i in range(3):
    model.add_vehicle(
        name=f"truck_{i}",
        capacity=500,  # kg capacity
        fixed_cost=40,
        variable_cost=0.3  # $/km
    )

# Set depot
model.set_depot("warehouse")

# Solve
solver = RoutingSolver(time_limit=10)
solution = solver.solve(model)

# Results
print(f"Status: {solution.status}")
print(f"Total distance: {solution.total_distance:.1f} km")
print(f"Total cost: ${solution.total_cost:.2f}")

# Validate solution
assert solution.status in ["Optimal", "Suboptimal"]
for vehicle_id, route in solution.routes.items():
    print(f"{vehicle_id}: {len(route)} stops")
```

### Example 2: Pickup-Delivery (PDVRP)

```python
import cuopt

model = cuopt.routing.RoutingModel(routing_type="pickup_delivery")

# Locations: warehouse, pickup points, delivery points
model.add_location("warehouse", 0, 0)
model.add_location("pickup_1", 1, 1)
model.add_location("delivery_1", 1.5, 1.5)
model.add_location("pickup_2", 2, 2)
model.add_location("delivery_2", 2.5, 2.5)

# Link pickup to delivery
model.add_pickup_delivery_pair(
    pickup="pickup_1",
    delivery="delivery_1",
    demand=100
)
model.add_pickup_delivery_pair(
    pickup="pickup_2",
    delivery="delivery_2",
    demand=150
)

# Add vehicles
model.add_vehicle("truck", capacity=500)

# Solve
solver = cuopt.routing.RoutingSolver()
solution = solver.solve(model)

# Results
print(f"Status: {solution.status}")
for vehicle, route in solution.routes.items():
    print(f"{vehicle}: {route}")
    print(f"  Total pickup: {sum_pickup(route)} kg")

# Validate: pickups before deliveries
assert all(
    route.index(pickup) < route.index(delivery)
    for pickup, delivery in solution.pairs
)
```

### Example 3: VRP with Time Windows

```python
import cuopt
import datetime

model = cuopt.routing.RoutingModel()

# Add locations
model.add_location("warehouse", 0, 0)
model.add_location("customer_1", 1, 0)
model.add_location("customer_2", 0, 1)

# Set time windows (hours since start of day)
model.add_time_window("customer_1", start_time=9, end_time=12)
model.add_time_window("customer_2", start_time=14, end_time=17)

# Service times
model.add_service_time("customer_1", duration=0.5)  # 30 min service
model.add_service_time("customer_2", duration=0.5)

# Add vehicle with start time
model.add_vehicle(
    "truck",
    capacity=1000,
    start_time=8  # 8 AM
)

# Solve
solver = cuopt.routing.RoutingSolver()
solution = solver.solve(model)

# Validate time windows
for vehicle, route in solution.routes.items():
    arrival_times = solution.arrival_times[vehicle]
    for location, arrival in zip(route, arrival_times):
        window = solution.time_windows[location]
        assert window['start'] <= arrival <= window['end'], \
            f"{location} arrival outside time window"

print(f"Status: {solution.status}")
```

---

## Common Patterns

### Pattern 1: Distance Matrix Input

```python
import numpy as np

# Pre-computed distance matrix
distances = np.array([
    [0, 10, 15, 20],
    [10, 0, 5, 12],
    [15, 5, 0, 8],
    [20, 12, 8, 0]
])

model = cuopt.routing.RoutingModel(
    distance_matrix=distances
)
# ... rest of model setup
```

### Pattern 2: Multi-Depot

```python
# Vehicles start/end at different depots
model.set_depot("depot_1", vehicles=[truck_1, truck_2])
model.set_depot("depot_2", vehicles=[truck_3])
```

### Pattern 3: Vehicle Specialization

```python
# Some vehicles can't visit certain locations
model.add_vehicle_restriction(
    vehicle="refrigerated_truck",
    allowed_locations=["cold_storage", "customer_A", "customer_B"]
)
```

---

## Known Limitations

### Precision & Rounding

**Issue**: Distance calculations use floating-point; may have rounding errors

**Workaround**: Scale distances to integers if possible

### Large Problems

**Issue**: Problems with 1000+ stops may take long to solve

**Workaround**: Use time limits, decompose into regional subproblems

### Non-Euclidean Distances

**Issue**: By default assumes Euclidean distance from coordinates

**Workaround**: Use custom distance matrix instead of lat/lon

---

## Next Steps

- **Multi-objective routing?** See `cuopt-multi-objective-exploration`
- **Server deployment?** See `cuopt-server-api-python` to expose routing as service

---

**Last Updated**: 2026-07-24  
**Status**: published  
**Version**: 1.0.0
