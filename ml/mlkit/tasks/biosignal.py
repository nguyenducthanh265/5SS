"""Tín hiệu y sinh / chuỗi thời gian (EEG, ECG, PSG, cảm biến): phân loại cửa sổ tín hiệu, chia theo đối tượng.

Dữ liệu: file .npz gồm X (N, kênh, mẫu), y (N,), subject (N,). Dùng make_windows để cắt bản ghi dài thành cửa sổ.
  python -m mlkit.tasks.biosignal train --config configs/biosignal.yaml [--set model=cnn tag=cnn]
  python -m mlkit.tasks.biosignal evaluate --run runs/<id> --split val|test
Quy tắc sống còn: các cửa sổ của cùng một đối tượng KHÔNG được nằm ở hai tập khác nhau, và thống kê chuẩn hóa chỉ tính trên train.
"""
from __future__ import annotations

import copy
import time
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .. import data, metrics, runs
from .common import cli, write_errors

BANDS = {"delta": (0.5, 4), "theta": (4, 8), "alpha": (8, 13), "beta": (13, 30), "gamma": (30, 45)}


def make_windows(signal, win, step):
    """Cắt bản ghi (kênh, mẫu) thành các cửa sổ (n, kênh, win) bước `step` mẫu."""
    c, t = signal.shape
    starts = range(0, t - win + 1, step)
    return np.stack([signal[:, s:s + win] for s in starts]) if len(starts) else np.empty((0, c, win))


def zscore_fit(X):
    """Thống kê theo kênh, CHỈ tính trên train."""
    return X.mean(axis=(0, 2), keepdims=True), X.std(axis=(0, 2), keepdims=True) + 1e-8


def zscore_apply(X, stats):
    return (X - stats[0]) / stats[1]


def features(X, fs):
    """Đặc trưng thủ công: thống kê miền thời gian + công suất tương đối theo băng tần (Welch đơn giản bằng FFT)."""
    feats = [X.mean(2), X.std(2), np.abs(np.diff(X, axis=2)).mean(2), (X ** 2).mean(2)]
    spec = np.abs(np.fft.rfft(X, axis=2)) ** 2
    freqs = np.fft.rfftfreq(X.shape[2], 1 / fs)
    total = spec[:, :, (freqs >= 0.5) & (freqs <= 45)].sum(2) + 1e-12
    for lo, hi in BANDS.values():
        m = (freqs >= lo) & (freqs < hi)
        feats.append(spec[:, :, m].sum(2) / total if m.any() else np.zeros(X.shape[:2]))
    return np.concatenate(feats, axis=1)


def load_arrays(cfg):
    d = np.load(cfg["npz"], allow_pickle=False)
    return d["X"].astype(np.float32), d["y"].astype(int), d["subject"].astype(str)


def subject_split(y, subjects, cfg):
    items = [(str(i), int(l)) for i, l in enumerate(y)]
    groups = {str(i): str(s) for i, s in enumerate(subjects)}
    split = data.make_split(items, tuple(cfg["ratios"]), cfg["seed"], groups=groups)
    return {k: [int(i) for i in v] for k, v in split.items()}, groups


def build_cnn(n_channels, n_classes):
    import torch.nn as nn

    def block(i, o):
        return nn.Sequential(nn.Conv1d(i, o, 7, padding=3), nn.BatchNorm1d(o), nn.ReLU(), nn.MaxPool1d(2))

    return nn.Sequential(block(n_channels, 16), block(16, 32), block(32, 64), nn.AdaptiveAvgPool1d(1), nn.Flatten(),
                         nn.Dropout(0.3), nn.Linear(64, n_classes))


def train_cnn(Xtr, ytr, Xva, yva, classes, cfg):
    import torch
    import torch.nn as nn

    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = build_cnn(Xtr.shape[1], len(classes)).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg["lr"], weight_decay=1e-4)
    w = None
    if cfg.get("class_weights") == "balanced":
        cnt = np.bincount(ytr, minlength=len(classes)).clip(1)
        w = torch.tensor(len(ytr) / (len(classes) * cnt), dtype=torch.float32, device=dev)
    loss_fn = nn.CrossEntropyLoss(weight=w)
    xt, yt = torch.tensor(Xtr), torch.tensor(ytr)

    def probs(X):
        model.eval()
        with torch.no_grad():
            return torch.cat([torch.softmax(model(torch.tensor(X[i:i + 256]).to(dev)), 1).cpu() for i in range(0, len(X), 256)]).numpy()

    best, best_state, bad, hist = -1.0, None, 0, []
    for ep in range(cfg["epochs"]):
        model.train()
        perm = torch.randperm(len(xt))
        for i in range(0, len(perm), cfg["batch_size"]):
            b = perm[i:i + cfg["batch_size"]]
            opt.zero_grad()
            loss_fn(model(xt[b].to(dev)), yt[b].to(dev)).backward()
            opt.step()
        m = metrics.summarize(yva, probs(Xva).argmax(1), classes)
        hist.append({"epoch": ep, "val_macro_f1": m["macro_f1"]})
        print(f"epoch {ep:2d} val_f1 {m['macro_f1']:.3f}")
        if m["macro_f1"] > best:
            best, best_state, bad = m["macro_f1"], copy.deepcopy(model.state_dict()), 0
        else:
            bad += 1
            if bad >= cfg["patience"]:
                break
    model.load_state_dict(best_state)
    return model, probs, hist


