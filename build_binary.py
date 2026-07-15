#!/usr/bin/env python3
"""Build Daybreak as single Linux binary via PyInstaller. Run INSIDE Docker container."""

import subprocess, shutil, os, sys, io, tarfile
from pathlib import Path

SRC = Path("/tmp/daybreak-src")
BUILD = Path("/tmp/daybreak-build")
DIST = Path("/tmp/daybreak-dist")

for d in [BUILD, DIST, SRC]:
    if d.exists(): shutil.rmtree(d)

# 1. Copy source
shutil.copytree("/app", SRC, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git", ".daybreak"))
print("Source copied to", SRC)

# 2. Patch config.py for frozen binary
config_py = SRC / "config.py"
orig = config_py.read_text()

# When frozen: ROOT_PATH = CWD (writable), WEB_DIST_PATH = sys._MEIPASS/web/dist-app
# When unfrozen: ROOT_PATH = Path(__file__).resolve().parent (dev mode)
frozen_patch = """
import sys as _pyi_sys
if getattr(_pyi_sys, "frozen", False):
    # ROOT_PATH = CWD (writable config/logs in .daybreak/ next to binary)
    ROOT_PATH = Path.cwd()
else:
    ROOT_PATH = Path(__file__).resolve().parent
"""

old_root = "ROOT_PATH = Path(__file__).resolve().parent"
if old_root in orig:
    orig = orig.replace(old_root, frozen_patch.lstrip("\n").rstrip())
    config_py.write_text(orig)
    print("config.py: replaced ROOT_PATH with frozen-aware version")
else:
    print("WARNING: could not find expected ROOT_PATH")

# 3. Patch app.py: use sys._MEIPASS for WEB_DIST_PATH when frozen
app_py = SRC / "app.py"
app_orig = app_py.read_text()

app_patch = """
import sys as _app_sys
from pathlib import Path as _app_Path
if getattr(_app_sys, "frozen", False):
    WEB_DIST_PATH = _app_Path(_app_sys._MEIPASS) / "web" / "dist-app"
else:
    WEB_DIST_PATH = ROOT_PATH / "web" / "dist-app"

"""

old_web = 'WEB_DIST_PATH = ROOT_PATH / "web" / "dist-app"'
if old_web in app_orig:
    app_orig = app_orig.replace(old_web, app_patch.lstrip("\n").rstrip())
    app_py.write_text(app_orig)
    print("app.py: WEB_DIST_PATH set to sys._MEIPASS when frozen")
else:
    print("WARNING: could not find WEB_DIST_PATH in app.py")

# 4. Remove test / cache files
for f in list(SRC.rglob("test_*.py")) + list(SRC.rglob("__pycache__")):
    if f.is_dir():
        shutil.rmtree(f, ignore_errors=True)
    else:
        f.unlink()

# 5. Build --add-data arguments from site-packages data files
sep = os.pathsep
add_data_args = []

# Frontend dist
add_data_args.extend(["--add-data", f"web/dist-app{sep}web/dist-app"])

# Find agents SDK data files (prompts, instructions, readme)
agents_pkg = Path("/usr/local/lib/python3.13/site-packages/agents")
if agents_pkg.is_dir():
    data_extensions = (".md", ".txt", ".yaml", ".yml")
    data_src_dirs = ["sandbox", "realtime"]
    for data_dir in data_src_dirs:
        target = agents_pkg / data_dir
        if target.is_dir():
            for fpath in target.rglob("*"):
                if fpath.is_file() and fpath.suffix in data_extensions:
                    # Map e.g. /usr/local/lib/python3.13/site-packages/agents/sandbox/... -> agents/sandbox/...
                    rel = fpath.relative_to(agents_pkg)
                    add_data_args.extend(["--add-data", f"{fpath}{sep}agents/{rel.parent}"])

# Include daybreak agent config files (.daybreak/agents/...)
daybreak_agents = SRC / ".daybreak" / "agents"
if daybreak_agents.is_dir():
    for fpath in daybreak_agents.rglob("*"):
        if fpath.is_file():
            rel = fpath.relative_to(SRC)
            add_data_args.extend(["--add-data", f"{fpath}{sep}{rel.parent}"])

# Also include requirements.txt (used by app somewhere?)
req_txt = SRC / "requirements.txt"
if req_txt.is_file():
    add_data_args.extend(["--add-data", f"{req_txt}{sep}."])

for arg in add_data_args:
    print(f"  add-data: {arg}")

print(f"\nTotal --add-data entries: {len(add_data_args)//2}")
os.chdir(SRC)
cmd = (
    [sys.executable, "-m", "PyInstaller"]
    + add_data_args
    + [
        "--onefile",
        "--name", "daybreak",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "sqlmodel",
        "--hidden-import", "openai",
        "--hidden-import", "openai_agents",
        "--hidden-import", "yaml",
        "--collect-all", "sqlmodel",
        "--collect-all", "openai",
        "--collect-all", "openai_agents",
        "--distpath", str(DIST),
        "--workpath", str(BUILD),
        "--specpath", str(SRC),
        "main.py",
    ]
)

print("\nRunning: " + " ".join(str(c) for c in cmd[:6]) + " ...")
result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)

# Print logs
out_lines = result.stdout.splitlines()
err_lines = result.stderr.splitlines()
for l in out_lines[-100:]:
    print(l)
for l in err_lines[-100:]:
    print(l, file=sys.stderr)

if result.returncode != 0:
    print(f"\nBUILD FAILED", flush=True)
    sys.exit(result.returncode)

print("\n=== BUILD SUCCESSFUL ===")
binary = DIST / "daybreak"
if binary.exists():
    size_mb = binary.stat().st_size / 1024 / 1024
    print(f"  Binary: {binary} ({size_mb:.1f} MB)")

    # Tar binary and example config to stdout for extraction
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(str(binary), arcname="daybreak")
        example = SRC / ".daybreak" / "config.json.example"
        if example.exists():
            tar.add(str(example), arcname="config.json.example")
    buf.seek(0)
    sys.stdout.buffer.write(buf.getvalue())
