"""Dependency-light 3D view shared by desktop UI and visual regression smoke checks."""
import math
from PIL import Image,ImageDraw,ImageFont

COLORS={"bolt":"#dc3e42","bracket":"#378ceb","spacer":"#ebbe28"}


def render_scene(state,width=760,height=490,azimuth=-.75,elevation=.65,zoom=1.):
    image=Image.new("RGB",(width,height),"#101a28")
    draw=ImageDraw.Draw(image)
    try:
        font=ImageFont.truetype("segoeui.ttf",12)
    except OSError:
        font=ImageFont.load_default()
    scale=min(width/5.7,height/4.1)*zoom
    def project(p):
        x=p[0]*math.cos(azimuth)-p[1]*math.sin(azimuth)
        y=p[0]*math.sin(azimuth)+p[1]*math.cos(azimuth)
        return width/2+x*scale,height*.66+(y*math.sin(elevation)-p[2]*math.cos(elevation))*scale
    def line(points,color,width=1):
        draw.line([project(p) for p in points],fill=color,width=width)
    def polygon(points,color):
        draw.polygon([project(p) for p in points],fill=color,outline="#53647b")
    def box(c,size,color):
        x,y,z=c
        a,b,h=size
        top=[[x-a/2,y-b/2,z+h],[x+a/2,y-b/2,z+h],[x+a/2,y+b/2,z+h],[x-a/2,y+b/2,z+h]]
        polygon([top[0],top[1],[x+a/2,y-b/2,z],[x-a/2,y-b/2,z]],color)
        polygon([top[1],top[2],[x+a/2,y+b/2,z],[x+a/2,y-b/2,z]],color)
        polygon(top,color)
    def text(p,message,color="#9db2cd"):
        draw.text(project(p),message,fill=color,font=font)
    for n in range(-8,9):
        x=n*.3
        line([[x,-1.7,0],[x,1.7,0]],"#203047")
    for n in range(-5,6):
        y=n*.3
        line([[-2.4,y,0],[2.4,y,0]],"#203047")
    for i,r in enumerate(state["obstacles"]):
        box([(r[0]+r[2])/2,(r[1]+r[3])/2,0],[r[2]-r[0],r[3]-r[1],.82 if i<2 else .45],
            "#34465b" if i==0 else "#284b4d" if i==1 else "#51495c")
    text([-1.6,-1.12,.97],"PARTS RACK")
    text([1.15,-.52,.98],"ASSEMBLY KIT")
    for i,p in enumerate(state["slots"]):
        box([p[0],p[1],.824],[.205,.29,.012],"#276254" if state["slot_checks"][i] else "#526375")
        text([p[0]-.04,p[1],.86],str(i+1),"#d5e7f2")
    if len(state.get("path",[]))>1:
        line([[p[0],p[1],.02] for p in state["path"]],"#58dbc1",3)
    for part in state["parts"]:
        x,y,z=part["position"]
        a=part["yaw"]
        length=.17 if part["kind"]=="bolt" else .19
        pts=[]
        for u,v in [(-length/2,-.0375),(length/2,-.0375),(length/2,.0375),(-length/2,.0375)]:
            pts.append([x+u*math.cos(a)-v*math.sin(a),y+u*math.sin(a)+v*math.cos(a),z+.025])
        polygon(pts,COLORS[part["kind"]])
    if state.get("obstruction"):
        r=state["obstruction"]
        box([(r[0]+r[2])/2,(r[1]+r[3])/2,.82],[r[2]-r[0],r[3]-r[1],.18],"#757780")
    x,y=state["base"]
    for sign in [-1,1]:
        box([x+sign*.09,y,0],[.12,.22,.08],"#7995b5")
        line([[x+sign*.1,y,.08],[x+sign*.1,y,.65],[x,y,.91]],"#8aa2bf",9)
    box([x,y,.91],[.30,.23,.42],"#c2d0e3")
    box([x,y,1.39],[.19,.18,.20],"#d5e0ef")
    line([[x-.14,y,1.22],[x-.23,y,1.02],[x-.18,y,.86]],"#7891b0",9)
    line(state["arm"],"#69dfc6",10)
    for p in state["arm"]:
        u,v=project(p)
        draw.ellipse((u-5,v-5,u+5,v+5),fill="#d6f8ee")
    p=state["hand"]
    a=state["hand_yaw"]
    for sign in [-1,1]:
        dx=sign*.045*math.cos(a+math.pi/2)
        dy=sign*.045*math.sin(a+math.pi/2)
        line([[p[0]+dx,p[1]+dy,p[2]+.05],[p[0]+dx,p[1]+dy,p[2]-.015]],"#e7f8f1",3)
    text([x-.35,y,1.77],"KINEMATIC SURROGATE","#8cdcc9")
    return image
