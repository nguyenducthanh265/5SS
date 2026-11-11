"""Mỗi lần chạy lưu vào runs/<id>/ với cấu hình, số liệu và môi trường để tái lập được."""
from __future__ import annotations

import json
import os
import platform
import random
import subprocess
import time
from pathlib import Path

import numpy as np


def new_run_dir(base, tag, backbone):
    stem = f"{time.strftime('%Y%m%d-%H%M%S')}-{backbone}-{tag}"
    for k in range(100):  # hai run cùng giây không được ghi đè lên nhau
        d = Path(base) / (stem if k == 0 else f"{stem}-{k}")
        try:
            d.mkdir(parents=True, exist_ok=False)
            return d
        except FileExistsError:
            continue
    raise RuntimeError("Không tạo được thư mục run")


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


def env_info():
    info = {"python": platform.python_version(), "platform": platform.platform()}
    try:
        import torch

        info["torch"] = torch.__version__
        info["cuda"] = torch.cuda.is_available()
    except ImportError:
        pass
    try:
        info["git"] = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        info["git"] = None
    return info


def save_json(obj, path):
    Path(path).write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def open_test_once(run_dir, force=False):
    """Hàng rào hai tầng. (1) Mỗi run chỉ mở test một lần (chặn cứng). (2) Mọi lần mở test được ghi vào
    <runs_dir>/test_log.jsonl; mở test bằng run thứ hai là dấu hiệu chọn mô hình theo test nên bị CẢNH BÁO
    (chặn cứng nếu đặt biến môi trường MLKIT_TEST_POLICY=strict). Đây là hàng rào nhắc quy trình, không phải cưỡng chế:
    với giải có scorer/hidden test riêng thì không cần. Trả về đường dẫn file kết quả test."""
    run_dir = Path(run_dir)
    marker = run_dir / "test_metrics.json"
    if marker.exists() and not force:
        raise SystemExit("Run này đã đánh giá trên test. Mở test lại là tự lừa mình; dùng --force nếu thật sự cần.")
    log = run_dir.resolve().parent / "test_log.jsonl"
    prior = []
    if log.exists():
        prior = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
        prior = [p for p in prior if p.get("run") != run_dir.name]
    if prior:
        names = ", ".join(sorted({p["run"] for p in prior}))
        msg = f"CẢNH BÁO: test đã được mở bởi run khác ({names}). Chọn mô hình dựa trên nhiều lần mở test là rò rỉ gián tiếp; chọn trên val, mở test cho ứng viên cuối cùng."
        if os.environ.get("MLKIT_TEST_POLICY") == "strict" and not force:
            raise SystemExit(msg + " (MLKIT_TEST_POLICY=strict: dừng)")
        print(msg)
    with open(log, "a", encoding="utf-8") as f:
        f.write(json.dumps({"run": run_dir.name, "t": time.time()}) + "\n")
    return marker


def write_metrics(out, primary, higher_is_better, val, baseline_val, history=None, params_m=None, seconds=0.0):
    """Schema chung cho mọi loại bài toán; report.py chỉ đọc file này."""
    save_json(
        {"primary": primary, "higher_is_better": higher_is_better, "val": val, "baseline_val": baseline_val,
         "history": history or [], "params_m": params_m, "train_seconds": seconds, "env": env_info()},
        Path(out) / "metrics.json",
    )
