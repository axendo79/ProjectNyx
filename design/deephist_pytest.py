"""Route the existing test suite to the explicit verifier experiment."""
import os
from pathlib import Path
import runpy
import sys

from deephist_prototype import ROOT, verifier

def pytest_configure(config):
    if os.environ.get("NYX_DEEPHIST_PROTOTYPE") != "1":
        return
    experimental = verifier(True)
    sys.modules["verify_store"] = experimental
    original = runpy.run_path
    def run_path(path, *args, **kwargs):
        if Path(path).resolve() == (ROOT / "scripts" / "verify_store.py").resolve():
            return experimental.__dict__.copy()
        return original(path, *args, **kwargs)
    runpy.run_path = run_path
