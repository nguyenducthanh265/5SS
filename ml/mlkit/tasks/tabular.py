"""Dữ liệu bảng và văn bản (kiểu Kaggle): phân loại hoặc hồi quy từ file CSV.

  python -m mlkit.tasks.tabular train --config configs/tabular.yaml [--set model=hgb tag=hgb]
  python -m mlkit.tasks.tabular evaluate --run runs/<id> --split val|test
Cột văn bản (text_cols) được biến thành TF-IDF, nên đây cũng là baseline cho bài phân loại văn bản.
"""
from __future__ import annotations

import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .. import data, metrics, runs
from .common import cli, write_errors

LINEAR = {"logreg", "ridge"}


def infer_task(y, task):
    if task != "auto":
        return task
    return "classification" if (y.dtype == object or str(y.dtype) in ("category", "bool") or y.nunique() <= 20) else "regression"


def split_rows(df, y, task, cfg):
    """Chia theo chỉ số dòng; có group_col thì cả nhóm (cùng người, cùng cửa hàng...) nằm cùng một tập."""
    codes = pd.factorize(y)[0] if task == "classification" else pd.qcut(y, 5, labels=False, duplicates="drop").to_numpy()
    items = [(str(i), int(c)) for i, c in enumerate(codes)]
    groups = {str(i): str(g) for i, g in enumerate(df[cfg["group_col"]])} if cfg.get("group_col") else None
    s = data.make_split(items, tuple(cfg["ratios"]), cfg["seed"], groups=groups)
    return {k: [int(i) for i in v] for k, v in s.items()}, groups


def leak_report(df, feature_cols, y, split, task, groups):
    """Trả về (lỗi, cảnh báo). Lỗi làm dừng huấn luyện."""
    str_split = {k: [str(i) for i in v] for k, v in split.items()}
    errors = data.find_leaks(str_split, groups=groups) if groups else []
    key = pd.util.hash_pandas_object(df[feature_cols].astype(str), index=False).to_numpy()
    owner = {}
    for name, idx in split.items():
        for i in idx:
            if key[i] in owner and owner[key[i]] != name:
                errors.append(f"Dòng {i} ({name}) trùng toàn bộ đặc trưng với dòng ở {owner[key[i]]}")
                break
            owner.setdefault(key[i], name)
    warns = []
    target = pd.factorize(y)[0] if task == "classification" else y.to_numpy(dtype=float)
    for c in feature_cols:
        if pd.api.types.is_numeric_dtype(df[c]) and df[c].nunique() > 1:
            r = np.corrcoef(df[c].fillna(df[c].median()), target)[0, 1]
            if abs(r) > 0.98:
                warns.append(f"Cột {c} tương quan {r:.3f} với nhãn: có thể là rò rỉ nhãn (thông tin chỉ biết sau khi có kết quả).")
    return errors, warns


