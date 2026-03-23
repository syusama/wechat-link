from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


def test_example_bootstrap_prefers_repo_src(monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    bootstrap_path = repo_root / "examples" / "_bootstrap.py"

    spec = spec_from_file_location("wechat_link_examples_bootstrap", bootstrap_path)
    assert spec is not None
    assert spec.loader is not None

    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    repo_src = str(repo_root / "src")
    monkeypatch.setattr(sys, "path", [entry for entry in sys.path if entry != repo_src])

    inserted = module.add_repo_src_to_path()

    assert inserted == repo_src
    assert sys.path[0] == repo_src
