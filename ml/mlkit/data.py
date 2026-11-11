"""Chia dữ liệu một lần, đóng băng vào split.json và kiểm tra rò rỉ.

Cấu trúc dữ liệu: data/<tên_lớp>/<ảnh>. Chạy: python -m mlkit.data --config configs/base.yaml
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def list_samples(root):
    """Trả về (danh sách lớp, [(đường_dẫn_tương_đối, chỉ_số_lớp)])."""
    root = Path(root)
    classes = sorted(p.name for p in root.iterdir() if p.is_dir())
    items = [
        ((f.relative_to(root)).as_posix(), i)
        for i, c in enumerate(classes)
        for f in sorted((root / c).rglob("*"))
        if f.suffix.lower() in IMG_EXT
    ]
    return classes, items


def group_of(path, group_regex=None, groups=None):
    """Nhóm của một mẫu. Mẫu cùng nhóm (cùng video, cùng bệnh nhân...) phải nằm cùng một tập.
    `groups` là dict mẫu -> nhóm (dùng cho dữ liệu bảng/tín hiệu); nếu không có thì dùng group_regex trên tên file."""
    if groups is not None:
        return groups[path]
    if group_regex:
        m = re.search(group_regex, Path(path).name)
        if m:
            return m.group(1)
    return path


def make_split(items, ratios=(0.7, 0.15, 0.15), seed=42, group_regex=None, groups=None):
    """Chia train/val/test phân tầng theo lớp, không tách một nhóm ra nhiều tập."""
    members_of = defaultdict(list)
    for path, label in items:
        members_of[group_of(path, group_regex, groups)].append((path, label))
    by_class = defaultdict(list)
    for g, members in members_of.items():
        by_class[Counter(l for _, l in members).most_common(1)[0][0]].append(g)

    rng = np.random.default_rng(seed)
    out = {"train": [], "val": [], "test": []}
    for label in sorted(by_class):
        gs = sorted(by_class[label])
        if len(gs) < 3:
            raise ValueError(f"Lớp {label} chỉ có {len(gs)} nhóm ảnh; cần ít nhất 3 để chia train/val/test.")
        rng.shuffle(gs)
        n_val = max(1, round(len(gs) * ratios[1]))
        n_test = max(1, round(len(gs) * ratios[2]))
        parts = {"val": gs[:n_val], "test": gs[n_val:n_val + n_test], "train": gs[n_val + n_test:]}
        for name, part in parts.items():
            for g in part:
                out[name] += [p for p, _ in members_of[g]]
    return {k: sorted(v) for k, v in out.items()}


def file_md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def find_leaks(split, root=None, group_regex=None, groups=None):
    """Trả về danh sách lỗi rò rỉ (rỗng nghĩa là sạch)."""
    problems, owner = [], {}
    for name, paths in split.items():
        for p in paths:
            if p in owner and owner[p] != name:
                problems.append(f"Ảnh {p} nằm ở cả {owner[p]} và {name}")
            owner[p] = name
    group_owner = {}
    for name, paths in split.items():
        for p in paths:
            g = group_of(p, group_regex, groups)
            if g in group_owner and group_owner[g] != name:
                problems.append(f"Nhóm {g} bị tách ra {group_owner[g]} và {name}")
            group_owner[g] = name
    if root is not None:
        hash_owner = {}
        for name, paths in split.items():
            for p in paths:
                h = file_md5(Path(root) / p)
                if h in hash_owner and hash_owner[h][1] != name:
                    problems.append(f"Nội dung trùng nhau: {hash_owner[h][0]} ({hash_owner[h][1]}) và {p} ({name})")
                hash_owner.setdefault(h, (p, name))
    return problems


def save_split(split, classes, path, meta=None):
    Path(path).write_text(json.dumps({"classes": classes, "meta": meta or {}, "split": split}, indent=1), encoding="utf-8")


def load_split(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    return d["classes"], d["split"]


def prepare(cfg):
    """Tạo split.json nếu chưa có (đóng băng), rồi kiểm tra rò rỉ và độ lệch lớp."""
    root, split_file = Path(cfg["data_dir"]), Path(cfg["split_file"])
    classes, items = list_samples(root)
    if not classes:
        raise SystemExit(f"Không thấy thư mục lớp trong {root}")
    if split_file.exists():
        classes_saved, split = load_split(split_file)
        if classes_saved != classes:
            raise SystemExit("Danh sách lớp đã đổi so với split.json. Xóa split.json nếu bạn thật sự muốn chia lại.")
        print(f"Dùng lại {split_file} (đã đóng băng).")
    else:
        split = make_split(items, tuple(cfg["ratios"]), cfg["seed"], cfg.get("group_regex"))
        save_split(split, classes, split_file, {"seed": cfg["seed"], "ratios": cfg["ratios"]})
        print(f"Đã tạo {split_file}. Commit file này để cả đội dùng cùng một cách chia.")
    problems = find_leaks(split, root, cfg.get("group_regex"))
    for p in problems:
        print("RÒ RỈ:", p)
    label_of = dict(items)
    for name, paths in split.items():
        counts = Counter(classes[label_of[p]] for p in paths if p in label_of)
        print(f"{name:5s} {len(paths):6d} ảnh  {dict(counts)}")
    all_counts = Counter(l for _, l in items)
    if max(all_counts.values()) > 3 * min(all_counts.values()):
        print("CẢNH BÁO: các lớp lệch hơn 3 lần; dùng class_weights: balanced và nhìn macro-F1, không chỉ accuracy.")
    if problems:
        raise SystemExit(f"Có {len(problems)} lỗi rò rỉ; sửa trước khi huấn luyện.")
    return classes, split


if __name__ == "__main__":
    import yaml

    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/base.yaml")
    prepare(yaml.safe_load(open(ap.parse_args().config, encoding="utf-8")))
