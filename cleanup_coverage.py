import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Удаляем файл .coverage
for p in ROOT.glob(".coverage"):
    try:
        p.unlink()
    except FileNotFoundError:
        pass

# Удаляем htmlcov
htmlcov = ROOT / "htmlcov"
if htmlcov.is_dir():
    shutil.rmtree(htmlcov)