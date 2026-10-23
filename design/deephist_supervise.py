"""Sequential supervisor: bounded child processes and an auditable command log."""
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "design" / "deephist-evidence"
OUT.mkdir(exist_ok=True)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["PYTHONPATH"] = os.pathsep.join([
    str(ROOT / "src"), str(ROOT / "design"),
    r"D:\ProjectNyx\.venv\Lib\site-packages"])
def run(name, command, env=None):
    before = time.perf_counter()
    print("START", name, command, flush=True)
    with (OUT / name).open("w", encoding="utf-8") as output:
        try:
            result = subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
                                    timeout=1200, env=env, check=False)
            row = dict(command=command, status="completed" if result.returncode == 0 else "failed",
                       returncode=result.returncode, seconds=time.perf_counter()-before, log=name)
        except subprocess.TimeoutExpired:
            row = dict(command=command, status="censored", limit_seconds=1200,
                       seconds=time.perf_counter()-before, log=name)
    with (OUT / "supervisor.jsonl").open("a", encoding="utf-8") as record:
        record.write(json.dumps(row)+"\n")
    print(row, flush=True)
    return row["status"] == "completed"

if not run("smoke.txt", [sys.executable, "-B", "design/deephist_experiment.py", "smoke"]):
    raise SystemExit("measurement smoke failed")
if not run("baseline-pytest.txt", [sys.executable, "-B", "-m", "pytest", "-q", "tests",
                                   "design/test_deephist.py"]):
    raise SystemExit("baseline suite incomplete; inspect before measuring")
env = dict(os.environ, NYX_DEEPHIST_PROTOTYPE="1")
if not run("prototype-pytest.txt", [sys.executable, "-B", "-m", "pytest", "-q", "tests",
                                  "design/test_deephist.py", "-p", "deephist_pytest"], env):
    raise SystemExit("prototype suite incomplete; inspect before measuring")
run("store-scaling.txt", [sys.executable, "-B", "scripts/probe_store_scaling.py",
    "--sizes", "250", "500", "1000", "2000", "--skip-projector-1",
    "--json", str(OUT / "store-scaling.json")])
# The experiment supervisor itself imposes 1200 seconds on every child job;
# its total wall time is intentionally not treated as one benchmark.
subprocess.run([sys.executable, "-B", "design/deephist_experiment.py", "all"], cwd=ROOT, check=True)
run("verifier-cli.json", [sys.executable, "-B", "scripts/verify_store.py", "--db",
    "scratch/deephist/concentrated-2-250.sqlite", "--projector", "2", "--json"])