def build_pipeline(df, feature_cols, cfg, task):
    text = [c for c in cfg.get("text_cols") or [] if c in feature_cols]
    rest = [c for c in feature_cols if c not in text]
    num = [c for c in rest if pd.api.types.is_numeric_dtype(df[c])]
    cat = [c for c in rest if c not in num]
    linear = cfg["model"] in LINEAR
    if text and not linear:
        raise SystemExit("Cột văn bản chỉ dùng với model logreg/ridge (TF-IDF cho ra ma trận thưa).")
    parts = []
    if num:
        parts.append(("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), num))
    if cat:
        parts.append(("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                                      ("oh", OneHotEncoder(handle_unknown="ignore", sparse_output=linear))]), cat))
    for c in text:
        parts.append((f"txt_{c}", TfidfVectorizer(max_features=20000, ngram_range=(1, 2), sublinear_tf=True), c))
    cw = "balanced" if cfg.get("class_weights") == "balanced" else None
    seed = cfg["seed"]
    models = {
        ("classification", "logreg"): lambda: LogisticRegression(max_iter=2000, class_weight=cw),
        ("classification", "rf"): lambda: RandomForestClassifier(300, class_weight=cw, n_jobs=-1, random_state=seed),
        ("classification", "hgb"): lambda: HistGradientBoostingClassifier(class_weight=cw, random_state=seed),
        ("regression", "ridge"): lambda: Ridge(),
        ("regression", "rf"): lambda: RandomForestRegressor(300, n_jobs=-1, random_state=seed),
        ("regression", "hgb"): lambda: HistGradientBoostingRegressor(random_state=seed),
    }
    if (task, cfg["model"]) not in models:
        raise SystemExit(f"model {cfg['model']} không hợp lệ cho {task}")
    return Pipeline([("prep", ColumnTransformer(parts, sparse_threshold=1.0 if linear else 0.0)), ("model", models[(task, cfg["model"])]())])


def score(pipe, X, y, task, classes):
    if task == "classification":
        proba = pipe.predict_proba(X)
        return metrics.summarize(y, proba.argmax(1), classes, proba), proba
    pred = pipe.predict(X)
    return metrics.regression_summary(y, pred), pred


def train(cfg):
    runs.set_seed(cfg["seed"])
    df = pd.read_csv(cfg["csv"])
    drop = set(cfg.get("drop_cols") or []) | {cfg["target"]} | ({cfg["group_col"]} if cfg.get("group_col") else set())
    feature_cols = [c for c in df.columns if c not in drop]
    task = infer_task(df[cfg["target"]], cfg.get("task", "auto"))
    y = df[cfg["target"]]
    classes = sorted(y.astype(str).unique()) if task == "classification" else None
    yv = pd.Series(pd.Categorical(y.astype(str), categories=classes).codes) if task == "classification" else y.astype(float)
    split_file = Path(cfg["split_file"])
    if split_file.exists():
        split = {k: [int(i) for i in v] for k, v in data.load_split(split_file)[1].items()}
        groups = {str(i): str(g) for i, g in enumerate(df[cfg["group_col"]])} if cfg.get("group_col") else None
        print(f"Dùng lại {split_file} (đã đóng băng).")
    else:
        split, groups = split_rows(df, yv, task, cfg)
        data.save_split({k: [str(i) for i in v] for k, v in split.items()}, classes or [], split_file, {"seed": cfg["seed"]})
        print(f"Đã tạo {split_file}. Commit file này.")
    errors, warns = leak_report(df, feature_cols, yv, split, task, groups)
    for w in warns:
        print("CẢNH BÁO:", w)
    if errors:
        raise SystemExit("RÒ RỈ:\n" + "\n".join(errors[:10]))

    tr, va = split["train"], split["val"]
    X, t0 = df[feature_cols], time.time()
    pipe = build_pipeline(df, feature_cols, cfg, task).fit(X.iloc[tr], yv.iloc[tr])
    val, _ = score(pipe, X.iloc[va], yv.iloc[va].to_numpy(), task, classes)
    if task == "classification":
        base, prim, higher = metrics.majority_baseline(yv.iloc[tr].tolist(), yv.iloc[va].tolist(), classes), "macro_f1", True
    else:
        base, prim, higher = metrics.mean_baseline(yv.iloc[tr], yv.iloc[va]), "rmse", False

    out = runs.new_run_dir(cfg["runs_dir"], cfg["tag"], cfg["model"])
    runs.save_json({**cfg, "task": "tabular", "problem": task, "features": feature_cols}, out / "config.json")
    runs.save_json(classes or [], out / "labels.json")
    joblib.dump(pipe, out / "model.joblib")
    sub = va[:2000]
    imp = permutation_importance(pipe, X.iloc[sub], yv.iloc[sub], n_repeats=5, random_state=cfg["seed"],
                                 scoring="f1_macro" if task == "classification" else "neg_root_mean_squared_error")
    order = np.argsort(-imp.importances_mean)
    write_errors(out / "importance.csv", [(feature_cols[i], f"{imp.importances_mean[i]:.4f}") for i in order], ["feature", "importance"])
    runs.write_metrics(out, prim, higher, val, base, seconds=time.time() - t0)
    print(f"{prim}: val={val[prim]:.4f} baseline={base[prim]:.4f}. Cột quan trọng nhất: {[feature_cols[i] for i in order[:3]]}. Lưu ở {out}")
    return out


def evaluate(run, split_name, force=False):
    run = Path(run)
    cfg, classes = runs.load_json(run / "config.json"), runs.load_json(run / "labels.json")
    marker = runs.open_test_once(run, force) if split_name == "test" else run / "val_metrics.json"
    df = pd.read_csv(cfg["csv"])
    task = cfg["problem"]
    y = df[cfg["target"]]
    yv = pd.Series(pd.Categorical(y.astype(str), categories=classes).codes) if task == "classification" else y.astype(float)
    idx = [int(i) for i in data.load_split(cfg["split_file"])[1][split_name]]
    pipe = joblib.load(run / "model.joblib")
    m, out = score(pipe, df[cfg["features"]].iloc[idx], yv.iloc[idx].to_numpy(), task, classes)
    runs.save_json(m, marker)
    truth = yv.iloc[idx].to_numpy()
    if task == "classification":
        pred = out.argmax(1)
        wrong = sorted((i for i in range(len(idx)) if pred[i] != truth[i]), key=lambda i: -out[i].max())[:30]
        write_errors(run / f"{split_name}_errors.csv", [(idx[i], classes[truth[i]], classes[pred[i]], f"{out[i].max():.3f}") for i in wrong],
                     ["row", "true", "pred", "confidence"])
        print(f"{split_name}: macro-F1={m['macro_f1']:.4f} acc={m['accuracy']:.4f}")
    else:
        worst = np.argsort(-np.abs(out - truth))[:30]
        write_errors(run / f"{split_name}_errors.csv", [(idx[i], f"{truth[i]:.4g}", f"{out[i]:.4g}") for i in worst], ["row", "true", "pred"])
        print(f"{split_name}: rmse={m['rmse']:.4f} mae={m['mae']:.4f} r2={m['r2']:.3f}")


if __name__ == "__main__":
    cli(train, evaluate, "configs/tabular.yaml")