def train(cfg):
    runs.set_seed(cfg["seed"])
    X, y, subj = load_arrays(cfg)
    classes = [str(c) for c in range(int(y.max()) + 1)] if not cfg.get("classes") else cfg["classes"]
    split_file = Path(cfg["split_file"])
    if split_file.exists():
        split = {k: [int(i) for i in v] for k, v in data.load_split(split_file)[1].items()}
        groups = {str(i): str(s) for i, s in enumerate(subj)}
        print(f"Dùng lại {split_file} (đã đóng băng).")
    else:
        split, groups = subject_split(y, subj, cfg)
        data.save_split({k: [str(i) for i in v] for k, v in split.items()}, classes, split_file, {"seed": cfg["seed"]})
        print(f"Đã tạo {split_file}. Chia theo đối tượng; commit file này.")
    problems = data.find_leaks({k: [str(i) for i in v] for k, v in split.items()}, groups=groups)
    if problems:
        raise SystemExit("RÒ RỈ:\n" + "\n".join(problems[:10]))
    tr, va = split["train"], split["val"]
    for name, idx in split.items():
        print(f"{name:5s} {len(idx):6d} cửa sổ, {len({subj[i] for i in idx})} đối tượng, phân bố nhãn {np.bincount(y[idx], minlength=len(classes)).tolist()}")

    stats = zscore_fit(X[tr])
    Xtr, Xva = zscore_apply(X[tr], stats), zscore_apply(X[va], stats)
    base = metrics.majority_baseline(y[tr].tolist(), y[va].tolist(), classes)
    t0, out = time.time(), None
    hist = []
    if cfg["model"] == "cnn":
        model, probs, hist = train_cnn(Xtr, y[tr], Xva, y[va], classes, cfg)
        pva = probs(Xva)
        params = sum(p.numel() for p in model.parameters()) / 1e6
    else:
        clf = LogisticRegression(max_iter=2000, class_weight=cfg.get("class_weights") if cfg.get("class_weights") == "balanced" else None) \
            if cfg["model"] == "logreg" else HistGradientBoostingClassifier(random_state=cfg["seed"])
        model = make_pipeline(StandardScaler(), clf).fit(features(Xtr, cfg["fs"]), y[tr])
        pva, params = model.predict_proba(features(Xva, cfg["fs"])), None
    val = metrics.summarize(y[va], pva.argmax(1), classes, pva)
    out = runs.new_run_dir(cfg["runs_dir"], cfg["tag"], cfg["model"])
    runs.save_json({**cfg, "task": "biosignal"}, out / "config.json")
    runs.save_json(classes, out / "labels.json")
    runs.save_json({"mean": stats[0].tolist(), "std": stats[1].tolist()}, out / "norm.json")
    if cfg["model"] == "cnn":
        import torch

        torch.save(model.state_dict(), out / "model.pt")
    else:
        joblib.dump(model, out / "model.joblib")
    runs.write_metrics(out, "macro_f1", True, val, base, hist, params, time.time() - t0)
    print(f"val macro-F1={val['macro_f1']:.3f} (baseline {base['macro_f1']:.3f}), balanced acc={val['balanced_accuracy']:.3f}. Lưu ở {out}")
    return out


def predict(run, X, cfg, classes):
    stats = runs.load_json(Path(run) / "norm.json")
    Xn = zscore_apply(X, (np.array(stats["mean"]), np.array(stats["std"])))
    if cfg["model"] == "cnn":
        import torch

        model = build_cnn(X.shape[1], len(classes))
        model.load_state_dict(torch.load(Path(run) / "model.pt", map_location="cpu"))
        model.eval()
        with torch.no_grad():
            return torch.cat([torch.softmax(model(torch.tensor(Xn[i:i + 256].astype(np.float32))), 1) for i in range(0, len(Xn), 256)]).numpy()
    return joblib.load(Path(run) / "model.joblib").predict_proba(features(Xn, cfg["fs"]))


def evaluate(run, split_name, force=False):
    run = Path(run)
    cfg, classes = runs.load_json(run / "config.json"), runs.load_json(run / "labels.json")
    marker = runs.open_test_once(run, force) if split_name == "test" else run / "val_metrics.json"
    X, y, subj = load_arrays(cfg)
    idx = [int(i) for i in data.load_split(cfg["split_file"])[1][split_name]]
    p = predict(run, X[idx], cfg, classes)
    m = metrics.summarize(y[idx], p.argmax(1), classes, p)
    # Số liệu theo đối tượng: cho thấy mô hình có ổn định giữa các người hay chỉ tốt với vài người
    per_subject = {}
    for s in sorted({subj[i] for i in idx}):
        mask = np.array([subj[i] == s for i in idx])
        per_subject[s] = float((p[mask].argmax(1) == y[idx][mask]).mean())
    m["accuracy_by_subject"] = per_subject
    runs.save_json(m, marker)
    write_errors(run / f"{split_name}_by_subject.csv", sorted(per_subject.items(), key=lambda kv: kv[1]), ["subject", "accuracy"])
    print(f"{split_name}: macro-F1={m['macro_f1']:.3f} balanced acc={m['balanced_accuracy']:.3f}"
          + (f" AUROC={m['auroc']:.3f}" if "auroc" in m else "")
          + f"; đối tượng kém nhất: {min(per_subject.items(), key=lambda kv: kv[1])}")


if __name__ == "__main__":
    cli(train, evaluate, "configs/biosignal.yaml")
