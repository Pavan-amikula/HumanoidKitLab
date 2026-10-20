"""Render evidence from executed simulator states, not generated video imagery."""
from pathlib import Path
import json
import math
import hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import av
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from humanoidkit.engine import Engine
from humanoidkit.render import render_scene
from humanoidkit.vision import detect

ROOT=Path(__file__).resolve().parents[1]
MEDIA=ROOT/"docs/media"
MEDIA.mkdir(parents=True,exist_ok=True)
FPS=12


def font(size,bold=False):
    try:
        return ImageFont.truetype("segoeuib.ttf" if bold else "segoeui.ttf",size)
    except OSError:
        return ImageFont.load_default(size=size)


def wrap(draw,text,xy,width,size=18,fill="#b8c9de",max_lines=3):
    words=text.split()
    lines=[]
    line=""
    for word in words:
        candidate=(line+" "+word).strip()
        if draw.textlength(candidate,font=font(size))>width and line:
            lines.append(line)
            line=word
        else:
            line=candidate
    if line:
        lines.append(line)
    for i,line in enumerate(lines[:max_lines]):
        draw.text((xy[0],xy[1]+i*(size+7)),line,font=font(size),fill=fill)


def frame(engine,chapter):
    s=engine.snapshot()
    r=s["summary"]
    image=Image.new("RGB",(1280,800),"#0b111b")
    draw=ImageDraw.Draw(image)
    draw.text((30,20),"HumanoidKitLab",font=font(32,True),fill="#72e5ca")
    draw.text((32,66),chapter,font=font(20),fill="#e1eafa")
    draw.text((32,102),"EXECUTED KINEMATIC SIMULATION  |  Accelerated playback  |  No physical G1 or gait",font=font(15),fill="#a6b7ce")
    image.paste(render_scene(s,860,465),(18,145))
    rgb,_=engine.camera.render(engine.world)
    image.paste(Image.fromarray(rgb).resize((356,267)),(896,164))
    draw.text((898,137),"RGB camera: perception input",font=font(16),fill="#9eb5cf")
    draw.text((898,446),f"Controller: {s['method']}",font=font(19,True),fill="#d9e8fa")
    draw.text((898,480),f"Verified slots: {r['correct_slots']} / 4",font=font(22,True),fill="#72e5ca")
    draw.text((898,518),f"Grasp attempts: {r['grasp_attempts']}",font=font(18),fill="#b8c9de")
    draw.text((898,550),f"Retries: {r['retries']}  |  Fallbacks: {r['classical_fallbacks']}",font=font(17),fill="#b8c9de")
    draw.rounded_rectangle((28,618,1252,765),radius=14,fill="#142133",outline="#2c405c")
    draw.text((48,634),s["state"],font=font(23,True),fill="#ffb7b7" if s["state"]=="FAILED" else "#72e5ca")
    wrap(draw,s["message"],(48,674),1160,size=19,max_lines=2)
    draw.text((48,734),"Order: 2 bolts + 1 bracket + 1 spacer   |   Assisted geometric grasping; no contact-force simulation",font=font(14),fill="#8fa6bf")
    return image


