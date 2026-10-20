# Research basis and implementation decisions

Source review: 20 October 2026. The job description was supplied by the user. This document distinguishes existing upstream capabilities from code implemented in this repository.

## Primary sources

1. **Unitree Robotics: SDK2 Python.** https://github.com/unitreerobotics/unitree_sdk2_python
   Official robot communication library. The README documents Python and CycloneDDS dependencies. Intended use: a future robot-state/command adapter. This repository does not currently import the SDK or send robot commands.

2. **Unitree Robotics: MuJoCo simulator.** https://github.com/unitreerobotics/unitree_mujoco
   Official low-level simulation bridge. The README distinguishes G1 `unitree_hg` messages from other robot message types. Intended use: rigid-body validation with the exact G1 model/controller. It is not installed in this build.

3. **Unitree Robotics: XR teleoperation.** https://github.com/unitreerobotics/xr_teleoperate
   Relevant reference for collecting robot-specific arm/hand demonstrations. Hand type and 23/29-DoF configuration must match the lab's robot. No XR device or physical demonstration was used for the included dataset.

4. **Hugging Face: LeRobot Unitree G1 documentation.** https://huggingface.co/docs/lerobot/unitree_g1
   Documents G1 simulation, controller and teleoperation integration. Its installation guide also identifies special arm-IK dependencies. This is a future integration candidate, not an installed or validated backend in this project.

5. **Zhao et al. (RSS 2023), Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware.**
   Paper: https://arxiv.org/abs/2304.13705
   Author project: https://tonyzhaozh.github.io/aloha/
   Contribution relevant here: learning short sequences of manipulation actions from demonstrations. The included model borrows the action-chunking idea only. It is a small state-input MLP, not ACT's image-conditioned Transformer/CVAE and not an ACT reproduction. Published ALOHA success rates do not describe this robot or project.

6. **Chi et al. (RSS 2023; IJRR 2024), Diffusion Policy: Visuomotor Policy Learning via Action Diffusion.**
   Author project and papers: https://diffusion-policy.cs.columbia.edu/
   Relevant design: action-sequence prediction with feedback/receding-horizon execution. Suitable later comparator when robot-specific demonstrations and deployment timing are available. No diffusion model has been trained here.

7. **BOP benchmark datasets and toolkit.** https://bop.felk.cvut.cz/datasets/
   Defines industrial/object-pose benchmarks, camera parameters, object models, masks, bounding boxes and pose labels. The project's BOP exporter reads this annotation structure. It does not download data, train a detector or report BOP scores.

8. **MVTec ITODD.** https://www.mvtec.com/research-teaching/datasets/mvtec-itodd
   Industrial 3D detection/pose dataset. Appropriate future stress test for industrial parts. ITODD includes grayscale/depth observations; do not assume every BOP dataset is RGB. Dataset-specific terms must be checked before reuse. No ITODD data are in this distribution.

9. **MuJoCo Python and API documentation.**
   https://mujoco.readthedocs.io/en/stable/python.html
   https://mujoco.readthedocs.io/en/stable/APIreference/APIfunctions.html
   Reference for a later physics implementation, model loading, stepping, rendering and Jacobians. Local package installation failed because package-network resolution was unavailable; no physics results are claimed.

10. **Hugging Face: ACT documentation.** https://huggingface.co/docs/lerobot/act
    Practical reference for a future image-conditioned learned manipulation comparator. Training and latency on the lab's exact setup must be measured rather than inferred from upstream examples.

## Research question

For a fixed industrial kitting task, how do classical, learned and hybrid arm controllers compare in complete-kit reliability, intervention/recovery requirements and computational latency under changes in position, orientation and visibility?

The present implementation supports a small preliminary version of this comparison. It does not answer physical-robot feasibility, balance, force-control, commercial readiness or full sim-to-real transfer questions.

## Current experimental design

- Same generated rack layout, part identity, kit order and fault condition per evaluation seed across methods.
- Same perception algorithm, calibrated tray coordinates, navigation, geometry checks, command limits and task supervisor.
- Classical method: analytic target-error servo.
- Learned method: imitation of that servo using an MLP that predicts six future normalized Cartesian/wrist commands. Only the first is executed before feedback.
- Hybrid method: the learned method with explicit, counted classical fallback on a bounded timeout.
- Complete generated episodes are assigned to train, validation and test; no frame-wise random splitting.
- Checkpoint selection uses validation action-chunk MSE. The held-out action test and separate kitting layout seeds are not used for selection.
- All successful placements receive fresh image-based verification. Simulation ground truth provides an additional final evaluation guard and is never passed to the pixel detector.
- Infeasible/faulted trials remain in the results. A stopped order is not counted as a completed kit.

The simple colored geometry, fixed furniture, small part-position variation and assisted grasps make this an easy benchmark. High synthetic success cannot establish general industrial robustness. The learned policy imitates an available analytic controller, so parity rather than improvement is a reasonable outcome.

## Data provenance

The included datasets are generated by `humanoidkit/learning.py` in an isolated kinematic arm workspace. They contain seven-dimensional state/target features and six four-dimensional future action commands. They contain no camera images, physical robot trajectories, Volvo data or public-dataset material.

See the exact record counts, episode IDs, model settings and history in `artifacts/training_report.json`. Evaluation seeds are disjoint and recorded in `results/evaluation.json`.

## Next evidence needed

1. Train/evaluate an industrial part detector and pose estimator on a small permitted public dataset subset and own rack images.
2. Use the actual G1 geometry and controller in a contact-capable simulator; replace assisted attachment with measured contact/grip outcomes.
3. Record timestamp-aligned images, joint state and commands from task-specific demonstrations.
4. Train ACT or a similar image-conditioned policy with the same independent episodes and bounded deployment interface.
5. Validate real stationary picking before linking navigation and manipulation.
6. Compare physical kit trials under the same conditions, recording all failures and operator interventions.
