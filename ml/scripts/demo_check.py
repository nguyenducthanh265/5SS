#!/usr/bin/env python3
"""Diễn lại đúng việc giám khảo làm ở tiêu chí demo: ĐÓNG HẲN app rồi MỞ LẠI trên điện thoại thật, chạy luồng AI trực tiếp.

  python -X utf8 scripts/demo_check.py --package com.team.app --scheme myapp [--apk app.apk] [--repeat 3]

Cần: adb (Android platform-tools) trong PATH; điện thoại bật USB debugging, cắm cáp (mọi máy đang cắm đều được kiểm);
app là bản cài độc lập (APK), KHÔNG phải Expo Go; app có deep link <scheme>://selftest chạy luồng AI THẬT trên dữ liệu mẫu
đóng gói sẵn trong app và in đúng một dòng console (React Native ghi console vào logcat; script tìm dòng ở mọi tag):
    HACKCHECK SELFTEST PASS           chỉ khi aiClient trả kind === "ai"
    HACKCHECK SELFTEST FAIL <lý do>   mọi trường hợp khác (fallback, busy, timeout, network, http, lỗi parse)
Mỗi vòng: force-stop -> xóa logcat -> mở từ launcher -> kiểm app còn sống -> gọi selftest -> chờ dòng kết quả -> chụp màn hình.
Dòng cuối luôn là `RESULT: PASS ...` hoặc `RESULT: FAIL ...` (ASCII). Mã thoát 0 = PASS, 1 = FAIL, 2 = sai cách gọi.
PASS chứng minh: app tự khởi động lại được trên máy và luồng AI trả kết quả AI thật lúc chạy. Không chứng minh UI đẹp hay
kết quả đúng: vẫn tự bấm thử luồng chính bằng tay.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time

for _st in (sys.stdout, sys.stderr):  # terminal Windows cp1252: không sập vì tiếng Việt
    try:
        _st.reconfigure(errors="replace")
    except Exception:
        pass

EXPO_GO = "host.exp.exponent"
LINE = re.compile(r"HACKCHECK SELFTEST (PASS|FAIL)(.*)")


def real_runner(adb="adb", timeout=60):
    def run(args, binary=False):
        try:
            p = subprocess.run([adb, *args], capture_output=True, timeout=timeout)
        except FileNotFoundError:
            return 127, b"" if binary else "adb not found"
        except subprocess.TimeoutExpired:
            return 124, b"" if binary else "adb timeout"
        out = p.stdout if binary else (p.stdout + p.stderr).decode("utf-8", errors="replace")
        return p.returncode, out
    return run


def list_devices(run):
    """-> (máy sẵn sàng, máy chưa cho phép USB debugging)."""
    code, out = run(["devices"])
    if code != 0:
        return None, []
    ready, blocked = [], []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2:
            (ready if parts[1] == "device" else blocked).append(parts[0])
    return ready, blocked


def app_running(run, serial, pkg):
    code, out = run(["-s", serial, "shell", "pidof", pkg])
    if code == 0 and out.strip():
        return True
    code, out = run(["-s", serial, "shell", "ps", "-A"])  # máy cũ không có pidof
    return code == 0 and any(l.split()[-1:] == [pkg] for l in out.splitlines())


def one_round(run, serial, pkg, scheme, timeout, boot_wait, sleep, clock, shot_path):
    """-> (ok, mô tả, giây). Mỗi bước là việc giám khảo làm hoặc thấy được."""
    run(["-s", serial, "shell", "am", "force-stop", pkg])
    run(["-s", serial, "logcat", "-c"])
    run(["-s", serial, "shell", "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"])
    sleep(boot_wait)
    if not app_running(run, serial, pkg):
        _, crash = run(["-s", serial, "logcat", "-d", "-b", "crash"])
        tail = " | ".join(crash.strip().splitlines()[-3:]) if isinstance(crash, str) else ""
        return False, f"app không chạy sau khi mở lại (crash: {tail or 'không có log'})", 0.0
    run(["-s", serial, "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", f"{scheme}://selftest", pkg])
    t0 = clock()
    result = None
    while clock() - t0 <= timeout:
        _, log = run(["-s", serial, "logcat", "-d"])  # không lọc theo tag: tag console có thể khác giữa bản debug/release
        found = LINE.findall(log or "")
        if found:
            result = found[-1]
            break
        sleep(1)
    elapsed = clock() - t0
    code, png = run(["-s", serial, "exec-out", "screencap", "-p"], binary=True)
    if code == 0 and png:
        with open(shot_path, "wb") as f:
            f.write(png)
    if result is None:
        return False, f"không thấy dòng HACKCHECK sau {timeout:.0f}s (app có deep link {scheme}://selftest chưa?)", elapsed
    status, detail = result
    return status == "PASS", (f"AI chạy trực tiếp" if status == "PASS" else f"selftest báo FAIL{detail}"), elapsed


def check(run, pkg, scheme, apk=None, repeat=1, timeout=40.0, boot_wait=5.0, serial=None, out_dir=".",
          sleep=time.sleep, clock=time.monotonic):
    """-> mã thoát. In báo cáo từng máy, từng vòng; dòng cuối RESULT."""
    if pkg == EXPO_GO:
        print("LỖI: đây là Expo Go. Giám khảo đóng hẳn rồi mở lại app: Expo Go phải nạp lại từ máy tính, dễ hỏng.")
        print("Build APK cài thẳng (eas build --profile preview) rồi kiểm lại bằng package của app.")
        print("RESULT: FAIL expo-go")
        return 1
    ready, blocked = list_devices(run)
    if ready is None:
        print("LỖI: không chạy được adb. Cài Android platform-tools và thêm vào PATH.")
        print("RESULT: FAIL no-adb")
        return 1
    for b in blocked:
        print(f"Máy {b}: chưa cho phép USB debugging (bấm 'Cho phép' trên điện thoại).")
    if serial:
        ready = [s for s in ready if s == serial]
    if not ready:
        print("LỖI: không có điện thoại sẵn sàng. Cắm cáp, bật USB debugging, chạy 'adb devices'.")
        print("RESULT: FAIL no-device")
        return 1
    fails, worst = 0, 0.0
    for s in ready:
        _, model = run(["-s", s, "shell", "getprop", "ro.product.model"])
        print(f"=== {(model or '').strip() or 'máy'} ({s}) ===")
        if apk:
            code, out = run(["-s", s, "install", "-r", apk])
            if code != 0:
                print(f"  FAIL cài APK: {out.strip()[-200:]}")
                fails += 1
                continue
            print(f"  đã cài {os.path.basename(apk)}")
        for i in range(1, repeat + 1):
            shot = os.path.join(out_dir, f"demo-check-{re.sub(r'[^A-Za-z0-9]', '_', s)}-{i}.png")
            ok, msg, secs = one_round(run, s, pkg, scheme, timeout, boot_wait, sleep, clock, shot)
            worst = max(worst, secs)
            print(f"  vòng {i}: {'PASS' if ok else 'FAIL'} - {msg} ({secs:.1f}s; ảnh: {shot})")
            fails += not ok
    total = len(ready) * repeat
    if fails:
        print(f"RESULT: FAIL {fails}/{total} rounds failed")
        return 1
    print(f"RESULT: PASS devices={len(ready)} rounds={total} max_ai_s={worst:.1f}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--package", required=True, help="applicationId của app, ví dụ com.team.app (không phải Expo Go)")
    ap.add_argument("--scheme", required=True, help="scheme trong app.json, ví dụ myapp")
    ap.add_argument("--apk", help="cài APK này trước khi kiểm")
    ap.add_argument("--repeat", type=int, default=1, help="số vòng đóng-mở-chạy AI mỗi máy (trước khi nộp: 3)")
    ap.add_argument("--timeout", type=float, default=40.0, help="giây chờ kết quả AI mỗi vòng")
    ap.add_argument("--boot-wait", type=float, default=5.0, help="giây chờ app khởi động")
    ap.add_argument("--serial", help="chỉ kiểm máy này")
    ap.add_argument("--adb", default=os.environ.get("ADB", "adb"))
    ap.add_argument("--out-dir", default=".")
    a = ap.parse_args(argv)
    if a.repeat < 1:
        ap.error("--repeat phải >= 1")
    os.makedirs(a.out_dir, exist_ok=True)
    return check(real_runner(a.adb), a.package, a.scheme, a.apk, a.repeat, a.timeout, a.boot_wait, a.serial, a.out_dir)


if __name__ == "__main__":
    sys.exit(main())
