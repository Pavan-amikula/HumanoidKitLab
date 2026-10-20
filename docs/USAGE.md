# HumanoidKitLab

**A working CPU kinematic research demonstrator for humanoid industrial kitting.**

The application assembles a four-slot kit from a rack, using rendered RGB-D observations, obstacle-aware base navigation, an articulated arm, classical or learned control, grasp checks, camera-based placement verification, bounded recovery and recorded experiments.

The current order is two bolts, one bracket and one spacer. There is an extra bracket as a distractor. Trials vary part position/orientation and include lighting noise, occlusion, missing stock, a blocked route, a missed grasp and a dropped part.

## Run on this laptop

The required libraries are already present in the environment used to build the project. The trained policy is included. **You do not need to retrain it or download a dataset.**

1. Open this folder in File Explorer.
2. Double-click **Start.cmd**.
3. Choose a controller and test condition.
4. Click **New trial**, then **Run kit**.
5. Drag the 3D workspace to orbit the view. Use Pause, Step and Stop to inspect execution.

Or, in PowerShell from this folder:

```powershell
python app.py desktop
```

The desktop app uses Tkinter and needs no network, web browser, Docker, NVIDIA GPU or local service. Logs are saved in `runs/`.

For a clean machine, use Python 3.11–3.13 with Tkinter and install `requirements.txt` in a virtual environment. CPU PyTorch installation can be larger than the project itself; use the already installed environment on this laptop. Tested environment versions are recorded in `artifacts/environment.json`.

## What is implemented

| Job requirement | Implemented capability | Boundary of evidence |
|---|---|---|
| Identify parts and positions | Independent color-coded RGB-D pixel detector; calibrated 3D centroid and planar yaw estimation | Controlled synthetic colors, known tabletop; not a trained industrial detector or arbitrary 6D object pose |
| Pick, rotate and place | Three-joint analytic arm IK plus wrist yaw; approach/lift/transfer/place motions; geometric grasp verification | Custom kinematic surrogate, assisted attachment; no physical grip, friction or torque model |
| Locomotion and orientation | A* route planning with base-footprint inflation; heading follows movement; stop before manipulation | Planar base-position proxy; no biped gait, balance controller or real walking |
| Traditional control | Bounded Cartesian visual-target servo, analytic IK and explicit task supervisor | Executed and evaluated locally |
| AI control | Trained behaviour-cloned six-action-chunk MLP; closed-loop receding-horizon execution | Generated state-action demonstrations, not ACT, a VLA or a G1-trained policy |
| System integration | One task supervisor connects observation, navigation, manipulation, verification and recovery | Working local desktop app and headless CLI |
| Industrial evaluation | Paired synthetic trials, fault scenarios, timings, logs, success counts and Wilson intervals | Small controlled simulation study; no physical industrial validation |

**Physical Unitree G1 deployment and rigid-body simulation are not implemented or validated.** A MuJoCo install was attempted during development, but package-network access was unavailable. This build does not silently substitute a fake MuJoCo or G1 backend.

## Controllers

- **classical:** computes bounded Cartesian and wrist corrections directly from target error.
- **learned:** executes the first action of the trained policy's predicted six-action chunk, then observes state again. It fails if it cannot reach the target within its command budget. There is no silent classical fallback.
- **hybrid:** uses the same learned policy and explicitly logs classical recovery after a learned-controller timeout.

The network receives target position error, wrapped wrist yaw error and hand position relative to the shoulder. Targets come from the perception module or fixed calibrated tray slots. The network does not consume raw images. Gripper opening/closing and the task sequence remain conventional in all three methods.

Training data contain 240 training, 40 validation and 40 held-out test episodes. Split identity is the entire generated episode, not individual samples. Episode IDs, NPZ files, checkpoint and training history are included in `artifacts/`. The MLP imitates the analytic servo, so the experiments do not establish an advantage over that expert.

## Experiments and commands

```powershell
# One full order without a GUI
python app.py demo --method learned --scenario rotated --seed 4101

# Fault recovery
python app.py demo --method hybrid --scenario grasp_failure --seed 4101

# Tests
python -m unittest discover -s tests -v

# Reproduce paired experiments: 3 methods × 8 conditions × 3 seeds
python app.py evaluate --seeds 4101 4102 4103

# Optional bounded CPU retraining; not required to use the application
python app.py train --epochs 120

# Create and update the actual desktop widgets without leaving a window open
python app.py desktop --smoke-test
```

`demo` returns exit code 0 on verified completion and 2 on an incomplete/failed trial. Missing stock, obstructed stock, blocked paths and dropped parts should not produce a completion claim. `evaluate` successfully writes a report even when some individual orders correctly fail.

Results are in [`results/RESULTS.md`](../results/RESULTS.md) and `results/evaluation.json`. See `results/test_results.txt` and `results/desktop_smoke.json` for recorded checks. `results/scene_preview.png` is rendered by the same scene renderer used by the desktop UI.

Modeled duration assumes a base speed of 0.25 m/s, a 0.15 s arm-command period and 0.5 s grip/release operations. It is **not a measured physical robot cycle time**. Wall-clock processing and control/perception latencies are separately measured. This is a soft real-time interactive demonstration, not a hard real-time system.

## Optional browser dashboard

```powershell
python app.py serve
```

Open `http://127.0.0.1:8765` in your browser. The server only binds loopback. Its UI offers the same scenarios and controllers, plus JSON reports. This development session blocked loopback client connections, so the desktop app is the verified default. Server startup and in-process session controls are checked; end-to-end browser operation could not be verified here.

## External data adapters

The project does not download public datasets automatically.

Export an existing BOP-format scene's annotations:

```powershell
python app.py export-bop --scene "D:\datasets\tless\train_primesense\000001" --output bop_annotations.json
```

Replay an existing RGB image and NumPy depth map with calibrated pinhole or synthetic orthographic camera parameters:

```powershell
python -m tools.replay_rgbd --rgb frame.png --depth depth.npy --calibration camera.json
```

The replay detector expects the project's color-coded parts and planar tabletop orientation. This input adapter does not turn it into a general T-LESS/ITODD detector. Public perception datasets have not been downloaded, used in training or evaluated in the reported results.

## Project layout

```text
app.py                       CLI entry point
Start.cmd / Start.ps1         Desktop launchers
humanoidkit/world.py          Kinematic scene, arm IK, simulated outcome checks
humanoidkit/vision.py         Synthetic RGB-D camera and pixel detector
humanoidkit/planning.py       A* with footprint inflation
humanoidkit/learning.py       Demonstrations, training and learned inference
humanoidkit/engine.py         Task supervisor, recovery and experiment logs
humanoidkit/desktop.py        Socket-free Tkinter application
humanoidkit/render.py         Interactive-view scene renderer
humanoidkit/server.py         Optional local HTTP dashboard
humanoidkit/rgbd.py           Calibrated external RGB-D replay
web/index.html               Browser dashboard, no CDN dependencies
artifacts/                   Included trained model and generated datasets
results/                     Actual experiment outputs and validation evidence
tests/                       Integration, perception, geometry and recovery tests
docs/RESEARCH.md              Primary sources and research decisions
docs/G1_INTEGRATION.md        Remaining hardware work and capability contracts
```

The research sources and precise remaining G1 requirements are documented rather than presented as completed integrations.
