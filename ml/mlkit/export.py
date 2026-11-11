"""Xuất mô hình sang ONNX, kiểm tra khớp với PyTorch, đo kích thước và độ trễ.

  python -m mlkit.export --run runs/<id> --out serve/model
"""
from __future__ import annotations

import argparse
import shutil
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

from . import modeling, runs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", default="serve/model")
    a = ap.parse_args()
    run, out = Path(a.run), Path(a.out)
    cfg, classes = runs.load_json(run / "config.json"), runs.load_json(run / "labels.json")
    size = cfg["img_size"]

    model, _ = modeling.build_model(cfg["backbone"], len(classes), pretrained=False)
    model.load_state_dict(torch.load(run / "model.pt", map_location="cpu"))
    model.eval()
    out.mkdir(parents=True, exist_ok=True)
    dummy = torch.randn(1, 3, size, size)
    kw = dict(input_names=["input"], output_names=["logits"], dynamic_axes={"input": {0: "batch"}, "logits": {0: "batch"}}, opset_version=17)
    try:
        torch.onnx.export(model, dummy, str(out / "model.onnx"), dynamo=False, **kw)
    except TypeError:  # torch cũ không có tham số dynamo
        torch.onnx.export(model, dummy, str(out / "model.onnx"), **kw)

    sess = ort.InferenceSession(str(out / "model.onnx"), providers=["CPUExecutionProvider"])
    x = torch.randn(2, 3, size, size)
    with torch.no_grad():
        ref = model(x).numpy()
    got = sess.run(None, {"input": x.numpy()})[0]
    diff = float(np.abs(ref - got).max())
    if diff > 1e-3:
        raise SystemExit(f"ONNX lệch PyTorch quá nhiều (max diff {diff:.5f}); không dùng bản xuất này.")
    t = time.time()
    for _ in range(20):
        sess.run(None, {"input": x[:1].numpy()})
    ms = (time.time() - t) / 20 * 1000

    runs.save_json(classes, out / "labels.json")
    runs.save_json({"size": size, **modeling.NORM}, out / "preprocess.json")
    shutil.copy(run / "config.json", out / "config.json")
    mb = (out / "model.onnx").stat().st_size / 1e6
    print(f"Xuất xong vào {out}: {mb:.1f} MB, ~{ms:.0f} ms/ảnh trên CPU, lệch PyTorch {diff:.1e}")


if __name__ == "__main__":
    main()
