"""Task supervisor, independent verification, bounded recovery and trial logs."""
from pathlib import Path
from collections import Counter
import json
import time
import threading
import numpy as np
from .world import World,BOM,angle_error
from .planning import GridPlanner,NoPath
from .vision import Camera,detect
from .learning import LearnedController,expert_action


class TaskFailure(RuntimeError):
    pass


class Engine:
    def __init__(self,seed=101,scenario="normal",method="classical",model="artifacts/policy.pt"):
        if method not in ("classical","learned","hybrid"):
            raise ValueError("Unknown control method")
        self.world=World(seed,scenario)
        self.camera=Camera()
        self.method=method
        self.policy=LearnedController(model) if method != "classical" else None
        self.planner=GridPlanner(self.world.rectangles)
        self.events=[]
        self.state="READY"
        self.message="Ready to assemble KIT-001"
        self.path=[]
        self.detections=[]
        self.latencies=[]
        self.retries=0
        self.fallbacks=0
        self.grasp_attempts=0
        self.grasp_successes=0
        self.first_grasp_successes=0
        self.completed=False
        self.finished=False
        self.stop_requested=False
        self.start=time.perf_counter()
        self.runner=self.run()
        self.lock=threading.RLock()
        self.last_frame=None
        self.observation_count=0
        self.placement_observations={}
        self.navigation_distance=0.

    def event(self,state,message,**extra):
        self.state,self.message=state,message
        entry={"sequence":len(self.events),"state":state,"message":message,
               "modeled_seconds":round(self.world.sim_seconds,4),**extra}
        self.events.append(entry)
        return entry

    def observe(self):
        t=time.perf_counter()
        rgb,depth=self.camera.render(self.world,self.observation_count)
        self.observation_count+=1
        detections=detect(rgb,depth,self.camera)
        self.last_frame=rgb
        self.detections=[d.as_dict() for d in detections]
        self.latencies.append({"module":"perception","milliseconds":(time.perf_counter()-t)*1000})
        return detections

    def navigate(self,goal):
        started=time.perf_counter()
        self.path=self.planner.plan(self.world.base,goal)
        self.latencies.append({"module":"planning","milliseconds":(time.perf_counter()-started)*1000})
        for point in self.path[1:]:
            self.navigation_distance+=float(np.linalg.norm(np.asarray(point)-self.world.base))
            self.world.move_base(point)
            yield self.event("NAVIGATE","Following footprint-clear A* route")
        self.path=[]
        yield self.event("DOCK","Base stopped for manipulation")

    def servo(self,goal,yaw,force_classical=False):
        goal=np.array(goal,dtype=float)
        controller="classical" if force_classical else self.method
        for _ in range(100):
            distance=float(np.linalg.norm(goal-self.world.hand))
            rotation=abs(angle_error(yaw,self.world.hand_yaw))
            if distance<.012 and rotation<.06:
                return
            t=time.perf_counter()
            if controller=="classical":
                a=expert_action(self.world.hand,self.world.hand_yaw,goal,yaw)
            else:
                a=self.policy.action(self.world,goal,yaw)
            self.latencies.append({"module":f"control_{controller}","milliseconds":(time.perf_counter()-t)*1000})
            self.world.move_hand(self.world.hand+a[:3],self.world.hand_yaw+float(a[3]))
            self.world.sim_seconds+=.15
            yield self.event("MANIPULATE",f"{controller}: closed-loop arm movement")
        if self.method=="hybrid" and not force_classical:
            self.fallbacks+=1
            yield self.event("RECOVER","Learned controller timed out; explicit classical fallback")
            yield from self.servo(goal,yaw,True)
        else:
            raise TaskFailure("Arm controller failed to reach its target within 100 commands")

    def park(self):
        goal=self.world.shoulder+np.array([.14,0,.22])
        # Lift before crossing the table edge.
        hover=self.world.hand.copy()
        hover[2]=max(1.16,float(hover[2]))
        yield from self.servo(hover,self.world.hand_yaw)
        yield from self.servo(goal,self.world.hand_yaw)

    def verify_slot_from_camera(self,slot,kind):
        target=self.world.slots[slot]
        candidates=[d for d in self.observe() if d.kind==kind and np.linalg.norm(d.position-target)<.055]
        if len(candidates)==1:
            self.placement_observations[str(slot)]={"position_error_m":float(np.linalg.norm(candidates[0].position-target)),
                                                    "yaw_error_rad":abs(angle_error(0,candidates[0].yaw))}
        return len(candidates)==1 and abs(angle_error(0,candidates[0].yaw))<.23

    def run(self):
        try:
            yield self.event("CHECK_ORDER","Checking observed rack inventory against the kit order")
            observations=self.observe()
            available=Counter(d.kind for d in observations if d.position[0]<0 and d.confidence>.65)
            required=Counter(BOM)
            if any(available[k]<count for k,count in required.items()):
                raise TaskFailure("Insufficient visible stock: missing or occluded required part")
            for slot,kind in enumerate(BOM):
                yield self.event("LOCATE_PART",f"Finding {kind} for slot {slot+1}")
                candidates=[d for d in self.observe() if d.kind==kind and d.position[0]<0 and d.confidence>.65]
                if not candidates:
                    raise TaskFailure(f"No reliable visible {kind} remains")
                part=min(candidates,key=lambda d:d.position[1])
                yield from self.park()
                yield from self.navigate((-.70,float(part.position[1])))
                success=False
                for attempt in range(2):
                    hover=part.position.copy()
                    hover[2]=1.12
                    yield from self.servo(hover,part.yaw)
                    yield from self.servo(part.position,part.yaw)
                    self.grasp_attempts+=1
                    success,reason=self.world.grasp(kind)
                    yield self.event("VERIFY_GRASP",reason,success=success)
                    if success:
                        self.grasp_successes+=1
                        self.first_grasp_successes+=int(attempt==0)
                        break
                    self.retries+=1
                    self.world.open=True
                    yield self.event("RECOVER","Opening hand and taking a fresh camera observation")
                    observations=[d for d in self.observe() if d.kind==kind and d.position[0]<0]
                    if not observations:
                        break
                    part=min(observations,key=lambda d:np.linalg.norm(d.position-part.position))
                if not success:
                    raise TaskFailure("Grasp failed after bounded retry")
                yield from self.park()
                yield from self.navigate((.72,0.))
                target=self.world.slots[slot]
                hover=target.copy()
                hover[2]=1.12
                yield self.event("ROTATE","Orienting the carried part for its kit slot")
                yield from self.servo(hover,0.)
                yield from self.servo(target,0.)
                self.world.release(slot)
                yield self.event("PLACE",f"Released {kind} in slot {slot+1}")
                yield from self.park()
                if not self.verify_slot_from_camera(slot,kind):
                    raise TaskFailure(f"Independent camera verification failed for slot {slot+1}")
                yield self.event("VERIFY_PLACEMENT",f"Camera confirmed {kind} and orientation in slot {slot+1}")
            camera_checks=[self.verify_slot_from_camera(i,k) for i,k in enumerate(BOM)]
            # Evaluation-only world truth is an additional guard, never the detector input.
            self.completed=all(camera_checks) and all(self.world.verify())
            if not self.completed:
                raise TaskFailure("Final kit verification failed")
            yield self.event("COMPLETE","KIT-001 verified: correct parts, quantities, slots and orientations")
        except (TaskFailure,NoPath,ValueError) as error:
            self.completed=False
            yield self.event("FAILED",str(error))
        self.finished=True

    def step(self):
        with self.lock:
            if self.finished:
                return False
            if self.stop_requested:
                self.event("STOPPED","Simulation stopped by operator")
                self.finished=True
                return False
            try:
                next(self.runner)
                return True
            except StopIteration:
                self.finished=True
                return False

    def execute(self,max_events=12000):
        for _ in range(max_events):
            if not self.step():
                return self.summary()
        self.stop_requested=True
        self.step()
        return self.summary()

    def summary(self):
        checks=self.world.verify()
        latencies={}
        for module in sorted({r["module"] for r in self.latencies}):
            v=[r["milliseconds"] for r in self.latencies if r["module"]==module]
            latencies[module]={"count":len(v),"median_ms":float(np.median(v)),"p95_ms":float(np.percentile(v,95))}
        return {"seed":self.world.seed,"scenario":self.world.scenario,"method":self.method,
                "environment":"kinematic synthetic simulation; assisted geometric grasps; no physics or gait",
                "success":self.completed,"status":self.state,"reason":self.message,
                "correct_slots":sum(checks),"total_slots":len(BOM),
                "grasp_attempts":self.grasp_attempts,"grasp_successes":self.grasp_successes,
                "first_attempt_grasp_successes":self.first_grasp_successes,
                "retries":self.retries,"classical_fallbacks":self.fallbacks,
                "navigation_distance_m":self.navigation_distance,
                "camera_placement_errors":self.placement_observations.copy(),
                "modeled_cycle_seconds":self.world.sim_seconds,
                "wall_seconds":time.perf_counter()-self.start,"latencies":latencies}

    def snapshot(self):
        with self.lock:
            return {**self.world.snapshot(),"state":self.state,"message":self.message,
                    "method":self.method,"finished":self.finished,"success":self.completed,
                    "path":self.path,"detections":self.detections,"events":self.events[-14:],
                    "summary":self.summary()}

    def save(self,directory="runs"):
        directory=Path(directory)
        directory.mkdir(parents=True,exist_ok=True)
        path=directory/f"{time.time_ns()}_{self.method}_{self.world.scenario}_{self.world.seed}.json"
        path.write_text(json.dumps({"summary":self.summary(),"events":self.events,
                                    "world":self.world.snapshot()},indent=2),encoding="utf-8")
        return path
