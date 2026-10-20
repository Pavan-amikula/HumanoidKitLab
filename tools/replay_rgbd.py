"""Run from the project root: python -m tools.replay_rgbd --help."""
import argparse
import json
from humanoidkit.rgbd import replay

parser=argparse.ArgumentParser(description="Color-coded tabletop RGB-D perception replay")
parser.add_argument("--rgb",required=True)
parser.add_argument("--depth",required=True)
parser.add_argument("--calibration",required=True)
args=parser.parse_args()
print(json.dumps(replay(args.rgb,args.depth,args.calibration),indent=2))
