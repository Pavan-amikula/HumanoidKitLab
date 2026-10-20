"""Create a portable source/model/evidence ZIP and SHA-256 manifest."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parents[1]
output=ROOT.parent/"outputs/HumanoidKitLab.zip"
output.parent.mkdir(parents=True,exist_ok=True)
files=[]
for path in sorted(ROOT.rglob("*")):
    if not path.is_file():
        continue
    relative=path.relative_to(ROOT)
    if any(part in {"__pycache__","runs",".pytest_cache",".venv",".git"} for part in relative.parts):
        continue
    # Bundle the latest paired evaluation logs only; older experiments remain on disk.
    if relative.parts[:2]==("results","trials"):
        continue
    files.append(path)
report_path=ROOT/"results/evaluation.json"
if report_path.exists():
    report=json.loads(report_path.read_text(encoding="utf-8"))
    # Exact logs are selected by seed/method/scenario, choosing latest timestamp.
    for row in report["trials"]:
        candidates=sorted((ROOT/"results/trials").glob(f"*_{row['method']}_{row['scenario']}_{row['seed']}.json"))
        if not candidates:
            raise RuntimeError("Missing evaluation trial evidence")
        actual=json.loads(candidates[-1].read_text(encoding="utf-8"))["summary"]
        if actual["success"]!=row["success"] or actual["correct_slots"]!=row["correct_slots"]:
            raise RuntimeError("Trial evidence does not match the report")
        files.append(candidates[-1])
manifest={str(path.relative_to(ROOT)).replace("\\","/"):hashlib.sha256(path.read_bytes()).hexdigest()
          for path in files}
with zipfile.ZipFile(output,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for path in files:
        archive.write(path,Path("HumanoidKitLab")/path.relative_to(ROOT))
    archive.writestr("HumanoidKitLab/SHA256_MANIFEST.json",json.dumps(manifest,indent=2))
with zipfile.ZipFile(output) as archive:
    bad=archive.testzip()
    if bad:
        raise RuntimeError(f"Corrupt archive member: {bad}")
    for name,digest in manifest.items():
        if hashlib.sha256(archive.read("HumanoidKitLab/"+name)).hexdigest()!=digest:
            raise RuntimeError(f"Hash mismatch: {name}")
print(json.dumps({"file":str(output),"files":len(files),"bytes":output.stat().st_size,
                  "sha256":hashlib.sha256(output.read_bytes()).hexdigest(),"archive_verified":True},indent=2))
