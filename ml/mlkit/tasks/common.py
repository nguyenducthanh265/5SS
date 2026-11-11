"""Phần dùng chung cho các module bài toán: đọc config, CLI train/evaluate, ghi file lỗi."""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import yaml


def load_config(path, overrides=None):
    cfg = yaml.safe_load(open(path, encoding="utf-8"))
    for item in overrides or []:
        k, v = item.split("=", 1)
        if k not in cfg:
            raise SystemExit(f"Khóa không có trong config: {k}")
        cfg[k] = yaml.safe_load(v)
    return cfg


def cli(train_fn, evaluate_fn, default_config):
    """python -m <module> train --config ... [--set k=v]   |   python -m <module> evaluate --run runs/<id> --split val|test"""
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("train")
    t.add_argument("--config", default=default_config)
    t.add_argument("--set", nargs="*")
    e = sub.add_parser("evaluate")
    e.add_argument("--run", required=True)
    e.add_argument("--split", default="val", choices=["val", "test"])
    e.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.cmd == "train":
        train_fn(load_config(a.config, a.set))
    else:
        evaluate_fn(a.run, a.split, a.force)


def write_errors(path, rows, header):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
