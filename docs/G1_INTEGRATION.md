# What remains to connect the actual MITC G1

The current project is deliberately a local kinematic demonstrator. There is no implemented physical Unitree backend, no robot networking and no switch that enables real motors. Replacing it with real control requires implementation and validation work, not just changing a flag.

## Required lab information

- Exact G1 variant and arm/wrist degrees of freedom.
- Installed hands or grippers and their command/state interfaces.
- Camera/depth devices, mounting and timestamp access.
- Available locomotion and arm control interfaces in the installed firmware.
- Rack, tray, part CAD/measurements, payloads and placement tolerances.
- A validated robot control/stop procedure provided by the lab.

## Software contracts to implement

| Module | Required input/output | Current implementation | Required replacement |
|---|---|---|---|
| Observation | Timestamped image, depth, camera calibration | Synthetic orthographic RGB-D | Actual calibrated RGB-D acquisition with frame age checks |
| Robot state | Joint positions/velocities, base pose, hand state | Analytic surrogate state | SDK state subscription with joint-name and unit mapping |
| Part perception | Identity, pose, confidence, timestamp | Color mask, centroid, tabletop yaw | Industrial detector and object-pose estimation with uncertainty |
| Base motion | Path/velocity command and reached/failed feedback | Footprint-clear planar point steps | Localized base navigation connected to a validated G1 gait controller |
| Arm motion | Bounded desired joint/hand targets and execution feedback | Analytic IK; direct kinematic state update | Actual G1 IK, joint limits, collision planning and controller |
| Grasp check | Independent held-object evidence | Geometric proximity/yaw test and assisted attachment | Hand/contact sensing and/or visual tracking |
| Placement check | Independent identity, quantity and pose evidence | Overhead pixel check plus evaluation-only truth guard | Real camera evidence with calibrated tolerances |
| Task supervisor | Outcomes, timeouts, recovery and operator stops | Implemented and tested for simulation | Integrate hardware feedback and timing; validate every state transition |

## Coordinate and control requirements

Specify each transform direction explicitly, for example `T_world_camera`, `T_world_base` and `T_base_tool`. Keep lengths in metres and angles in radians. Record calibration provenance and timestamps.

The simulation's three-joint arm plus wrist is not the G1 joint chain. Its IK, reach, joint angles and learned checkpoint must not be sent to the G1. Train or retarget a policy for the actual observation/action specification.

Task supervision and model inference must remain separate from the high-rate joint-control loop. Use the official controller interfaces and appropriate command/state watchdogs; this desktop event loop cannot replace them.

Start with stationary, single-part picking, then multi-part kitting, then separate walking and docking. Simultaneous walking and manipulation should be a later experiment after balance and manipulation are independently validated.

## Validation ladder

1. Verify calibrated perception on recorded real frames.
2. Load the exact robot and hand in a contact-capable simulator.
3. Validate joint mapping, limits, reachable poses and arm/furniture collisions.
4. Demonstrate stationary physical grasps with lab supervision.
5. Collect independent demonstrations and evaluate classical versus learned control.
6. Integrate walking, docking and stationary picking into complete physical orders.
7. Report kit success, errors, cycle time, latency and interventions separately from all synthetic results.
