# Validation record

Validated on 20 October 2026 in the supplied Windows workspace.

## Completed checks

- 26 tests passed. See `test_results.txt` for the recorded output.
- The actual Tkinter widgets were created and refreshed using a completed learned-controller trial. See `desktop_smoke.json`.
- The desktop renderer produced `scene_preview.png`; its output was visually inspected.
- A paired evaluation executed 72 orders: three controllers, eight conditions and three independent layout seeds.
- All 36 feasible orders completed with four correct slots. This covers normal layouts, rotated parts, low light/noise and recovery from an injected missed grasp.
- All 36 infeasible/faulted orders stopped without claiming a complete kit. This covers missing stock, fully occluded required stock, blocked routes and an injected dropped part.
- The learned method completed these feasible orders without classical fallbacks. Separate fault tests freeze the learned policy and verify that pure learned control fails while hybrid control records and executes a classical fallback.
- Generated training, validation and action-test episode IDs do not overlap.
- BOP annotation export and calibrated RGB-D file replay were tested with synthetic fixtures.

## Important limits

These are small, controlled kinematic experiments with geometric assisted grasps. They do not demonstrate industrial deployment, real contact/grip mechanics, biped stability, general part recognition or G1 control. No claim is made that the learned controller outperforms the analytic expert it imitates.

Modeled cycle time is based on explicit assumed speeds and control periods. It is separate from measured software latency and wall time. Three layout seeds per condition provide limited statistical coverage; Wilson intervals are included in the JSON report.

The optional HTTP server started, and its in-process session controls passed tests. This session blocked loopback client sockets, so end-to-end browser operation was not verified. The tested desktop app does not use sockets.

MuJoCo was not available, and its installation attempt failed because network resolution was unavailable. There is no simulated claim that a physics engine or Unitree SDK was used.
