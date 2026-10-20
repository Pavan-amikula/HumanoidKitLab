# HumanoidKitLab: project handoff for resume writing

## Instructions for the resume writer

Use this as the factual source. Tailor the wording to robotics, computer vision, automation, machine learning or software engineering roles. Use specific verbs and relevant keywords. Do not invent hardware experience, change the numbers or present this independent project as an employer-sponsored thesis. No wording guarantees selection.

## Project identity

- Candidate: Amikula Pavan Kumar Goud.
- Project: **HumanoidKitLab — Vision-Guided Industrial Kitting with Classical and Learned Control**.
- Repository: https://github.com/Pavan-amikula/HumanoidKitLab
- Type: independent robotics/AI portfolio project; implemented and tested CPU kinematic simulation prototype.
- Context: inspired by an industrial humanoid-kitting thesis description covering computer vision, part manipulation, movement between stations, control-method comparison, integration and evaluation.
- Demonstration: `docs/media/humanoidkit_demo.mp4`; animated preview and outputs in the README.

## What the project does

A simulated humanoid surrogate receives a four-slot assembly order: two bolts, one bracket and one spacer. An extra bracket remains as a distractor. The system observes the rack, checks inventory, plans a route, docks, picks a required part, lifts/transfers/rotates it, places it in its assigned tray slot and verifies the result. Completion requires all four slots to pass fresh camera checks and a final simulation-truth evaluation guard.

The desktop interface shows a live 3D workspace, perception image, task state, grasp counts and recovery events. A CLI supports headless reproducible experiments. An optional HTTP dashboard is included; only startup and in-process controls were validated because loopback client connections were blocked during development. The actual desktop widgets were exercised.

## Implemented technical work

**Perception:** synthetic RGB-D rendering; chromaticity/color masks; connected-component analysis; calibrated depth unprojection; 3D centroids; PCA-based planar yaw. The detector receives pixels, depth and calibration, never simulator object poses. This is a color-coded controlled baseline, not a trained general industrial detector or full 6D estimator. A pinhole RGB-D replay adapter and BOP annotation exporter were tested using fixtures. No physical camera driver or public-data detector was validated.

**Navigation:** metric four-connected A*, robot-footprint obstacle inflation, route rejection and docking. Base motion is a planar position/heading proxy. There is no biped walking gait or balance controller.

**Manipulation:** analytic inverse/forward kinematics for a two-link spatial arm with shoulder azimuth and wrist yaw; approach, lift, park, transfer, rotation and placement sequences; reachability checks; sampled arm-centreline furniture checks; bounded commands. Grasping uses explicit geometric position/yaw criteria and assisted attachment, without contact forces, friction, torques or rigid-body dynamics.

**Learning:** a PyTorch behaviour-cloned action-chunking MLP with 7 → 96 → 96 → 24 dimensions and Tanh nonlinearities predicts six future four-dimensional commands: Cartesian hand increments plus wrist-yaw increment. Inputs are normalized target-position error, wrapped target-yaw error and hand position relative to the shoulder. Actions are normalized during training and bounded during execution.

The controller executes the first action of each predicted chunk, then recomputes using feedback: state-based imitation learning with receding-horizon control. Camera-derived target poses feed the task, but the network does not consume raw images. It is not ACT's Transformer/CVAE or Diffusion Policy.

Generated demonstrations from the analytic expert in an isolated reachable arm workspace. Used AdamW, action-regression losses, fixed seeds, episode-separated splits and validation-based checkpoint selection. The model imitates an existing classical expert; no superiority over the expert is claimed.

**Control comparison:** classical analytic servo, learned controller without silent fallback, and hybrid learned control with explicit counted classical recovery after timeout. All share perception, navigation, task sequencing, command limits and verification. Tests freeze the learned controller to establish that pure learned execution fails and hybrid execution records and performs recovery.

**Integration:** an explicit task supervisor handles stock checks, part location, navigation, docking, manipulation, grasp verification, placement, final verification, bounded recovery, operator stop, completion and failure. Added independent image-based slot checks, JSON evidence, a socket-free Tkinter desktop application, PIL scene renderer, CLI, optional HTTP interface, dataset tools, video renderer and automated tests.

## Exact metrics

