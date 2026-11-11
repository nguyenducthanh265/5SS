#!/usr/bin/env python3
"""Tạo dữ liệu giả (3 lớp theo màu chủ đạo) để chạy thử toàn bộ pipeline trước ngày thi.

  python scripts/make_toy_data.py data 40
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

out, n = Path(sys.argv[1] if len(sys.argv) > 1 else "data"), int(sys.argv[2] if len(sys.argv) > 2 else 40)
rng = np.random.default_rng(0)
for cls, base in {"do": (210, 40, 40), "xanh": (40, 200, 60), "tim": (150, 60, 200)}.items():
    (out / cls).mkdir(parents=True, exist_ok=True)
    for i in range(n):
        arr = np.clip(np.array(base) + rng.normal(0, 35, (64, 64, 3)), 0, 255).astype("uint8")
        Image.fromarray(arr).save(out / cls / f"{cls}_{i:03d}.png")
print("Đã tạo dữ liệu giả ở", out)
