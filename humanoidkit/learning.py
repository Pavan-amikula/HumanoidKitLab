"""Bounded CPU behaviour cloning of kinematic expert action chunks.

This is a small state-based action-chunking MLP, NOT the ACT paper/model.
Training data are generated demonstrations, never public or physical G1 data.
"""
from pathlib import Path
import json
import time
import math
import numpy as np
import torch
from torch import nn
from .world import World, angle_error

HORIZON=6
ACTION_SCALE=np.array([.045,.045,.045,.18],dtype=np.float32)


def features(hand,hand_yaw,goal,goal_yaw,shoulder):
    return np.r_[((np.asarray(goal)-hand)/.3),angle_error(goal_yaw,hand_yaw)/.5,
                  (np.asarray(hand)-shoulder)/.8].astype(np.float32)


def expert_action(hand,hand_yaw,goal,goal_yaw):
    error=np.asarray(goal)-hand
    distance=float(np.linalg.norm(error))
    delta=error*min(1.,.045/max(distance,1e-9))
    return np.r_[delta,np.clip(angle_error(goal_yaw,hand_yaw),-.18,.18)].astype(np.float32)


class ChunkPolicy(nn.Module):
    def __init__(self):
        super().__init__()
        self.network=nn.Sequential(nn.Linear(7,96),nn.Tanh(),nn.Linear(96,96),nn.Tanh(),
                                   nn.Linear(96,HORIZON*4),nn.Tanh())

    def forward(self,x):
        return self.network(x).reshape(-1,HORIZON,4)


def demonstrations(seeds):
    observations,actions,episode_ids=[],[],[]
    for seed in seeds:
        rng=np.random.default_rng(seed)
        world=World(seed)
        world.rectangles=[]  # isolated-arm demonstrations, no furniture domain claim
        world.base[:]=0
        def point():
            theta=rng.uniform(-math.pi,math.pi)
            r=rng.uniform(.12,.66)
            return world.shoulder+[r*math.cos(theta),r*math.sin(theta),rng.uniform(-.36,.22)]
        world.hand=point()
        world.hand_yaw=rng.uniform(-1.5,1.5)
        goal=point()
        # A two-link arm has an inner unreachable sphere as well as an outer limit.
        # Reject demonstration segments crossing that sphere instead of recording impossible motion.
        while min(np.linalg.norm((1-t)*world.hand+t*goal-world.shoulder)
                  for t in np.linspace(0,1,100))<.05:
            goal=point()
        goal_yaw=rng.uniform(-1.5,1.5)
        for step in range(42):
            x=features(world.hand,world.hand_yaw,goal,goal_yaw,world.shoulder)
            h,y=world.hand.copy(),world.hand_yaw
            chunk=[]
            for _ in range(HORIZON):
                a=expert_action(h,y,goal,goal_yaw)
                chunk.append(a/ACTION_SCALE)
                h+=a[:3]
                y+=float(a[3])
            observations.append(x)
            actions.append(chunk)
            episode_ids.append(seed)
            a=expert_action(world.hand,world.hand_yaw,goal,goal_yaw)
            world.move_hand(world.hand+a[:3],world.hand_yaw+float(a[3]))
            if np.linalg.norm(goal-world.hand)<1e-5 and abs(angle_error(goal_yaw,world.hand_yaw))<1e-5:
                # Explicit stationary demonstrations discourage drift near a reached goal.
                for _ in range(3):
                    observations.append(features(world.hand,world.hand_yaw,goal,goal_yaw,world.shoulder))
                    actions.append(np.zeros((HORIZON,4),dtype=np.float32))
                    episode_ids.append(seed)
                break
    return np.array(observations,dtype=np.float32),np.array(actions,dtype=np.float32),np.array(episode_ids)


def train(output="artifacts",epochs=100):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    torch.set_num_threads(2)
    torch.manual_seed(17)
    rng=np.random.default_rng(17)
    split_seeds={"train":range(1000,1240),"validation":range(2000,2040),"test":range(3000,3040)}
    datasets={}
    for split,seeds in split_seeds.items():
        x,y,ids=demonstrations(seeds)
        np.savez_compressed(output/f"demonstrations_{split}.npz",observations=x,actions=y,episode_ids=ids)
        datasets[split]=(torch.from_numpy(x),torch.from_numpy(y))
    model=ChunkPolicy()
    optimizer=torch.optim.AdamW(model.parameters(),lr=.0015,weight_decay=1e-5)
    x,y=datasets["train"]
    best=float("inf")
    history=[]
    start=time.perf_counter()
    for epoch in range(epochs):
        model.train()
        indices=torch.from_numpy(rng.permutation(len(x)))
        total=0.
        for batch in indices.split(128):
            prediction=model(x[batch])
            # First receding-horizon command receives extra weight.
            loss=((prediction-y[batch])**2).mean()+((prediction[:,0]-y[batch,0])**2).mean()
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total+=float(loss.detach())*len(batch)
        model.eval()
        with torch.inference_mode():
            vx,vy=datasets["validation"]
            val=float(((model(vx)-vy)**2).mean())
        history.append({"epoch":epoch+1,"train_loss":total/len(x),"validation_chunk_mse":val})
        if val<best:
            best=val
            torch.save({"state_dict":model.state_dict(),"horizon":HORIZON,"architecture":"chunk_mlp", "features":7},output/"policy.pt")
        if epoch%10==0 or epoch==epochs-1:
            print(f"epoch {epoch+1}/{epochs} | validation chunk MSE {val:.6f}",flush=True)
    model.load_state_dict(torch.load(output/"policy.pt",map_location="cpu",weights_only=True)["state_dict"])
    tx,ty=datasets["test"]
    with torch.inference_mode():
        test=float(((model(tx)-ty)**2).mean())
    report={"provenance":"generated isolated-arm kinematic demonstrations; no real robot data",
            "architecture":"state-based behaviour-cloned 6-action-chunk MLP; not ACT",
            "execution":"receding horizon: execute first action, observe again",
            "epochs":epochs,"training_seconds":time.perf_counter()-start,
            "train_records":len(x),"validation_records":len(vx),"test_records":len(tx),
            "episode_seeds":{k:list(v) for k,v in split_seeds.items()},
            "best_validation_chunk_mse":best,"held_out_test_chunk_mse":test,"history":history}
    (output/"training_report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in ("episode_seeds","history")},indent=2),flush=True)
    return report


class LearnedController:
    def __init__(self,path):
        torch.set_num_threads(2)
        self.model=ChunkPolicy()
        payload=torch.load(path,map_location="cpu",weights_only=True)
        self.model.load_state_dict(payload["state_dict"])
        self.model.eval()

    def action(self,world,goal,yaw):
        x=features(world.hand,world.hand_yaw,goal,yaw,world.shoulder)
        with torch.inference_mode():
            action=self.model(torch.from_numpy(x)[None])[0,0].numpy()*ACTION_SCALE
        # Identical actuator limits apply to both controllers.
        norm=float(np.linalg.norm(action[:3]))
        if norm>.045:
            action[:3]*=.045/norm
        action[3]=np.clip(action[3],-.18,.18)
        return action
