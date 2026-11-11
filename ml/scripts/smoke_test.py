#!/usr/bin/env python3
"""Kiểm tra nhanh API đã deploy. Chạy trên URL THẬT, không phải localhost, trước khi demo.

  API nhận ảnh:  python scripts/smoke_test.py https://ten-app.onrender.com --kind image [--image anh.jpg]
  API JSON (LLM, RAG, bảng): python scripts/smoke_test.py https://ten-app.onrender.com --kind json \
                     --payload '{"input": "câu thử"}' --expect-key output [--path /predict]
  Kiểm tra: /health ok; request hợp lệ trả đúng schema dưới --max-ms; request hỏng bị từ chối 4xx.
  Chế độ json mặc định còn đòi source == "ai" và không có "error" (cổng xác nhận AI chạy thật; đổi bằng --require).
  --check-fallback: thêm một ca riêng gửi header X-Force-Fallback: 1 (server cần ALLOW_FORCE_FALLBACK=1) và đòi source == "fallback".
  --transport-only: chỉ kiểm HTTP/JSON; kết quả in rõ là KHÔNG chứng minh AI chạy.
Thoát mã 0 nếu mọi thứ đạt, 1 nếu có lỗi.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
import urllib.error
import urllib.request
import uuid

for _st in (sys.stdout, sys.stderr):  # terminal Windows cp1252: không sập vì tiếng Việt
    try:
        _st.reconfigure(errors="replace")
    except Exception:
        pass


def sample_png():
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (200, 30, 30)).save(buf, "PNG")
    return buf.getvalue(), "sample.png"


def post_image(url, data, name):
    b = uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{name}\"\r\n"
            f"Content-Type: application/octet-stream\r\n\r\n").encode() + data + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(url, body, {"Content-Type": f"multipart/form-data; boundary={b}"})
    return urllib.request.urlopen(req, timeout=30)


def post_json(url, body: bytes, headers=None):
    req = urllib.request.Request(url, body, {"Content-Type": "application/json", **(headers or {})})
    return urllib.request.urlopen(req, timeout=60)


def json_checks(url, payload, keys, max_ms, check, is_ok, require=(), check_fallback=False, transport_only=False):
    try:
        t = time.time()
        r = json.load(post_json(url, json.dumps(payload).encode()))
        ms = (time.time() - t) * 1000
        missing = [k for k in keys if k not in r]
        check("trả JSON đúng schema", not missing, f"thiếu {missing}" if missing else str({k: str(r[k])[:60] for k in keys}))
        check("không trả rỗng", all(isinstance(r.get(k), str) and r[k].strip() for k in keys if k in r) and not missing)
        for cond in require:
            k, v = cond.split("=", 1)
            check(f"{k} == {v!r} [{k}={v}]", str(r.get(k)) == v, f"nhận {r.get(k)!r}" + (f", error={r['error']!r}" if r.get("error") else ""))
        if require:
            check("không có trường error", not r.get("error"), str(r.get("error") or ""))
        check(f"độ trễ < {max_ms:.0f} ms", ms < max_ms, f"{ms:.0f} ms (lần đầu có thể chậm do khởi động nguội)")
    except Exception as e:
        check("request hợp lệ", False, str(e))
    if check_fallback:
        try:
            r = json.load(post_json(url, json.dumps(payload).encode(), {"X-Force-Fallback": "1"}))
            check("ca fallback: source == 'fallback' và có output", r.get("source") == "fallback" and str(r.get("output", "")).strip(),
                  f"nhận source={r.get('source')!r} (server cần ALLOW_FORCE_FALLBACK=1)")
        except Exception as e:
            check("ca fallback", False, str(e))
    try:
        post_json(url, b"{khong phai json")
        check("từ chối body hỏng bằng 4xx", False, "server trả 2xx")
    except urllib.error.HTTPError as e:
        check("từ chối body hỏng bằng 4xx", 400 <= e.code < 500, f"mã {e.code}")
    except Exception as e:
        check("từ chối body hỏng bằng 4xx", False, str(e))
    if is_ok():
        if transport_only or not require:
            print("TẤT CẢ ĐẠT (chỉ HTTP/JSON: KHÔNG chứng minh AI đang chạy)")
            print("RESULT: PASS transport-only (does NOT prove the AI works)")
        else:
            print("TẤT CẢ ĐẠT: hệ thống báo thành công (source=ai). Điều này chưa chứng minh đã gọi model thật nếu SYSTEM là hệ thống giả.")
            print("RESULT: PASS source=ai")
    else:
        print("CÓ LỖI, chưa nên demo")
        print("RESULT: FAIL")
    return 0 if is_ok() else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("base_url")
    ap.add_argument("--kind", choices=["image", "json"], default="image")
    ap.add_argument("--path", default="/predict")
    ap.add_argument("--image")
    ap.add_argument("--payload", default='{"input": "xin chào"}')
    ap.add_argument("--expect-key", action="append", default=None, help="khóa bắt buộc trong JSON trả về (lặp lại được)")
    ap.add_argument("--require", action="append", default=None, help='điều kiện giá trị key=value, mặc định source=ai (lặp lại được)')
    ap.add_argument("--check-fallback", action="store_true")
    ap.add_argument("--transport-only", action="store_true")
    ap.add_argument("--max-ms", type=float, default=3000)
    a = ap.parse_args()
    base, ok = a.base_url.rstrip("/"), True

    def check(name, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        print(("PASS" if cond else "FAIL"), name, detail)

    try:
        h = json.load(urllib.request.urlopen(base + "/health", timeout=90))  # gói free có thể đang ngủ: lần đầu chậm
        check("health", h.get("status") == "ok", f"{len(h.get('classes', []))} lớp" if "classes" in h else "")
    except Exception as e:
        check("health", False, str(e))
        return 1
    if a.kind == "json":
        req = [] if a.transport_only else (a.require or ["source=ai"])
        return json_checks(base + a.path, json.loads(a.payload), a.expect_key or ["output"], a.max_ms, check, lambda: ok,
                           req, a.check_fallback, a.transport_only)
    data, name = (open(a.image, "rb").read(), a.image) if a.image else sample_png()
    try:
        t = time.time()
        r = json.load(post_image(base + "/predict", data, name))
        ms = (time.time() - t) * 1000
        check("predict trả nhãn hợp lệ", r.get("label") in h["classes"], f"{r.get('label')} {r.get('confidence', 0):.2f}")
        check(f"độ trễ < {a.max_ms:.0f} ms", ms < a.max_ms, f"{ms:.0f} ms (lần đầu có thể chậm do khởi động nguội)")
    except Exception as e:
        check("predict", False, str(e))
    try:
        post_image(base + "/predict", b"khong phai anh", "bad.txt")
        check("từ chối file lỗi bằng 400", False, "server trả 200")
    except urllib.error.HTTPError as e:
        check("từ chối file lỗi bằng 400", e.code == 400, f"mã {e.code}")
    except Exception as e:
        check("từ chối file lỗi bằng 400", False, str(e))
    print("TẤT CẢ ĐẠT" if ok else "CÓ LỖI, chưa nên demo")
    print("RESULT: PASS" if ok else "RESULT: FAIL")  # dòng ASCII: đọc được cả trên terminal Windows cp1252
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
