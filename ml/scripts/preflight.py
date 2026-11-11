#!/usr/bin/env python3
"""Preflight trước ngày thi: một lệnh kiểm các điều kiện GO có thể tự động hóa, ghi preflight-report.md.

Chạy từ thư mục ml/ của dự án:
  python -X utf8 scripts/preflight.py                                   # kiểm môi trường + API local (không tốn tiền)
  python -X utf8 scripts/preflight.py --real                            # + MỘT request thật tới model (tốn một lượt gọi)
  python -X utf8 scripts/preflight.py --real --url https://x.onrender.com --app-dir ../app   # đủ điều kiện GO kỹ thuật

SYSTEM (module:function) lấy từ --system hoặc biến môi trường SYSTEM; mặc định examples.toy_system:run (hệ thống GIẢ).
Kết luận:
  GO KỸ THUẬT  = không có FAIL, và các mục bắt buộc (request thật, URL deploy, quét key trong app) đều PASS.
                 Vẫn còn checklist trên điện thoại trong profiles/mobile-ai.md (máy không tự kiểm được).
  CHƯA GO      = có FAIL hoặc còn mục bắt buộc chưa chạy (SKIP).
Mã thoát: 0 = GO kỹ thuật; 1 = có FAIL; 2 = không FAIL nhưng còn mục bắt buộc chưa chạy.
Không bao giờ in giá trị API key.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

for _st in (sys.stdout, sys.stderr):
    try:
        _st.reconfigure(errors="replace")
    except Exception:
        pass

ML = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML))
FAKE_SYSTEMS = {"examples.toy_system:run", "examples.broken_system:run"}
KEY_ENV = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY", "google": "GOOGLE_API_KEY"}
SECRET_PATTERNS = [
    ("Anthropic key", re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}")),
    ("OpenAI-style key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{20,}")),
    ("Google API key", re.compile(r"AIza[0-9A-Za-z_\-]{30,}")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("biến key gán giá trị", re.compile(r"(?i)\b[A-Z0-9_]*(?:API_KEY|SECRET|TOKEN)\s*[:=]\s*['\"][^'\"\s]{12,}['\"]")),
    ("EXPO_PUBLIC_* chứa key (lộ trong bundle)", re.compile(r"(?i)EXPO_PUBLIC_[A-Z0-9_]*(?:KEY|SECRET|TOKEN)\s*=\s*\S{8,}")),
]
SCAN_EXT = {".js", ".jsx", ".ts", ".tsx", ".json", ".env", ".mjs", ".cjs"}
SKIP_DIRS = {"node_modules", ".git", ".expo", "dist", "build", "android", "ios", "__pycache__", "web-build"}


class Report:
    def __init__(self):
        self.rows = []

    def add(self, name, status, detail="", required=False):
        self.rows.append((name, status, detail, required))
        print(f"[{status:<4}] {name}" + (f": {detail}" if detail else ""))

    def verdict(self):
        if any(s == "FAIL" for _, s, _, _ in self.rows):
            return 1, "CHƯA GO: có mục FAIL"
        missing = [n for n, s, _, r in self.rows if r and s != "PASS"]
        if missing:
            return 2, "CHƯA GO: còn mục bắt buộc chưa chạy hoặc chưa đạt: " + "; ".join(missing)
        return 0, "GO KỸ THUẬT (còn checklist trên điện thoại trong profiles/mobile-ai.md)"

    def write(self, path, args):
        code, msg = self.verdict()
        lines = [f"# Preflight {time.strftime('%Y-%m-%d %H:%M')}", "", f"**Kết luận: {msg}**", "",
                 f"SYSTEM: `{args.system}`" + (" (hệ thống GIẢ)" if args.system in FAKE_SYSTEMS else ""), "",
                 "| Mục | Kết quả | Chi tiết | Bắt buộc cho GO |", "|---|---|---|---|"]
        for n, s, d, r in self.rows:
            lines.append(f"| {n} | {s} | {d.replace('|', '/')} | {'có' if r else ''} |")
        lines += ["", "Mục không tự kiểm được (tự tick kèm bằng chứng): app mở trên điện thoại thật qua 4G gọi URL deploy; "
                  "luồng chính 3 lần liên tiếp gồm lần server nguội; tắt mạng; từ chối quyền camera/mic; giao thử một task agent trên host chính."]
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        return code, msg


def provider_of(fn):
    src = ""
    try:
        import inspect
        src = inspect.getsource(sys.modules[fn.__module__])
    except Exception:
        pass
    return [p for p in KEY_ENV if re.search(rf"\bimport {p}\b|\bfrom {p}\b", src)]


def check_env(rep, args):
    v = sys.version_info
    rep.add("Python >= 3.10", "PASS" if v >= (3, 10) else "FAIL", f"{v.major}.{v.minor}.{v.micro}")
    missing = []
    for mod in ("fastapi", "uvicorn", "pydantic", "yaml"):
        try:
            importlib.import_module(mod)
        except Exception:
            missing.append(mod)
    rep.add("Thư viện backend", "FAIL" if missing else "PASS",
            f"thiếu {missing}: pip install -r requirements-serve.txt pyyaml" if missing else "fastapi, uvicorn, pydantic, pyyaml")
    if os.environ.get("ALLOW_FORCE_FALLBACK") == "1":
        rep.add("ALLOW_FORCE_FALLBACK", "WARN", "đang bật: chỉ để kiểm thử, tắt trước khi demo")


def load_system(rep, spec):
    try:
        mod, fn = spec.split(":")
        f = getattr(importlib.import_module(mod), fn)
        rep.add("Import SYSTEM", "PASS", spec)
        return f
    except Exception as e:
        rep.add("Import SYSTEM", "FAIL", f"{spec}: {type(e).__name__}: {e}")
        return None


def check_keys(rep, f):
    provs = provider_of(f)
    for p in provs:
        try:
            importlib.import_module(p)
            rep.add(f"SDK {p}", "PASS")
        except Exception:
            rep.add(f"SDK {p}", "FAIL", f"pip install {p}")
        env = KEY_ENV[p]
        rep.add(f"Biến môi trường {env}", "PASS" if os.environ.get(env) else "FAIL",
                "có (không in giá trị)" if os.environ.get(env) else "chưa đặt")
    return provs


def check_local_api(rep, spec):
    os.environ["SYSTEM"] = spec
    try:
        from fastapi.testclient import TestClient
        sys.modules.pop("serve.app_llm", None)
        m = importlib.import_module("serve.app_llm")
        c = TestClient(m.app)
        h = c.get("/health")
        bad = c.post("/predict", content=b"{hong", headers={"Content-Type": "application/json"})
        ok = h.status_code == 200 and bad.status_code == 422
        rep.add("API local: /health và từ chối body hỏng", "PASS" if ok else "FAIL", f"health {h.status_code}, body hỏng {bad.status_code}")
    except Exception as e:
        rep.add("API local", "FAIL", f"{type(e).__name__}: {e}")


def check_real(rep, f, spec, args):
    if not args.real:
        rep.add("Request thật tới model", "SKIP", "thêm --real (tốn một lượt gọi)", required=True)
        return
    if spec in FAKE_SYSTEMS:
        rep.add("Request thật tới model", "FAIL", f"SYSTEM={spec} là hệ thống giả; đặt SYSTEM=module:function của bạn", required=True)
        return
    from mlkit.result import normalize
    import inspect
    t = time.time()
    try:
        params = inspect.signature(f).parameters
        kw = {"timeout": args.timeout} if "timeout" in params or any(p.kind is p.VAR_KEYWORD for p in params.values()) else {}
        n = normalize(f(args.prompt, **kw))
    except Exception as e:
        rep.add("Request thật tới model", "FAIL", f"{type(e).__name__}: {str(e)[:200]}", required=True)
        return
    ms = (time.time() - t) * 1000
    if n["ok"]:
        rep.add("Request thật tới model", "PASS", f"{ms:.0f} ms, {n['tokens']} token, trả lời: {n['output'][:80]!r}", required=True)
        rep.add("Độ trễ request thật", "PASS" if ms < args.timeout * 1000 * 0.8 else "WARN",
                f"{ms:.0f} ms so với timeout {args.timeout:.0f}s")
    else:
        rep.add("Request thật tới model", "FAIL", f"source={n['source']} error={n['error']}", required=True)


def is_local_url(url):
    return bool(re.search(r"//(localhost|127\.|0\.0\.0\.0|192\.168\.|10\.|172\.(1[6-9]|2\d|3[01])\.)", url))


def check_url(rep, args):
    if not args.url:
        rep.add("Smoke test trên URL deploy", "SKIP", "thêm --url https://...", required=True)
        return
    if is_local_url(args.url):
        rep.add("Smoke test trên URL deploy", "FAIL", "URL phải là địa chỉ deploy công khai, không phải localhost/LAN", required=True)
        return
    cmd = [sys.executable, str(ML / "scripts" / "smoke_test.py"), args.url, "--kind", "json",
           "--payload", json.dumps({"input": args.prompt}), "--max-ms", str(args.timeout * 1000)]  # JSON thoát ký tự: argv chỉ ASCII
    if args.check_fallback:
        cmd.append("--check-fallback")
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}, timeout=180)
    last = (r.stdout.strip().splitlines() or ["(không có output)"])[-1]
    ok = r.returncode == 0 and "RESULT: PASS source=ai" in r.stdout
    rep.add("Smoke test trên URL deploy", "PASS" if ok else "FAIL", last, required=True)


def check_app(rep, args):
    if not args.app_dir:
        rep.add("Quét key trong mã app mobile", "SKIP", "thêm --app-dir <thư mục app Expo>", required=True)
        return
    root = Path(args.app_dir)
    if not root.is_dir():
        rep.add("Quét key trong mã app mobile", "FAIL", f"không có thư mục {root}", required=True)
        return
    hits, n = [], 0
    for p in root.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts) or not p.is_file() or (p.suffix not in SCAN_EXT and not p.name.startswith(".env")):
            continue
        n += 1
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for label, rx in SECRET_PATTERNS:
            if rx.search(text):
                hits.append(f"{p.relative_to(root)} ({label})")
    rep.add("Quét key trong mã app mobile", "FAIL" if hits else "PASS",
            ("nghi lộ key: " + ", ".join(hits[:8])) if hits else f"{n} file, không thấy key", required=True)


def check_kit(rep):
    proj = ML.parent
    mf = proj / ".hackathon-kit" / "manifest.json"
    if not mf.exists():
        rep.add("Kit đã cài bằng installer", "WARN", "không thấy .hackathon-kit/manifest.json (chạy preflight trong ml/ của dự án đã cài?)")
    else:
        rep.add("Kit đã cài bằng installer", "PASS")
    pending = [str(p.relative_to(proj)) for p in proj.rglob("*.kit-new") if "node_modules" not in p.parts]
    rep.add("Không còn file .kit-new chưa xử lý", "WARN" if pending else "PASS", ", ".join(pending[:5]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--system", default=os.environ.get("SYSTEM", "examples.toy_system:run"))
    ap.add_argument("--real", action="store_true", help="gọi model thật một lần")
    ap.add_argument("--url", help="URL backend đã deploy")
    ap.add_argument("--check-fallback", action="store_true", help="kiểm thêm nhánh fallback trên URL (server cần ALLOW_FORCE_FALLBACK=1)")
    ap.add_argument("--app-dir", help="thư mục mã app Expo để quét key")
    ap.add_argument("--prompt", default="Trả lời một từ: thủ đô của Việt Nam?")
    ap.add_argument("--timeout", type=float, default=20.0)
    ap.add_argument("--report", default="preflight-report.md")
    args = ap.parse_args(argv)

    rep = Report()
    check_env(rep, args)
    f = load_system(rep, args.system)
    if args.system in FAKE_SYSTEMS:
        rep.add("SYSTEM là hệ thống thật", "WARN", "đang dùng hệ thống giả; kết quả source=ai không chứng minh gọi model")
    if f:
        check_keys(rep, f)
        check_local_api(rep, args.system)
        check_real(rep, f, args.system, args)
    check_url(rep, args)
    check_app(rep, args)
    check_kit(rep)
    code, msg = rep.write(args.report, args)
    print(f"\n{msg}\nBáo cáo: {Path(args.report).resolve()}")
    print("RESULT: GO-TECH" if code == 0 else "RESULT: FAIL" if code == 1 else "RESULT: INCOMPLETE")
    return code


if __name__ == "__main__":
    sys.exit(main())
