"""Fine-tune một backbone. Chạy: python -m mlkit.train --config configs/base.yaml [--set khóa=giá_trị ...]"""
from __future__ import annotations

import argparse
import copy
import time
from collections import Counter

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from . import data, metrics, modeling, runs
from .tasks.common import load_config


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/base.yaml")
    ap.add_argument("--set", nargs="*", help="ghi đè cấu hình, ví dụ backbone=resnet18 tag=r18")
    a = ap.parse_args()
    cfg = load_config(a.config, a.set)

    runs.set_seed(cfg["seed"])
    classes, split = data.prepare(cfg)  # tạo/đọc split và dừng nếu có rò rỉ
    root = cfg["data_dir"]
    ytr = modeling.labels_for(split["train"], classes)
    yva = modeling.labels_for(split["val"], classes)
    base = metrics.majority_baseline(ytr, yva, classes)
    print(f"Baseline đoán lớp đông nhất: acc={base['accuracy']:.3f} macro-F1={base['macro_f1']:.3f}")

    device = modeling.pick_device()
    mk = lambda paths, labels, train: DataLoader(
        modeling.ImageSet(root, paths, labels, modeling.make_transform(cfg["img_size"], cfg["augment"], cfg["hflip"], train)),
        batch_size=cfg["batch_size"], shuffle=train, num_workers=cfg["num_workers"],
    )
    tr, va = mk(split["train"], ytr, True), mk(split["val"], yva, False)

    model, head = modeling.build_model(cfg["backbone"], len(classes), cfg["pretrained"])
    model.to(device)
    head_ids = {id(p) for p in head.parameters()}
    backbone_params = [p for p in model.parameters() if id(p) not in head_ids]
    opt = torch.optim.AdamW(
        [{"params": list(head.parameters()), "lr": cfg["lr"]}, {"params": backbone_params, "lr": cfg["lr"] * 0.1}],
        weight_decay=cfg["weight_decay"],
    )
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=cfg["epochs"])
    weight = None
    if cfg["class_weights"] == "balanced":
        c = Counter(ytr)
        weight = torch.tensor([len(ytr) / (len(classes) * c[i]) for i in range(len(classes))], dtype=torch.float32).to(device)
    loss_fn = nn.CrossEntropyLoss(weight=weight, label_smoothing=cfg["label_smoothing"])

    out = runs.new_run_dir(cfg["runs_dir"], cfg["tag"], cfg["backbone"])
    runs.save_json(cfg, out / "config.json")
    runs.save_json(classes, out / "labels.json")
    best, best_state, bad, history, t0 = -1.0, None, 0, [], time.time()

    for epoch in range(cfg["epochs"]):
        for p in backbone_params:  # đóng băng backbone ở vài epoch đầu
            p.requires_grad = epoch >= cfg["freeze_epochs"]
        model.train()
        total = 0.0
        for x, y in tr:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            loss = loss_fn(model(x), y)
            loss.backward()
            opt.step()
            total += loss.item() * len(y)
        sched.step()
        probs = modeling.predict_probs(model, va, device)
        m = metrics.summarize(yva, probs.argmax(1), classes)
        history.append({"epoch": epoch, "train_loss": total / len(tr.dataset), "val_acc": m["accuracy"], "val_macro_f1": m["macro_f1"]})
        print(f"epoch {epoch:2d} loss {history[-1]['train_loss']:.4f} val_acc {m['accuracy']:.3f} val_f1 {m['macro_f1']:.3f}")
        if m["macro_f1"] > best:
            best, best_state, bad = m["macro_f1"], copy.deepcopy(model.state_dict()), 0
        else:
            bad += 1
            if bad >= cfg["patience"]:
                print("Dừng sớm.")
                break

    model.load_state_dict(best_state)
    torch.save(best_state, out / "model.pt")
    probs = modeling.predict_probs(model, va, device)
    final = metrics.summarize(yva, probs.argmax(1), classes)
    runs.write_metrics(out, "macro_f1", True, final, base, history,
                       sum(p.numel() for p in model.parameters()) / 1e6, time.time() - t0)
    print(f"Xong. val macro-F1={final['macro_f1']:.3f} (baseline {base['macro_f1']:.3f}). Lưu ở {out}")


if __name__ == "__main__":
    main()
