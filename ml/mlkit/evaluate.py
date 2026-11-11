"""Đánh giá một run và phân tích lỗi. Tập test chỉ được mở MỘT lần cho mỗi run (dùng --force để ép).

  python -m mlkit.evaluate --run runs/<id> --split val
  python -m mlkit.evaluate --run runs/<id> --split test     # chỉ khi đã chốt mô hình
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from . import data, metrics, modeling, runs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--split", default="val", choices=["val", "test"])
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    run = Path(a.run)
    cfg, classes = runs.load_json(run / "config.json"), runs.load_json(run / "labels.json")
    marker = runs.open_test_once(run, a.force) if a.split == "test" else run / "val_metrics.json"

    _, split = data.load_split(cfg["split_file"])
    paths = split[a.split]
    y = modeling.labels_for(paths, classes)
    device = modeling.pick_device()
    model, _ = modeling.build_model(cfg["backbone"], len(classes), pretrained=False)
    model.load_state_dict(torch.load(run / "model.pt", map_location="cpu"))
    model.to(device)
    loader = DataLoader(
        modeling.ImageSet(cfg["data_dir"], paths, y, modeling.make_transform(cfg["img_size"])),
        batch_size=cfg["batch_size"], num_workers=cfg["num_workers"],
    )
    probs = modeling.predict_probs(model, loader, device)
    pred = probs.argmax(1)
    m = metrics.summarize(y, pred, classes)
    m["accuracy_ci95"] = metrics.bootstrap_ci(y, pred)
    runs.save_json(m, marker)

    with open(run / f"{a.split}_errors.csv", "w", newline="", encoding="utf-8") as f:  # ảnh sai mà mô hình tự tin nhất
        w = csv.writer(f)
        w.writerow(["path", "true", "pred", "confidence"])
        wrong = sorted((i for i in range(len(y)) if pred[i] != y[i]), key=lambda i: -probs[i].max())
        for i in wrong[:30]:
            w.writerow([paths[i], classes[y[i]], classes[pred[i]], f"{probs[i].max():.3f}"])
    lo, hi = m["accuracy_ci95"]
    print(f"{a.split}: acc={m['accuracy']:.3f} (CI95 {lo:.3f}-{hi:.3f}) macro-F1={m['macro_f1']:.3f}; {len(wrong)} ảnh sai")
    print(f"Xem {run / (a.split + '_errors.csv')} để phân tích lỗi.")


if __name__ == "__main__":
    main()
