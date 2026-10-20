"""Read-only bridge for publishing selected files via GitHub's Git Data API.

Contains no credentials and makes no network requests.
"""
from pathlib import Path
import argparse
import base64
import hashlib
import json

ROOT=Path(__file__).resolve().parents[1]
BINARY={".png",".gif",".mp4",".npz",".pt"}


def selected():
    files=[]
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():continue
        relative=path.relative_to(ROOT)
        if any(p in {"__pycache__","runs",".venv",".git",".pytest_cache"} for p in relative.parts):continue
        if relative.parts[:2]==("results","trials"):continue
        raw=path.read_bytes()
        files.append({"path":relative.as_posix(),"bytes":len(raw),
                      "binary":path.suffix.lower() in BINARY,
                      "git_blob_sha":hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()})
    return files


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--read")
    parser.add_argument("--offset",type=int,default=0)
    parser.add_argument("--length",type=int,default=24576)
    parser.add_argument("--text-batch",type=int)
    args=parser.parse_args()
    if args.text_batch is not None:
        entries=[f for f in selected() if not f["binary"]][args.text_batch:args.text_batch+8]
        print(json.dumps([{"path":f["path"],"mode":"100644","type":"blob",
                           "content":(ROOT/f["path"]).read_bytes().decode("utf-8-sig")}
                          for f in entries],ensure_ascii=True))
        return
    if not args.read:
        print(json.dumps(selected(),ensure_ascii=True))
        return
    path=(ROOT/args.read).resolve()
    if not path.is_relative_to(ROOT) or args.offset<0 or args.length<=0:
        raise ValueError("Invalid project file or byte range")
    raw=path.read_bytes()
    if path.suffix.lower() in BINARY:
        chunk=raw[args.offset:args.offset+args.length]
        print(json.dumps({"path":args.read,"content":base64.b64encode(chunk).decode("ascii"),
                          "encoding":"base64","bytes":len(chunk)}))
    else:
        print(json.dumps({"path":args.read,"content":raw.decode("utf-8-sig"),"encoding":"utf-8"},ensure_ascii=True))


if __name__=="__main__":main()
