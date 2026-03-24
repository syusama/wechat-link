from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


def load_example_state_module():
    repo_root = Path(__file__).resolve().parents[1]
    module_path = repo_root / "examples" / "_example_state.py"

    spec = spec_from_file_location("wechat_link_example_state", module_path)
    assert spec is not None
    assert spec.loader is not None

    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_load_session_requires_existing_file(tmp_path, monkeypatch) -> None:
    module = load_example_state_module()
    session_path = tmp_path / "wechat-link-session.json"

    monkeypatch.setattr(module, "STATE_DIR", tmp_path)
    monkeypatch.setattr(module, "SESSION_PATH", session_path)

    with pytest.raises(SystemExit, match="login_session.py"):
        module.load_session()


def test_save_and_load_last_context_round_trip(tmp_path, monkeypatch) -> None:
    module = load_example_state_module()
    context_path = tmp_path / "last-message-context.json"

    monkeypatch.setattr(module, "STATE_DIR", tmp_path)
    monkeypatch.setattr(module, "LAST_CONTEXT_PATH", context_path)

    saved_path = module.save_last_context(
        from_user_id="user@im.wechat",
        context_token="ctx-1",
        text="hello",
    )
    loaded = module.load_last_context()

    assert saved_path == context_path
    assert loaded == {
        "from_user_id": "user@im.wechat",
        "context_token": "ctx-1",
        "text": "hello",
    }
