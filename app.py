"""CLI: desktop, serve, train, evaluate, demo, export-bop."""
from pathlib import Path
import argparse
import json
import math
import sys
import time

ROOT=Path(__file__).resolve().parent


def evaluate(seeds,output):
    import numpy as np
    from humanoidkit.engine import Engine
    from humanoidkit.world import SCENARIOS
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    rows=[]
    # Identical scenario and layout seeds across methods. Never used for policy fitting.
    for method in ("classical","learned","hybrid"):
        for scenario in SCENARIOS:
            for seed in seeds:
                e=Engine(seed,scenario,method,str(ROOT/"artifacts/policy.pt"))
                result=e.execute()
                e.save(output/"trials")
                rows.append(result)
                print(f"{method:9} {scenario:14} seed={seed} {result['status']:8} slots={result['correct_slots']}/4",flush=True)
    groups=[]
    for method in ("classical","learned","hybrid"):
        for scenario in SCENARIOS:
            subset=[r for r in rows if r["method"]==method and r["scenario"]==scenario]
            n=len(subset)
            wins=sum(r["success"] for r in subset)
            rate=wins/n
            # Wilson 95% interval; descriptive uncertainty for these synthetic trials only.
            z=1.96
            center=(rate+z*z/(2*n))/(1+z*z/n)
            half=z*math.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/(1+z*z/n)
            times=[r["modeled_cycle_seconds"] for r in subset if r["success"]]
            groups.append({"method":method,"scenario":scenario,"attempts":n,"completed_kits":wins,
                           "kit_success_rate":rate,"wilson_95":[max(0,center-half),min(1,center+half)],
                           "median_modeled_seconds_completed":float(np.median(times)) if times else None,
                           "retries":sum(r["retries"] for r in subset),
                           "fallbacks":sum(r["classical_fallbacks"] for r in subset)})
    report={"environment":"kinematic synthetic simulation, assisted grasps, no rigid-body physics or gait",
            "evaluation_seeds":list(seeds),"seeds_used_for_training":False,
            "infeasible_scenarios":["missing","occluded","blocked"],
            "verification_fault_scenario":"drop",
            "interpretation":"Correctly stopping an infeasible/faulted trial is expected; do not count it as a completed kit.",
            "timing":"modeled_cycle_seconds uses assumed 0.25m/s base speed and 0.15s control period; not measured physical cycle time",
            "groups":groups,"trials":rows}
    (output/"evaluation.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    lines=["# Measured kinematic simulation evaluation","",report["environment"],"",report["timing"],"",
           "Missing/occluded stock, blocked routes and dropped parts should stop without a completion claim.","",
           "| Method | Scenario | Completed / attempted | Retries | Classical fallbacks |",
           "|---|---|---:|---:|---:|"]
    for r in groups:
        lines.append(f"| {r['method']} | {r['scenario']} | {r['completed_kits']}/{r['attempts']} | {r['retries']} | {r['fallbacks']} |")
    (output/"RESULTS.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Saved {len(rows)} comparable trials to {output}",flush=True)


def export_bop(scene,output):
    """Export public BOP scene annotations as detector-training records.

    This reads existing data only; it downloads nothing and trains no detector.
    """
    scene=Path(scene)
    gt=json.loads((scene/"scene_gt.json").read_text(encoding="utf-8"))
    info=json.loads((scene/"scene_gt_info.json").read_text(encoding="utf-8"))
    cameras=json.loads((scene/"scene_camera.json").read_text(encoding="utf-8"))
    records=[]
    for image_id,objects in gt.items():
        for index,obj in enumerate(objects):
            metadata=info[image_id][index]
            records.append({"image_id":int(image_id),"object_id":obj["obj_id"],
                            "bbox_xywh":metadata["bbox_visib"],"visible_fraction":metadata["visib_fract"],
                            "rotation_model_to_camera":obj["cam_R_m2c"],
                            "translation_model_to_camera_mm":obj["cam_t_m2c"],
                            "camera":cameras[image_id],"source_scene":str(scene.resolve())})
    Path(output).write_text(json.dumps({"format":"BOP annotation export; no dataset evaluation performed",
                                       "records":records},indent=2),encoding="utf-8")
    print(f"Exported {len(records)} annotations to {output}")


def main():
    parser=argparse.ArgumentParser(description="HumanoidKitLab: local CPU kinematic research demonstrator")
    sub=parser.add_subparsers(dest="command",required=True)
    desktop=sub.add_parser("desktop")
    desktop.add_argument("--smoke-test",action="store_true")
    serve=sub.add_parser("serve")
    serve.add_argument("--port",type=int,default=8765)
    training=sub.add_parser("train")
    training.add_argument("--epochs",type=int,default=120)
    evaluation=sub.add_parser("evaluate")
    evaluation.add_argument("--seeds",type=int,nargs="+",default=[4101,4102,4103])
    evaluation.add_argument("--output",default="results")
    demo=sub.add_parser("demo")
    demo.add_argument("--method",choices=["classical","learned","hybrid"],default="classical")
    demo.add_argument("--scenario",default="normal")
    demo.add_argument("--seed",type=int,default=101)
    bop=sub.add_parser("export-bop")
    bop.add_argument("--scene",required=True)
    bop.add_argument("--output",default="bop_annotations.json")
    args=parser.parse_args()
    # Make relative artifacts deterministic even if launched from Explorer or another directory.
    import os
    os.chdir(ROOT)
    if args.command=="desktop":
        from humanoidkit.desktop import launch
        launch(args.smoke_test)
    elif args.command=="serve":
        from humanoidkit.server import serve
        serve(args.port)
    elif args.command=="train":
        from humanoidkit.learning import train
        train(ROOT/"artifacts",args.epochs)
    elif args.command=="evaluate":
        evaluate(args.seeds,args.output)
    elif args.command=="demo":
        from humanoidkit.engine import Engine
        e=Engine(args.seed,args.scenario,args.method,ROOT/"artifacts/policy.pt")
        print(json.dumps(e.execute(),indent=2))
        print(f"Trial log: {e.save()}")
        return 0 if e.completed else 2
    elif args.command=="export-bop":
        export_bop(args.scene,args.output)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
