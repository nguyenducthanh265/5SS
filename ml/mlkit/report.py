"""Gộp mọi run (mọi loại bài toán) thành results.md. Chạy: python -m mlkit.report"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import runs

COLS = ["run", "task", "model", "metric", "val", "test", "baseline", "params (M)", "train (s)"]


def collect(runs_dir):
    rows = []
    for d in Path(runs_dir).glob("*/metrics.json"):
        m, cfg = runs.load_json(d), runs.load_json(d.parent / "config.json")
        prim = m.get("primary", "macro_f1")
        test = d.parent / "test_metrics.json"
        rows.append(
            {
                "run": d.parent.name, "task": cfg.get("task", "image"), "model": cfg.get("model") or cfg.get("backbone") or cfg.get("system", "-"),
                "metric": prim, "higher": m.get("higher_is_better", True), "val": m["val"][prim],
                "test": runs.load_json(test).get(prim) if test.exists() else None,
                "baseline": m["baseline_val"].get(prim), "params (M)": m.get("params_m"), "train (s)": m.get("train_seconds"),
            }
        )
    return sorted(rows, key=lambda r: (r["metric"], -r["val"] if r["higher"] else r["val"]))


def fmt(v):
    if v is None:
        return "-"
    if isinstance(v, float):
        return f"{v:.0f}" if abs(v) >= 100 else f"{v:.3f}"
    return str(v)


def render(rows):
    if not rows:
        return "# Kết quả\n\nChưa có run nào.\n"
    lines = ["# Kết quả thí nghiệm", "",
             "Baseline là cách đoán đơn giản nhất cho cùng chỉ số; mô hình phải thắng nó. Với chỉ số có `higher=False` (ví dụ rmse) thì càng thấp càng tốt.", "",
             "| " + " | ".join(COLS) + " |", "|" + "---|" * len(COLS)]
    lines += ["| " + " | ".join(fmt(r[c]) for c in COLS) + " |" for r in rows]
    lines += ["", "Chọn mô hình theo cột val. Cột test chỉ điền sau khi chốt mô hình và mở test đúng một lần."]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="runs")
    ap.add_argument("--out", default="results.md")
    a = ap.parse_args()
    text = render(collect(a.runs))
    Path(a.out).write_text(text, encoding="utf-8")
    print(text)