| Evidence | Verified value | Interpretation |
|---|---:|---|
| Automated tests | **26 passed** | Geometry, perception, workflows, recovery, split integrity and adapters |
| Paired kitting trials | **72** | 3 controllers × 8 conditions × 3 held-out layout seeds |
| Feasible trials | **36 / 36 completed** | Normal, rotated, low-light/noise and missed-grasp recovery; four verified slots |
| Infeasible/faulted trials | **36 / 36 correctly stopped** | Occluded/missing stock, blocked routes, dropped parts; not completed kits |
| Training / validation / action-test episodes | **240 / 40 / 40** | Entire generated episodes assigned to separate splits |
| Training / validation / action-test records | **3,940 / 671 / 681** | Generated states/actions, not images or real robot demonstrations |
| Predicted horizon | **6 commands** | First action executed before the next feedback update |
| Epochs | **120** | Checkpoint chosen using validation chunk MSE |
| Best validation chunk MSE | **0.0042378502** | Normalized action regression error |
| Held-out action-test chunk MSE | **0.0043108989** | Separate regression loss, not grasp accuracy |
| Runtime | **CPU training and inference** | No NVIDIA GPU required for the validated prototype |

Train, validation, action-test and kitting-evaluation episode/layout seeds are separate. Three layouts per condition are a small controlled study, not broad industrial validation. Wilson confidence intervals appear in the JSON report. Modeled duration assumes motion speeds and control periods; do not claim measured physical cycle-time improvement or hard real-time deadlines.

## Resume wording: three strong bullets

**HumanoidKitLab | Robotics, Computer Vision & Imitation Learning | Python, PyTorch, NumPy, SciPy**

- Built an integrated industrial-kitting simulation combining RGB-D part localization, footprint-aware A* navigation, analytic inverse kinematics and closed-loop pick–rotate–place control with independent kit verification.
- Trained a behaviour-cloned six-action-chunk PyTorch controller on 240 generated demonstration episodes and compared classical, learned and hybrid control using episode-separated validation and held-out evaluation.
- Validated the CPU prototype with 26 automated tests and 72 paired trials: completed all 36 feasible kits and correctly stopped all 36 missing-stock, occlusion, blocked-route and dropped-part cases.

## Compact resume wording

- Developed a CPU industrial-kitting simulator integrating RGB-D perception, A* planning, inverse kinematics, learned action chunks and camera-based placement verification.
- Evaluated three control strategies across 72 paired simulation trials: 36/36 feasible-kit completions, 36/36 correctly stopped faulted orders and 26 passing automated tests.

## Interview explanation

"I built a software prototype of a humanoid robot preparing an assembly kit. It finds colored parts with a simulated depth camera, plans routes around obstacles, moves an articulated arm, picks and rotates parts, and verifies the tray with a fresh image. I compared a programmed controller with a neural controller trained from generated demonstrations and a hybrid with explicit recovery. The main work was integrating the whole sequence and handling failures, rather than only training a model. It runs on CPU. These are kinematic simulation results; physical G1 walking and gripping remain the next integration stage."

## Relevant supported keywords

Python; PyTorch; NumPy; SciPy; Pillow; Tkinter; computer vision; RGB-D perception; segmentation; connected components; depth unprojection; camera calibration; 3D localization; planar orientation estimation; PCA; robotic manipulation; inverse kinematics; forward kinematics; A* path planning; obstacle inflation; footprint-aware navigation; docking; pick and place; part rotation; robot programming; task-state machines; system integration; imitation learning; behaviour cloning; action chunking; MLP; AdamW; receding-horizon control; closed-loop control; bounded recovery; fault injection; independent verification; industrial kitting; reproducible evaluation; episode-level splitting; model validation; CPU inference; structured telemetry; automated testing.

Use the relevant keywords naturally rather than inserting every term into one bullet.

## Do not claim these as completed work

Physical Unitree G1 deployment; ROS 2; MoveIt; Nav2; MuJoCo/Isaac Sim execution; reinforcement learning; ACT implementation; Diffusion Policy implementation; VLA models; biped locomotion; force control; contact dynamics; sim-to-real transfer; commercial deployment; full 6D estimation; real-camera validation; T-LESS/ITODD model training.

This is an engineering integration/evaluation project using established methods. Do not claim a novel algorithm, state-of-the-art performance, published paper, accepted thesis, industry employment, Volvo/MDU collaboration or measured business impact. Its strengths are a runnable workflow, trained policy, failure handling, reproducible experiments and inspectable evidence.
