# Measured kinematic simulation evaluation

kinematic synthetic simulation, assisted grasps, no rigid-body physics or gait

modeled_cycle_seconds uses assumed 0.25m/s base speed and 0.15s control period; not measured physical cycle time

Missing/occluded stock, blocked routes and dropped parts should stop without a completion claim.

| Method | Scenario | Completed / attempted | Retries | Classical fallbacks |
|---|---|---:|---:|---:|
| classical | normal | 3/3 | 0 | 0 |
| classical | rotated | 3/3 | 0 | 0 |
| classical | lighting | 3/3 | 0 | 0 |
| classical | occluded | 0/3 | 0 | 0 |
| classical | missing | 0/3 | 0 | 0 |
| classical | blocked | 0/3 | 0 | 0 |
| classical | grasp_failure | 3/3 | 3 | 0 |
| classical | drop | 0/3 | 0 | 0 |
| learned | normal | 3/3 | 0 | 0 |
| learned | rotated | 3/3 | 0 | 0 |
| learned | lighting | 3/3 | 0 | 0 |
| learned | occluded | 0/3 | 0 | 0 |
| learned | missing | 0/3 | 0 | 0 |
| learned | blocked | 0/3 | 0 | 0 |
| learned | grasp_failure | 3/3 | 3 | 0 |
| learned | drop | 0/3 | 0 | 0 |
| hybrid | normal | 3/3 | 0 | 0 |
| hybrid | rotated | 3/3 | 0 | 0 |
| hybrid | lighting | 3/3 | 0 | 0 |
| hybrid | occluded | 0/3 | 0 | 0 |
| hybrid | missing | 0/3 | 0 | 0 |
| hybrid | blocked | 0/3 | 0 | 0 |
| hybrid | grasp_failure | 3/3 | 3 | 0 |
| hybrid | drop | 0/3 | 0 | 0 |
