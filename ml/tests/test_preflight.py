"""Preflight phải: không bao giờ báo GO với hệ thống giả hay khi thiếu mục bắt buộc; bắt key lộ trong app; không in giá trị key."""
import importlib
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


@pytest.fixture()
def pf(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    sys.modules.pop("preflight", None)
    return importlib.import_module("preflight")


def write_sys(tmp_path, body, name):
    (tmp_path / f"{name}.py").write_text(body, encoding="utf-8")
    sys.path.insert(0, str(tmp_path))
    sys.modules.pop(name, None)
    return f"{name}:run"


def test_default_toy_is_never_go(pf, tmp_path):
    code = pf.main(["--real"])
    rep = (tmp_path / "preflight-report.md").read_text(encoding="utf-8")
    assert code == 1 and "hệ thống giả" in rep and "CHƯA GO" in rep


def test_without_required_checks_is_incomplete(pf, tmp_path):
    spec = write_sys(tmp_path, "def run(x, timeout=None):\n    return 'Hà Nội'\n", "pf_real_a")
    code = pf.main(["--system", spec])
    assert code == 2
    rep = (tmp_path / "preflight-report.md").read_text(encoding="utf-8")
    assert "Request thật tới model | SKIP" in rep and "Smoke test trên URL deploy | SKIP" in rep


def test_real_request_failure_and_fallback_are_fail(pf, tmp_path):
    spec = write_sys(tmp_path, "def run(x, timeout=None):\n    raise RuntimeError('401 invalid x-api-key')\n", "pf_real_b")
    assert pf.main(["--system", spec, "--real"]) == 1
    spec = write_sys(tmp_path, "def run(x, timeout=None):\n    return {'output': 'mẫu', 'source': 'fallback', 'error': 'down'}\n", "pf_real_c")
    assert pf.main(["--system", spec, "--real"]) == 1


def test_provider_key_presence_checked_but_never_printed(pf, tmp_path, monkeypatch, capsys):
    spec = write_sys(tmp_path, "import anthropic\n\ndef run(x, timeout=None):\n    return 'ok'\n", "pf_real_d")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-SECRETVALUE1234567890")
    pf.main(["--system", spec])
    out = capsys.readouterr().out + (tmp_path / "preflight-report.md").read_text(encoding="utf-8")
    assert "ANTHROPIC_API_KEY" in out and "SECRETVALUE" not in out
    monkeypatch.delenv("ANTHROPIC_API_KEY")
    assert pf.main(["--system", spec]) == 1


def test_secret_scan(pf, tmp_path):
    app = tmp_path / "app"; (app / "src").mkdir(parents=True); (app / "node_modules" / "x").mkdir(parents=True)
    (app / "src" / "api.ts").write_text("const BASE = process.env.EXPO_PUBLIC_API_URL;\n", encoding="utf-8")
    (app / "node_modules" / "x" / "k.js").write_text("sk-ant-api03-ignoredbecausenodemodules000", encoding="utf-8")
    spec = write_sys(tmp_path, "def run(x, timeout=None):\n    return 'ok'\n", "pf_real_e")
    pf.main(["--system", spec, "--app-dir", str(app)])
    assert "Quét key trong mã app mobile | PASS" in (tmp_path / "preflight-report.md").read_text(encoding="utf-8")
    (app / "src" / "llm.ts").write_text('const key = "sk-ant-api03-abcdefghijklmnopqrstu";\n', encoding="utf-8")
    (app / ".env").write_text("EXPO_PUBLIC_OPENAI_KEY=abcdefghijkl\n", encoding="utf-8")
    assert pf.main(["--system", spec, "--app-dir", str(app)]) == 1
    rep = (tmp_path / "preflight-report.md").read_text(encoding="utf-8")
    assert "src/llm.ts" in rep.replace("\\", "/") and ".env" in rep


def test_localhost_url_rejected(pf, tmp_path):
    spec = write_sys(tmp_path, "def run(x, timeout=None):\n    return 'ok'\n", "pf_real_f")
    pf.main(["--system", spec, "--url", "http://127.0.0.1:8000"])
    assert "không phải localhost" in (tmp_path / "preflight-report.md").read_text(encoding="utf-8")


def test_full_go_path_with_public_looking_url(pf, tmp_path, monkeypatch):
    """Đường GO đầy đủ: request thật (hệ thống thật giả lập), URL chạy smoke PASS, app sạch.
    URL thật không có trong sandbox, nên chặn kiểm tra localhost bằng cách trỏ tên 'demo.test' về server local."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "SYSTEM": "examples.toy_system:run"}
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "serve.app_llm:app", "--port", str(port)], cwd=ROOT, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        import urllib.request
        for _ in range(50):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1); break
            except Exception:
                time.sleep(0.2)
        assert pf.is_local_url(f"http://127.0.0.1:{port}")  # bình thường bị chặn
        monkeypatch.setattr(pf, "is_local_url", lambda url: False)  # chỉ trong test: coi server local như URL công khai
        spec = write_sys(tmp_path, "def run(x, timeout=None):\n    return {'output': 'Hà Nội', 'tokens': 5, 'source': 'ai'}\n", "pf_real_g")
        app = tmp_path / "app"; app.mkdir(); (app / "App.tsx").write_text("export default 1;\n", encoding="utf-8")
        code = pf.main(["--system", spec, "--real", "--url", f"http://127.0.0.1:{port}", "--app-dir", str(app)])
        rep = (tmp_path / "preflight-report.md").read_text(encoding="utf-8")
        assert code == 0 and "GO KỸ THUẬT" in rep, rep
    finally:
        p.terminate(); p.wait()
