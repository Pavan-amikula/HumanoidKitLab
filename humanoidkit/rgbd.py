"""Replay calibrated RGB-D frames with color-coded tabletop parts.

This is a usable file-input adapter, not a validated physical camera driver.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from .vision import Camera,detect


class PinholeCamera:
    def __init__(self,config):
        self.width=int(config["width"])
        self.height=int(config["height"])
        self.fx,self.fy,self.cx,self.cy=map(float,(config["fx"],config["fy"],config["cx"],config["cy"]))
        self.transform=np.array(config["camera_to_world"],dtype=float)
        self.z=float(config.get("maximum_depth_m",10.))
        if (self.width<=0 or self.height<=0 or self.fx<=0 or self.fy<=0 or
                not np.isfinite([self.fx,self.fy,self.cx,self.cy,self.z]).all() or self.z<=0 or
                self.transform.shape!=(4,4) or not np.isfinite(self.transform).all()):
            raise ValueError("Invalid camera calibration")
        if (not np.allclose(self.transform[3],[0,0,0,1]) or
                not np.allclose(self.transform[:3,:3].T@self.transform[:3,:3],np.eye(3),atol=1e-4) or
                not np.isclose(np.linalg.det(self.transform[:3,:3]),1.,atol=1e-4)):
            raise ValueError("camera_to_world must be a rigid transform")

    def unproject(self,u,v,depth):
        point=np.array([(u-self.cx)*depth/self.fx,(v-self.cy)*depth/self.fy,depth,1.])
        return (self.transform@point)[:3]


def replay(rgb_path,depth_path,calibration_path):
    config=json.loads(Path(calibration_path).read_text(encoding="utf-8"))
    projection=config.get("projection","orthographic")
    if projection not in ("pinhole","orthographic"):
        raise ValueError("Unsupported camera projection")
    camera=PinholeCamera(config) if projection=="pinhole" else Camera()
    rgb=np.asarray(Image.open(rgb_path).convert("RGB"))
    scale=float(config.get("depth_scale_to_metres",1.))
    if not np.isfinite(scale) or scale<=0:
        raise ValueError("Depth scale must be finite and positive")
    depth=np.load(depth_path,allow_pickle=False)*scale
    return [d.as_dict() for d in detect(rgb,depth,camera)]