def video():
    output=MEDIA/"humanoidkit_demo.mp4"
    container=av.open(str(output),mode="w",options={"movflags":"+faststart"})
    stream=container.add_stream("libx264",rate=FPS)
    stream.width,stream.height=1280,800
    stream.pix_fmt="yuv420p"
    stream.options={"crf":"23","preset":"fast","threads":"2"}
    count=0
    preview=[]
    chapters=[]
    selected={}
    def encode(image,repeat=1):
        nonlocal count
        for _ in range(repeat):
            vf=av.VideoFrame.from_image(image)
            for packet in stream.encode(vf):
                container.mux(packet)
            count+=1
    cases=[("learned","normal","01 / Full kit: vision, navigation, picking and verified placement"),
           ("hybrid","grasp_failure","02 / Recovery: a missed grasp triggers a fresh observation and retry"),
           ("classical","missing","03 / Failure handling: missing stock never becomes a completed kit")]
    for method,scenario,title in cases:
        engine=Engine(4101,scenario,method,ROOT/"artifacts/policy.pt")
        start=count/FPS
        encode(frame(engine,title),FPS*2)
        step=0
        while engine.step():
            step+=1
            if engine.state in ("VERIFY_GRASP","ROTATE","VERIFY_PLACEMENT","RECOVER","COMPLETE","FAILED"):
                selected.setdefault(engine.state,frame(engine,title))
            if step%3==0 or engine.state in ("COMPLETE","FAILED","RECOVER","VERIFY_PLACEMENT"):
                picture=frame(engine,title)
                encode(picture)
                if scenario=="normal" and step%6==0:
                    preview.append(picture.resize((800,500)))
        picture=frame(engine,title)
        encode(picture,FPS*3)
        if scenario=="normal":
            picture.save(MEDIA/"demo_poster.png")
            preview.extend([picture.resize((800,500))]*12)
        log=engine.save(ROOT/"results/showcase_trials")
        chapters.append({"title":title,"starts_at_seconds":start,"ends_at_seconds":count/FPS,
                         "method":method,"scenario":scenario,"seed":4101,
                         "success":engine.completed,"correct_slots":sum(engine.world.verify()),
                         "log":str(log.relative_to(ROOT)).replace("\\","/")})
        print(f"Rendered {method}/{scenario}: {engine.state}, {count} frames total",flush=True)
    for packet in stream.encode():
        container.mux(packet)
    container.close()
    # GIF is a preview of the full successful execution, with explicitly accelerated playback.
    preview[0].save(MEDIA/"demo_preview.gif",save_all=True,append_images=preview[1:],duration=160,loop=0,optimize=True)
    for key,image in selected.items():
        image.save(MEDIA/f"stage_{key.lower()}.png")
    with av.open(str(output)) as check:
        decoded=sum(1 for _ in check.decode(video=0))
    if decoded!=count:
        raise RuntimeError(f"Decoded {decoded} of {count} expected frames")
    manifest={"video":"docs/media/humanoidkit_demo.mp4","codec":"H.264","pixel_format":"yuv420p",
              "resolution":[1280,800],"fps":FPS,"frames":count,"duration_seconds":count/FPS,
              "decoded_frame_count_verified":decoded,"content":"Rendered states from executed simulator runs, not a desktop screen capture or physical robot video",
              "playback":"Accelerated; not a measurement of robot or application wall-clock speed",
              "chapters":chapters,"sha256":hashlib.sha256(output.read_bytes()).hexdigest()}
    (MEDIA/"demo_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps(manifest,indent=2),flush=True)


def outputs():
    engine=Engine(4101,"rotated")
    rgb,depth=engine.camera.render(engine.world)
    detections=detect(rgb,depth,engine.camera)
    image=Image.fromarray(rgb).resize((960,720))
    draw=ImageDraw.Draw(image)
    for d in detections:
        u,v=engine.camera.project(*d.position[:2])
        u,v=u*1.5,v*1.5
        draw.ellipse((u-5,v-5,u+5,v+5),fill="#ffffff")
        label=f"{d.kind}  ({d.position[0]:.2f}, {d.position[1]:.2f}, {d.position[2]:.2f}) m"
        draw.text((u+14,v-8),label,font=font(16),fill="#ffffff",stroke_width=2,stroke_fill="#101a28")
    draw.rectangle((0,0,960,68),fill="#0b111b")
    draw.text((20,12),"Pixel-based part detection and calibrated 3D centroids",font=font(24,True),fill="#72e5ca")
    draw.text((20,45),"Synthetic RGB-D | color-coded parts | planar yaw from PCA",font=font(16),fill="#b8c9de")
    image.save(MEDIA/"perception_output.png")
    report=json.loads((ROOT/"results/evaluation.json").read_text(encoding="utf-8"))
    conditions=["normal","rotated","lighting","grasp_failure","occluded","missing","blocked","drop"]
    methods=["classical","learned","hybrid"]
    plt.rcParams.update({"font.size":11,"figure.facecolor":"#0b111b","axes.facecolor":"#0b111b",
                         "text.color":"#dae7f8","axes.labelcolor":"#dae7f8","xtick.color":"#dae7f8","ytick.color":"#dae7f8"})
    fig,ax=plt.subplots(figsize=(12.8,4.5))
    for row,method in enumerate(methods):
        for col,scenario in enumerate(conditions):
            g=next(g for g in report["groups"] if g["method"]==method and g["scenario"]==scenario)
            completed=g["completed_kits"]
            ax.add_patch(plt.Rectangle((col-.47,row-.42),.94,.84,color="#23644e" if col<4 else "#284b73"))
            ax.text(col,row,(f"{completed}/{g['attempts']}\ncompleted" if col<4 else f"{g['attempts']-completed}/{g['attempts']}\nstopped"),ha="center",va="center",color="white",fontsize=11)
    ax.set_xlim(-.55,7.55);ax.set_ylim(2.55,-.6)
    ax.set_xticks(range(8),["Normal","Rotated","Low light","Missed grasp","Occluded","Missing","Blocked","Dropped"])
    ax.set_yticks(range(3),["Classical","Learned","Hybrid"])
    ax.set_title("72 paired simulation trials: completed kits and correctly stopped fault cases",loc="left",pad=22,fontsize=16,fontweight="bold")
    ax.tick_params(length=0,pad=10)
    for spine in ax.spines.values():spine.set_visible(False)
    fig.text(.13,.025,"3 held-out layout seeds per condition. Kinematic simulation and assisted grasps; no physical G1 results.",fontsize=10,color="#a6b7ce")
    fig.tight_layout(rect=[0,.08,1,1]);fig.savefig(MEDIA/"evaluation_overview.png",dpi=130);plt.close(fig)
    training=json.loads((ROOT/"artifacts/training_report.json").read_text(encoding="utf-8"))
    fig,ax=plt.subplots(figsize=(9,4))
    ax.plot([h["epoch"] for h in training["history"]],[h["validation_chunk_mse"] for h in training["history"]],color="#72e5ca",linewidth=2)
    ax.set(xlabel="Training epoch",ylabel="Validation action-chunk MSE",title="Behaviour-cloned action chunks: validation history")
    ax.grid(alpha=.15);fig.tight_layout();fig.savefig(MEDIA/"training_curve.png",dpi=130);plt.close(fig)
    (MEDIA/"perception_detections.json").write_text(json.dumps([d.as_dict() for d in detections],indent=2),encoding="utf-8")


if __name__=="__main__":
    outputs()
    video()
