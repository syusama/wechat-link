from __future__ import annotations

import sys
from pathlib import Path


def add_repo_src_to_path() -> str | None:
    repo_src = Path(__file__).resolve().parents[1] / "src"
    if not repo_src.exists():
        return None

    repo_src_text = str(repo_src)
    if repo_src_text in sys.path:
        sys.path.remove(repo_src_text)

    sys.path.insert(0, repo_src_text)
    return repo_src_text
