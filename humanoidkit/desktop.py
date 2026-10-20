"""Socket-free live desktop UI for restricted laptops."""
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox
import json
from PIL import Image,ImageTk
from .engine import Engine
from .world import SCENARIOS
from .render import render_scene

ROOT=Path(__file__).resolve().parents[1]


class DesktopApp:
    def __init__(self,root):
        self.root=root
        root.title("HumanoidKitLab | Industrial Kitting Research")
        root.geometry("1180x880")
        root.minsize(980,750)
        root.configure(bg="#0b111b")
        style=ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame",background="#0b111b")
        style.configure("TLabel",background="#0b111b",foreground="#dfe8f3",font=("Segoe UI",10))
        style.configure("TButton",padding=8,font=("Segoe UI",10))
        self.engine=Engine()
        self.playing=False
        self.saved=False
        self.frame_number=0
        self.azimuth=-.75
        self.elevation=.65
        self.last_drag=None
        self.method=tk.StringVar(value="classical")
        self.scenario=tk.StringVar(value="normal")
        self.seed=tk.StringVar(value="4101")
        outer=ttk.Frame(root,padding=18)
        outer.pack(fill="both",expand=True)
        ttk.Label(outer,text="HumanoidKitLab",font=("Segoe UI",23,"bold"),foreground="#58dbc1").pack(anchor="w")
        ttk.Label(outer,text="Vision-guided industrial kitting | Classical and learned control").pack(anchor="w",pady=(2,8))
        ttk.Label(outer,text="KINEMATIC SIMULATION  |  Synthetic RGB-D  |  Assisted grasps  |  Planar navigation  |  No physical G1 or gait",
                  foreground="#aabdd4").pack(anchor="w",pady=(0,14))
        controls=ttk.Frame(outer)
        controls.pack(fill="x")
        for title,variable,values in [("Controller",self.method,["classical","learned","hybrid"]),
                                      ("Condition",self.scenario,list(SCENARIOS))]:
            ttk.Label(controls,text=title).pack(side="left",padx=(0,6))
            ttk.Combobox(controls,textvariable=variable,values=values,state="readonly",width=15).pack(side="left",padx=(0,12))
        ttk.Label(controls,text="Seed").pack(side="left",padx=(0,6))
        ttk.Entry(controls,textvariable=self.seed,width=7).pack(side="left",padx=(0,12))
        ttk.Button(controls,text="New trial",command=self.reset).pack(side="left")
        for text,command in [("Run kit",self.run),("Pause",self.pause),("Step",self.step),("Stop",self.stop)]:
            ttk.Button(controls,text=text,command=command).pack(side="left",padx=3)
        self.metrics=ttk.Label(outer,font=("Segoe UI",12,"bold"),foreground="#9bead7")
        self.metrics.pack(fill="x",pady=14)
        views=ttk.Frame(outer)
        views.pack(fill="both",expand=True)
        left=ttk.Frame(views)
        left.pack(side="left",fill="both",expand=True)
        ttk.Label(left,text="3D WORKSPACE · Drag to orbit",foreground="#91a7c2").pack(anchor="w")
        self.scene=tk.Label(left,bg="#101a28")
        self.scene.pack(fill="both",expand=True,pady=6)
        self.scene.bind("<ButtonPress-1>",self.begin_drag)
        self.scene.bind("<B1-Motion>",self.orbit)
        right=ttk.Frame(views,padding=(12,0,0,0))
        right.pack(side="right",fill="y")
        ttk.Label(right,text="OVERHEAD CAMERA · Detector input",foreground="#91a7c2").pack(anchor="w")
        self.camera=tk.Label(right,bg="#101a28")
        self.camera.pack(pady=6)
        self.details=ttk.Label(right,text="",wraplength=335,justify="left")
        self.details.pack(anchor="w",pady=10)
        self.status=ttk.Label(outer,font=("Segoe UI",12,"bold"),foreground="#58dbc1")
        self.status.pack(anchor="w",pady=(8,2))
        self.message=ttk.Label(outer,wraplength=1100)
        self.message.pack(anchor="w",pady=(0,8))
        self.events=tk.Text(outer,height=7,bg="#111c2a",fg="#bcd0e8",font=("Consolas",9),relief="flat",wrap="word")
        self.events.pack(fill="x")
        ttk.Label(outer,text="Order: 2 bolts + 1 bracket + 1 spacer. All run logs save automatically to runs/.",foreground="#91a7c2").pack(anchor="w",pady=(8,0))
        root.protocol("WM_DELETE_WINDOW",self.close)
        self.refresh(camera=True)
        root.after(25,self.tick)

    def begin_drag(self,event):
        self.last_drag=(event.x,event.y)

    def orbit(self,event):
        if self.last_drag:
            self.azimuth+=(event.x-self.last_drag[0])*.008
            self.elevation=max(.15,min(1.5,self.elevation+(event.y-self.last_drag[1])*.006))
            self.last_drag=(event.x,event.y)
            self.refresh()

    def save(self):
        if self.engine.finished and not self.saved:
            self.engine.save(ROOT/"runs")
            self.saved=True

    def reset(self):
        try:
            new=Engine(int(self.seed.get()),self.scenario.get(),self.method.get(),ROOT/"artifacts/policy.pt")
            if self.engine.events and not self.engine.finished:
                self.engine.stop_requested=True
                self.engine.step()
                self.save()
            self.engine=new
            self.saved=self.playing=False
            self.refresh(camera=True)
        except (ValueError,FileNotFoundError) as error:
            messagebox.showerror("Cannot create trial",str(error))

    def run(self):
        if self.engine.finished:
            self.reset()
        self.playing=True

    def pause(self):
        self.playing=False

    def step(self):
        self.playing=False
        self.engine.step()
        self.save()
        self.refresh(camera=True)

    def stop(self):
        self.playing=False
        self.engine.stop_requested=True
        self.engine.step()
        self.save()
        self.refresh(camera=True)

    def tick(self):
        if self.playing:
            self.engine.step()
            if self.engine.finished:
                self.playing=False
                self.save()
            self.refresh(camera=self.frame_number%20==0 or self.engine.finished)
        self.frame_number+=1
        self.root.after(25,self.tick)

    def refresh(self,camera=False):
        s=self.engine.snapshot()
        r=s["summary"]
        self.metrics.configure(text=f"Verified slots: {r['correct_slots']}/4     Modeled duration: {s['sim_seconds']:.1f}s     Grasp attempts: {r['grasp_attempts']}     Retries / fallbacks: {r['retries']} / {r['classical_fallbacks']}")
        width=max(600,self.scene.winfo_width())
        height=max(350,min(490,self.scene.winfo_height()))
        image=render_scene(s,width,height,self.azimuth,self.elevation)
        self.scene_image=ImageTk.PhotoImage(image)
        self.scene.configure(image=self.scene_image)
        if camera:
            rgb,_=self.engine.camera.render(self.engine.world)
            self.camera_image=ImageTk.PhotoImage(Image.fromarray(rgb).resize((336,252)))
            self.camera.configure(image=self.camera_image)
        self.status.configure(text=s["state"],foreground="#ff9a9a" if s["state"]=="FAILED" else "#58dbc1")
        self.message.configure(text=s["message"])
        latencies="\n".join(f"{k}: {v['median_ms']:.2f} ms median" for k,v in r["latencies"].items())
        self.details.configure(text=f"Controller: {s['method']}\nSeed: {s['seed']}\nDetected parts: {len(s['detections'])}\nHeld part: {s['held'] or 'none'}\n\n{latencies}\n\nModeled seconds use assumed motion speeds, not physical robot timings.")
        self.events.configure(state="normal")
        self.events.delete("1.0","end")
        important=[e for e in self.engine.events if e["state"] not in ("MANIPULATE","NAVIGATE")]
        for event in important[-7:]:
            self.events.insert("end",f"{event['state']:18} {event['message']}\n")
        self.events.configure(state="disabled")

    def close(self):
        if self.engine.events and not self.engine.finished:
            self.engine.stop_requested=True
            self.engine.step()
        self.save()
        self.root.destroy()


def launch(smoke_test=False):
    root=tk.Tk()
    if smoke_test:
        root.withdraw()
    app=DesktopApp(root)
    if smoke_test:
        root.update_idletasks()
        app.engine=Engine(4101,"normal","learned",ROOT/"artifacts/policy.pt")
        app.engine.execute()
        app.refresh(camera=True)
        root.update_idletasks()
        (ROOT/"results").mkdir(exist_ok=True)
        render_scene(app.engine.snapshot()).save(ROOT/"results/scene_preview.png")
        print(json.dumps({"desktop_widgets":"created and updated","completed_learned_trial":app.engine.completed,
                          "preview":"results/scene_preview.png"}))
        root.destroy()
    else:
        root.mainloop()
