"""Backend AI JSON (serve/app_llm.py) và smoke test chế độ JSON. Chỉ cần fastapi/uvicorn/httpx, không cần onnx/torch."""
import importlib
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _utf8_env(**extra):
    """Tiến trình con xuất UTF-8 và tiến trình cha đọc UTF-8 (pytest -X utf8 KHÔNG truyền cờ -X sang tiến trình con)."""
    return {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", **extra}


def test_llm_app_schema_fallback_and_validation(monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.chdir(ROOT)
    monkeypatch.setenv("SYSTEM", "examples.toy_system:run")
    sys.modules.pop("serve.app_llm", None)
    m = importlib.import_module("serve.app_llm")
    c = TestClient(m.app)
    assert c.get("/health").json()["status"] == "ok"
    r = c.post("/predict", json={"input": "Thủ đô của Pháp là gì?"}).json()
    assert r["source"] == "ai" and r["output"]
    assert c.post("/predict", content=b"{hong", headers={"Content-Type": "application/json"}).status_code == 422
    assert c.post("/predict", json={"input": ""}).status_code == 422
    m.system = lambda x: (_ for _ in ()).throw(RuntimeError("API down"))
    r = c.post("/predict", json={"input": "x"}).json()
    assert r["source"] == "fallback" and r["error"] == "RuntimeError"


def test_smoke_script_json_mode_against_live_server():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
    env = _utf8_env(SYSTEM="examples.toy_system:run", ALLOW_FORCE_FALLBACK="1")
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "serve.app_llm:app", "--port", str(port)], cwd=ROOT, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        import urllib.request
        for _ in range(50):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1); break
            except Exception:
                time.sleep(0.2)
        r = subprocess.run([sys.executable, "scripts/smoke_test.py", f"http://127.0.0.1:{port}", "--kind", "json",
                            "--payload", '{"input": "Th\\u1ee7 \\u0111\\u00f4 c\\u1ee7a Ph\\u00e1p l\\u00e0 g\\u00ec?"}', "--expect-key", "output", "--check-fallback"],
                           cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=_utf8_env(), timeout=60)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "RESULT: PASS source=ai" in r.stdout
    finally:
        p.terminate(); p.wait()


def _live(env_extra):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
    env = _utf8_env(**env_extra)
    p = subprocess.Popen([sys.executable, "-m", "uvicorn", "serve.app_llm:app", "--port", str(port)], cwd=ROOT, env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import urllib.request
    for _ in range(50):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1); break
        except Exception:
            time.sleep(0.2)
    return p, port


def test_smoke_fails_when_server_only_returns_fallback():
    """Lỗi đã báo: smoke từng PASS khi AI hỏng. Hệ thống luôn ném lỗi -> server trả fallback -> smoke phải FAIL."""
    p, port = _live({"SYSTEM": "examples.broken_system:run"})
    try:
        base = [sys.executable, "scripts/smoke_test.py", f"http://127.0.0.1:{port}", "--kind", "json"]
        r = subprocess.run(base, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=_utf8_env(), timeout=60)
        assert r.returncode == 1 and "[source=ai]" in r.stdout and "RESULT: FAIL" in r.stdout, r.stdout
        r = subprocess.run(base + ["--transport-only"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=_utf8_env(), timeout=60)
        assert r.returncode == 0 and "RESULT: PASS transport-only" in r.stdout, r.stdout
    finally:
        p.terminate(); p.wait()


def test_slow_calls_do_not_block_later_requests(monkeypatch):
    """Lỗi đã báo: 8 lời gọi treo chiếm hết worker, request sau timeout dù hệ thống đã khỏe; tác vụ trong queue chạy muộn.
    Giờ: không có queue; quá MAX_INFLIGHT trả ngay 503 busy; khi lời gọi treo kết thúc thì chỗ được trả lại."""
    from fastapi.testclient import TestClient
    monkeypatch.chdir(ROOT)
    monkeypatch.setenv("MAX_INFLIGHT", "2"); monkeypatch.setenv("TIMEOUT_S", "0.3")
    sys.modules.pop("serve.app_llm", None)
    m = importlib.import_module("serve.app_llm")
    gate, started = threading.Event(), []
    def slow(x):
        started.append(x); gate.wait(5); return "muộn"
    m.system = slow
    c = TestClient(m.app)
    for i in range(2):
        r = c.post("/predict", json={"input": f"chậm {i}"}).json()
        assert r["source"] == "fallback" and r["error"] == "timeout"
    m.system = lambda x: "nhanh"
    t = time.time()
    r = c.post("/predict", json={"input": "khỏe"})
    assert r.status_code == 503 and r.json()["source"] == "busy" and time.time() - t < 0.25  # trả ngay, không treo
    gate.set()
    for _ in range(50):
        if m.slots._value == 2: break
        time.sleep(0.05)
    r = c.post("/predict", json={"input": "khỏe"}).json()
    assert r["source"] == "ai" and r["output"] == "nhanh"
    assert len(started) == 2  # không có request nào bị xếp hàng rồi chạy muộn


def test_timeout_is_passed_to_system_client(monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.chdir(ROOT); monkeypatch.setenv("TIMEOUT_S", "7")
    sys.modules.pop("serve.app_llm", None)
    m = importlib.import_module("serve.app_llm")
    seen = {}
    def sysfn(x, timeout=None):
        seen["t"] = timeout; return "ok"
    m.system = sysfn
    assert TestClient(m.app).post("/predict", json={"input": "a"}).json()["source"] == "ai"
    assert seen["t"] == 7.0


def test_stats_counts_real_usage_by_device(monkeypatch, capsys):
    """/stats là số liệu dùng thật cho pitch: chỉ lượt AI thành công mới vào ai_requests/devices_ai; id máy không lộ ra log."""
    from fastapi.testclient import TestClient
    monkeypatch.chdir(ROOT)
    monkeypatch.setenv("SYSTEM", "examples.toy_system:run")
    sys.modules.pop("serve.app_llm", None)
    m = importlib.import_module("serve.app_llm")
    c = TestClient(m.app)
    assert c.get("/stats").json()["ai_requests"] == 0
    for dev in ("may-A", "may-A", "may-B"):
        assert c.post("/predict", json={"input": "Thủ đô của Pháp là gì?"}, headers={"X-Device-Id": dev}).json()["source"] == "ai"
    c.post("/predict", json={"input": "không có id máy"})
    m.system = lambda x: (_ for _ in ()).throw(RuntimeError("API down"))
    assert c.post("/predict", json={"input": "x"}, headers={"X-Device-Id": "may-C"}).json()["source"] == "fallback"
    s = c.get("/stats").json()
    assert (s["ai_requests"], s["fallback"], s["busy"], s["devices_total"], s["devices_ai"]) == (4, 1, 0, 3, 2)
    out = capsys.readouterr().out
    assert out.count("USAGE source=ai") == 4 and "USAGE source=fallback" in out
    assert "may-A" not in out and "may-C" not in out  # chỉ in dạng băm
