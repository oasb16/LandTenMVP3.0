import os
import sys
from pathlib import Path

os.environ.setdefault("OPENAI_API_KEY", "test-key")

ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT_DIR.parent
for path in (ROOT_DIR, PROJECT_ROOT):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)
