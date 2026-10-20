"""Synthetic orthographic RGB-D camera and independent pixel-based detector.

The detector receives images, depth and calibration, never world object poses.
Color coding is a controlled simulation baseline, not an industrial detector.
"""
from dataclasses import dataclass
import math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from .world import COLORS


@dataclass
class Detection:
    kind: str
    position: np.ndarray
    yaw: float
    confidence: float
    pixels: int

    def as_dict(self):
        return {"kind":self.kind,"position":self.position.tolist(),"yaw":self.yaw,
                "confidence":self.confidence,"pixels":self.pixels}


class Camera:
    width, height, z = 640, 480, 3.0
    xmin, xmax, ymin, ymax = -2.4, 2.4, -1.7, 1.7

    def project(self,x,y):
        return ((x-self.xmin)/(self.xmax-self.xmin)*(self.width-1),
                (self.ymax-y)/(self.ymax-self.ymin)*(self.height-1))

    def unproject(self,u,v,depth):
        return np.array([self.xmin+u/(self.width-1)*(self.xmax-self.xmin),
                         self.ymax-v/(self.height-1)*(self.ymax-self.ymin), self.z-depth])

    def render(self,world,noise_seed=0):
        image=Image.new("RGB",(self.width,self.height),(28,36,48))
        draw=ImageDraw.Draw(image)
        depth=Image.new("F",image.size,self.z)
        zd=ImageDraw.Draw(depth)
        for i,(l,b,r,t) in enumerate(world.rectangles):
            a,c=self.project(l,t),self.project(r,b)
            draw.rectangle([a,c],fill=(88,94,103) if i<2 else (110,112,120))
            zd.rectangle([a,c],fill=self.z-(.82 if i<2 else .45))
        for p in sorted(world.parts,key=lambda p:p.position[2]):
            if p.location == "hand":
                continue  # hand is excluded from this fixed overhead verification camera
            x,y,z=p.position
            # Every object has an elongated axis; parallel-jaw yaw has pi symmetry.
            length,width={"bolt":(.17,.065),"bracket":(.19,.09),"spacer":(.14,.075)}[p.kind]
            polygon=[]
            for a,b in [(-length/2,-width/2),(length/2,-width/2),(length/2,width/2),(-length/2,width/2)]:
                polygon.append(self.project(x+a*math.cos(p.yaw)-b*math.sin(p.yaw),
                                            y+a*math.sin(p.yaw)+b*math.cos(p.yaw)))
            draw.polygon(polygon,fill=COLORS[p.kind])
            zd.polygon(polygon,fill=self.z-z)
        if world.obstruction:
            l,b,r,t=world.obstruction
            draw.rectangle([self.project(l,t),self.project(r,b)],fill=(115,115,115))
            zd.rectangle([self.project(l,t),self.project(r,b)],fill=self.z-1.0)
        rgb=np.asarray(image).copy()
        if world.scenario == "lighting":
            rng=np.random.default_rng(world.seed+noise_seed)
            rgb=np.clip(rgb.astype(float)*.58+rng.normal(0,4,rgb.shape),0,255).astype(np.uint8)
        return rgb,np.asarray(depth).copy()


def detect(rgb,depth,camera=None):
    camera=camera or Camera()
    rgb=np.asarray(rgb,dtype=float)
    if rgb.shape[:2] != depth.shape or rgb.shape != (camera.height,camera.width,3):
        raise ValueError("Image dimensions do not match camera calibration")
    chroma=rgb/np.maximum(rgb.sum(axis=2,keepdims=True),1)
    detections=[]
    for kind,color in COLORS.items():
        reference=np.array(color,dtype=float)/sum(color)
        distance=np.linalg.norm(chroma-reference,axis=2)
        mask=(distance<.105)&(rgb.max(axis=2)>45)
        labels,n=ndimage.label(mask)
        for i in range(1,n+1):
            v,u=np.where(labels==i)
            if len(u)<30:
                continue
            good=np.isfinite(depth[v,u])&(depth[v,u]>0)&(depth[v,u]<camera.z)
            u,v=u[good],v[good]
            if len(u)<30:
                continue
            points=np.array([camera.unproject(a,b,float(depth[b,a])) for a,b in zip(u,v)])
            position=np.median(points,axis=0)
            eigenvalues,vectors=np.linalg.eigh(np.cov(points[:,:2].T))
            axis=vectors[:,-1]
            yaw=float(math.atan2(axis[1],axis[0]))
            confidence=float(np.clip(1-np.median(distance[v,u])/.105,0,1))
            detections.append(Detection(kind,position,yaw,confidence,len(u)))
    return detections
