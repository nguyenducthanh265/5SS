"""Bộ file mà Dockerfile chép vào phải đủ để chạy backend; render.yaml và Dockerfile cùng chạy một app."""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_copy_set_is_enough_to_serve(tmp_path):
    for line in (ROOT / "Dockerfile").read_text(encoding="utf-8").splitlines():
        m = re.match(r"COPY\s+(.+)\s+(\S+)$", line.strip())
        if not m:
            continue
        srcs, dst = m.group(1).split(), m.group(2)
        for s in srcs:
            src = ROOT / s.rstrip("/")
            target = tmp_path / dst.rstrip("/") if dst not in (".", "./") else tmp_path
            if src.is_dir():
                shutil.copytree(src, tmp_path / dst.rstrip("/"), dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                (target if dst.endswith("/") else target.parent).mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, target / src.name if dst.endswith("/") else target)
    code = ("from fastapi.testclient import TestClient; import serve.app_llm as m; c = TestClient(m.app); "
            "r = c.post('/predict', json={'input': 'Th\\u1ee7 \\u0111\\u00f4 c\\u1ee7a Ph\\u00e1p?'}).json(); assert r['source'] == 'ai', r; print('ok')")
    r = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, encoding="utf-8",
                       env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "SYSTEM": "examples.toy_system:run",
                            "PYTHONPATH": str(tmp_path)})
    assert r.returncode == 0 and "ok" in r.stdout, r.stderr
    assert not (tmp_path / "mlkit" / "tasks").exists()  # backend không kéo theo phần train


def test_render_and_docker_start_same_app():
    render = (ROOT / "deploy" / "render.yaml").read_text(encoding="utf-8")
    docker = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "serve.app_llm:app" in render and "serve.app_llm:app" in docker
    assert "requirements-llm.txt" in render and "requirements-llm.txt" in docker
    assert re.search(r"key: ANTHROPIC_API_KEY\s*\n\s*sync: false", render)  # key không nằm trong file
