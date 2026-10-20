"""Explicitly kinematic humanoid surrogate with assisted, geometric grasps.

There is no rigid-body dynamics, gait, balance, force model or Unitree model.
All dimensions are metres. Arm links have analytic inverse kinematics.
"""
from dataclasses import dataclass
from collections import Counter
import math
import numpy as np

COLORS = {"bolt": (220, 62, 66), "bracket": (55, 140, 235), "spacer": (235, 190, 40)}
BOM = ["bolt", "bolt", "bracket", "spacer"]
SCENARIOS = ("normal", "rotated", "lighting", "occluded", "missing", "blocked", "grasp_failure", "drop")


def angle_error(target, current):
    """Parallel-jaw grasp symmetry: orientations repeat every pi radians."""
    return (float(target)-float(current)+math.pi/2) % math.pi-math.pi/2


@dataclass
class Part:
    uid: str
    kind: str
    position: np.ndarray
    yaw: float
    location: str = "rack"

    def as_dict(self):
        return {"id": self.uid, "kind": self.kind, "position": self.position.tolist(),
                "yaw": float(self.yaw), "location": self.location}


class World:
    L1, L2 = .46, .43

    def __init__(self, seed=101, scenario="normal"):
        if scenario not in SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario}")
        self.seed, self.scenario = seed, scenario
        rng = np.random.default_rng(seed)
        self.base = np.array([-.65, 1.3])
        self.heading = -math.pi/2
        self.hand = np.array([-.47, 1.3, 1.35])
        self.hand_yaw = 0.
        self.held = None
        self.open = True
        self.parts = []
        for i, kind in enumerate(BOM + ["bracket"]):
            y = -.74 + i*.35 + rng.uniform(-.025, .025)
            yaw = rng.uniform(-1.4, 1.4) if scenario == "rotated" else rng.uniform(-.6, .6)
            self.parts.append(Part(f"p{i}", kind, np.array([-1.30+rng.uniform(-.025,.025), y, .855]), yaw))
        if scenario == "missing":
            self.parts = [p for p in self.parts if p.kind != "spacer"]
        self.slots = [np.array([1.25 + (i % 2)*.24, -.20 + (i//2)*.40, .855]) for i in range(4)]
        self.rectangles = [(-1.56,-1.02,-1.07,1.02), (1.12,-.43,1.64,.43), (-.1,.35,.22,.72)]
        if scenario == "blocked":
            self.rectangles.append((.25,-1.7,.45,1.7))
        self.obstruction = (-1.6, .18, -1.05, .48) if scenario == "occluded" else None
        self.sim_seconds = 0.
        self.grasp_injected = False
        self.drop_injected = False
        self.joints = self.ik(self.hand)

    @property
    def shoulder(self):
        return np.array([self.base[0], self.base[1], 1.20])

    def ik(self, target):
        v = np.asarray(target)-self.shoulder
        radial = float(np.linalg.norm(v[:2]))
        c = (float(v@v)-self.L1**2-self.L2**2)/(2*self.L1*self.L2)
        if abs(c) > 1.000001:
            raise ValueError("Arm target outside reachable workspace")
        elbow = -math.acos(float(np.clip(c,-1,1)))
        shoulder = math.atan2(v[2],radial)-math.atan2(self.L2*math.sin(elbow),self.L1+self.L2*math.cos(elbow))
        return np.array([math.atan2(v[1],v[0]), shoulder, elbow])

    def links(self, joints=None):
        q = self.joints if joints is None else joints
        yaw, shoulder, elbow = q
        direction = np.array([math.cos(yaw), math.sin(yaw), 0.])
        a = self.shoulder
        b = a + self.L1*math.cos(shoulder)*direction + [0,0,self.L1*math.sin(shoulder)]
        c = b + self.L2*math.cos(shoulder+elbow)*direction + [0,0,self.L2*math.sin(shoulder+elbow)]
        return [a.tolist(), b.tolist(), c.tolist()]

    def move_hand(self, target, yaw):
        target = np.asarray(target, dtype=float)
        joints = self.ik(target)
        points = self.links(joints)
        # Sampled centreline check against tabletops, not mesh-level collision validation.
        for a,b in zip(points[:-1],points[1:]):
            for t in np.linspace(0,1,14):
                p = np.array(a)*(1-t)+np.array(b)*t
                if p[2] < .825 and any(l-.015 <= p[0] <= r+.015 and d-.015 <= p[1] <= u+.015
                                      for l,d,r,u in self.rectangles[:2]):
                    raise ValueError("Arm centreline intersects furniture")
        self.joints, self.hand, self.hand_yaw = joints, target, float(yaw)
        if self.held:
            self.held.position = target.copy()
            self.held.yaw = self.hand_yaw

    def move_base(self, point):
        point = np.asarray(point, dtype=float)
        delta = point-self.base
        distance = float(np.linalg.norm(delta))
        if distance:
            self.heading = math.atan2(delta[1],delta[0])
        self.base = point
        self.move_hand(np.array([point[0]+.14, point[1], 1.42]), self.hand_yaw)
        self.sim_seconds += distance/.25

    def grasp(self, expected_kind):
        self.open = False
        if self.scenario == "grasp_failure" and not self.grasp_injected:
            self.grasp_injected = True
            return False, "Injected missed grasp"
        available = [p for p in self.parts if p.location == "rack"]
        if not available:
            return False, "No part near hand"
        p = min(available, key=lambda p: np.linalg.norm(p.position-self.hand))
        if p.kind != expected_kind or np.linalg.norm(p.position-self.hand) > .045:
            return False, "Wrong part or grasp position error"
        if abs(angle_error(p.yaw,self.hand_yaw)) > math.radians(18):
            return False, "Grasp orientation error"
        self.held, p.location = p, "hand"
        p.position = self.hand.copy()
        p.yaw = self.hand_yaw
        self.sim_seconds += .5
        return True, "Geometric assisted grasp verified"

    def release(self, slot):
        if not self.held:
            return False
        p = self.held
        self.held, self.open = None, True
        p.position = self.hand.copy()
        if self.scenario == "drop" and not self.drop_injected:
            self.drop_injected = True
            p.position += [.18,.18,-.40]
            p.location = "floor"
        else:
            p.location = f"slot{slot}"
        self.sim_seconds += .5
        return True

    def verify(self):
        checks = []
        for i,kind in enumerate(BOM):
            parts = [p for p in self.parts if p.location == f"slot{i}"]
            ok = len(parts) == 1 and parts[0].kind == kind
            if ok:
                ok = np.linalg.norm(parts[0].position-self.slots[i]) < .045 and abs(angle_error(0,parts[0].yaw)) < .20
            checks.append(bool(ok))
        return checks

    def snapshot(self):
        return {"seed": self.seed, "scenario": self.scenario, "base": self.base.tolist(),
                "heading": self.heading, "hand": self.hand.tolist(), "hand_yaw": self.hand_yaw,
                "arm": self.links(), "held": self.held.uid if self.held else None,
                "parts": [p.as_dict() for p in self.parts], "slots": [s.tolist() for s in self.slots],
                "obstacles": self.rectangles, "obstruction": self.obstruction,
                "slot_checks": self.verify(), "sim_seconds": self.sim_seconds}
