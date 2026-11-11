import importlib
import io
import json
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
onnx = pytest.importorskip("onnx")
pytest.importorskip("onnxruntime")
Image = pytest.importorskip("PIL.Image")
from onnx import TensorProto, helper  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _utf8_env(**extra):
    """Tiến trình con xuất UTF-8 và tiến trình cha đọc UTF-8 (pytest -X utf8 KHÔNG truyền cờ -X sang tiến trình con)."""
    import os
    return {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", **extra}
CLASSES = ["do", "xanh", "tim"]


def build_tiny_onnx(path):
    """Mô hình giả: trung bình theo kênh rồi nhân ma trận 3x3 -> logits (đủ để kiểm tra pipeline phục vụ)."""
    w = helper.make_tensor("W", TensorProto.FLOAT, [3, 3], np.eye(3, dtype=np.float32).ravel() * 10)
    nodes = [
        helper.make_node("ReduceMean", ["input"], ["m"], axes=[2, 3], keepdims=0),
        helper.make_node("MatMul", ["m", "W"], ["logits"]),
    ]
    g = helper.make_graph(nodes, "tiny",
                          [helper.make_tensor_value_info("input", TensorProto.FLOAT, ["batch", 3, "h", "w"])],
                          [helper.make_tensor_value_info("logits", TensorProto.FLOAT, ["batch", 3])], [w])
    m = helper.make_model(g, opset_imports=[helper.make_opsetid("", 13)])
    m.ir_version = 8
    onnx.save(m, str(path))


@pytest.fixture()
def model_dir(tmp_path, monkeypatch):
    build_tiny_onnx(tmp_path / "model.onnx")
    (tmp_path / "labels.json").write_text(json.dumps(CLASSES), encoding="utf-8")
    (tmp_path / "preprocess.json").write_text(json.dumps({"size": 32, "mean": [0, 0, 0], "std": [1, 1, 1]}), encoding="utf-8")
    monkeypatch.setenv("MODEL_DIR", str(tmp_path))
    monkeypatch.syspath_prepend(str(ROOT))
    sys.modules.pop("serve.app", None)
    return tmp_path


def png(color):
    b = io.BytesIO()
    Image.new("RGB", (40, 40), color).save(b, "PNG")
    return b.getvalue()


def test_health_and_predict(model_dir):
    from fastapi.testclient import TestClient

    app = importlib.import_module("serve.app").app
    c = TestClient(app)
    assert c.get("/health").json() == {"status": "ok", "classes": CLASSES}
    r = c.post("/predict", files={"file": ("a.png", png((255, 0, 0)), "image/png")}).json()
    assert r["label"] == "do" and r["confidence"] > 0.9 and len(r["top3"]) == 3
    r = c.post("/predict", files={"file": ("b.png", png((0, 0, 255)), "image/png")}).json()
    assert r["label"] == "tim"
    assert c.post("/predict", files={"file": ("x.txt", b"khong phai anh", "text/plain")}).status_code == 400


def test_smoke_script_against_live_server(model_dir):
    import uvicorn

    app = importlib.import_module("serve.app").app
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)
    try:
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "smoke_test.py"), f"http://127.0.0.1:{port}"],
                           capture_output=True, text=True, encoding="utf-8", env=_utf8_env(), timeout=60)
        assert r.returncode == 0, r.stdout + r.stderr
        assert "RESULT: PASS" in r.stdout
        bad = subprocess.run([sys.executable, str(ROOT / "scripts" / "smoke_test.py"), "http://127.0.0.1:1"],
                             capture_output=True, text=True, encoding="utf-8", env=_utf8_env(), timeout=60)
        assert bad.returncode == 1  # server chết phải bị phát hiện
    finally:
        server.should_exit = True
        t.join(5)
