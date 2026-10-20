"""Loopback-only live dashboard. There are no physical robot endpoints."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import io
import json
import threading
import time
from PIL import Image
from .engine import Engine

ROOT=Path(__file__).resolve().parents[1]


class Session:
    def __init__(self):
        self.lock=threading.RLock()
        self.engine=Engine()
        self.playing=False
        self.saved=False
        self.closed=False

    def save_if_finished(self):
        if self.engine.finished and not self.saved:
            self.engine.save(ROOT/"runs")
            self.saved=True

    def worker(self):
        while not self.closed:
            with self.lock:
                if self.playing:
                    self.engine.step()
                    if self.engine.finished:
                        self.playing=False
                    self.save_if_finished()
            time.sleep(.025)

    def control(self,request):
        with self.lock:
            action=request.get("action")
            if action=="reset":
                method=request.get("method","classical")
                scenario=request.get("scenario","normal")
                seed=int(request.get("seed",101))
                new_engine=Engine(seed,scenario,method,ROOT/"artifacts/policy.pt")
                if self.engine.events and not self.engine.finished:
                    self.engine.stop_requested=True
                    self.engine.step()
                    self.save_if_finished()
                self.engine=new_engine
                self.saved=self.playing=False
            elif action=="run":
                if self.engine.finished:
                    raise ValueError("Create a new trial before running again")
                self.playing=True
            elif action=="pause":
                self.playing=False
            elif action=="step":
                self.playing=False
                self.engine.step()
                self.save_if_finished()
            elif action=="stop":
                self.playing=False
                self.engine.stop_requested=True
                self.engine.step()
                self.save_if_finished()
            else:
                raise ValueError("Unknown command")
            return {"ok":True}


def serve(port=8765):
    session=Session()

    class Handler(BaseHTTPRequestHandler):
        def respond(self,payload,content_type="application/json",status=200):
            if not isinstance(payload,bytes):
                payload=json.dumps(payload,allow_nan=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type",content_type)
            self.send_header("Content-Length",str(len(payload)))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            path=self.path.split("?",1)[0]
            if path=="/":
                return self.respond((ROOT/"web/index.html").read_bytes(),"text/html; charset=utf-8")
            if path in ("/api/state","/api/report"):
                with session.lock:
                    state=session.engine.snapshot()
                    state["playing"]=session.playing
                    if path=="/api/report":
                        return self.respond({"summary":state["summary"],"events":session.engine.events})
                    return self.respond(state)
            if path=="/camera.png":
                with session.lock:
                    rgb,_=session.engine.camera.render(session.engine.world)
                buffer=io.BytesIO()
                Image.fromarray(rgb).save(buffer,format="PNG")
                return self.respond(buffer.getvalue(),"image/png")
            self.respond({"error":"Not found"},status=404)

        def do_POST(self):
            # Refuse cross-origin browser requests to this local service.
            origin=self.headers.get("Origin")
            if origin and origin not in (f"http://127.0.0.1:{port}",f"http://localhost:{port}"):
                return self.respond({"error":"Origin rejected"},status=403)
            if self.path!="/api/control":
                return self.respond({"error":"Not found"},status=404)
            try:
                size=int(self.headers.get("Content-Length",0))
                if not 0<size<=4096:
                    raise ValueError("Invalid request length")
                request=json.loads(self.rfile.read(size))
                self.respond(session.control(request))
            except (ValueError,TypeError,KeyError,FileNotFoundError) as error:
                self.respond({"error":str(error)},status=400)

        def log_message(self,*args):
            pass

    worker=threading.Thread(target=session.worker,daemon=True)
    worker.start()
    server=ThreadingHTTPServer(("127.0.0.1",port),Handler)
    print(f"HumanoidKitLab dashboard: http://127.0.0.1:{port}",flush=True)
    print("Kinematic simulation only. Ctrl+C stops the server.",flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        session.closed=True
        server.server_close()
