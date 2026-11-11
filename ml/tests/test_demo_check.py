"""demo_check.py với adb giả: kiểm đúng những gì giám khảo làm (đóng hẳn, mở lại, AI chạy thật) và mọi đường FAIL."""
from scripts import demo_check as D


class FakeAdb:
    def __init__(self, devices="SER1\tdevice", running=True, lines=("HACKCHECK SELFTEST PASS",), appear_after=0, install_ok=True):
        self.devices, self.running, self.lines, self.appear_after, self.install_ok = devices, running, list(lines), appear_after, install_ok
        self.calls, self.polls, self.now = [], 0, 0.0

    def run(self, args, binary=False):
        self.calls.append(args)
        a = " ".join(args)
        if args == ["devices"]:
            return 0, "List of devices attached\n" + self.devices + "\n"
        if "getprop" in a:
            return 0, "Pixel 7\n"
        if "pidof" in a:
            return (0, "1234\n") if self.running else (1, "")
        if a.endswith("ps -A"):
            return 0, "USER PID NAME\n"
        if a.endswith("logcat -d"):
            self.polls += 1
            if self.polls > self.appear_after and self.lines:
                return 0, "\n".join(f"11-14 10:00:00 I ReactNativeJS: {l}" for l in self.lines)
            return 0, "11-14 I ReactNativeJS: app started\n"
        if "-b crash" in a:
            return 0, "FATAL EXCEPTION: main\njava.lang.RuntimeException: boom\n"
        if "screencap" in a:
            return 0, b"PNG"
        if args[2:3] == ["install"]:
            return (0, "Success") if self.install_ok else (1, "INSTALL_FAILED_VERSION_DOWNGRADE")
        return 0, ""

    def sleep(self, s):
        self.now += s

    def clock(self):
        return self.now


def go(fake, tmp_path, capsys, **kw):
    code = D.check(fake.run, kw.pop("pkg", "com.team.app"), "myapp", out_dir=str(tmp_path), sleep=fake.sleep, clock=fake.clock, **kw)
    return code, capsys.readouterr().out


def test_pass_force_stops_and_reopens_every_round(tmp_path, capsys):
    f = FakeAdb()
    code, out = go(f, tmp_path, capsys, repeat=3)
    assert code == 0 and out.strip().splitlines()[-1].startswith("RESULT: PASS devices=1 rounds=3")
    flat = [" ".join(c) for c in f.calls]
    assert sum("force-stop com.team.app" in c for c in flat) == 3
    assert sum("monkey -p com.team.app" in c for c in flat) == 3
    assert sum("myapp://selftest" in c for c in flat) == 3
    assert all((tmp_path / f"demo-check-SER1-{i}.png").read_bytes() == b"PNG" for i in (1, 2, 3))
    # force-stop phải đứng trước lần mở lại và trước selftest
    first = [i for i, c in enumerate(flat) if "force-stop" in c][0]
    assert first < [i for i, c in enumerate(flat) if "monkey" in c][0] < [i for i, c in enumerate(flat) if "selftest" in c][0]


def test_fail_line_from_app_fails(tmp_path, capsys):
    code, out = go(FakeAdb(lines=("HACKCHECK SELFTEST FAIL fallback: timeout",)), tmp_path, capsys)
    assert code == 1 and "selftest báo FAIL fallback: timeout" in out and "RESULT: FAIL 1/1" in out


def test_last_line_wins(tmp_path, capsys):
    code, _ = go(FakeAdb(lines=("HACKCHECK SELFTEST PASS", "HACKCHECK SELFTEST FAIL network")), tmp_path, capsys)
    assert code == 1


def test_no_result_line_times_out(tmp_path, capsys):
    code, out = go(FakeAdb(lines=()), tmp_path, capsys, timeout=5)
    assert code == 1 and "không thấy dòng HACKCHECK" in out


def test_slow_ai_within_timeout_passes_and_reports_time(tmp_path, capsys):
    code, out = go(FakeAdb(appear_after=3), tmp_path, capsys, timeout=10)
    assert code == 0 and "max_ai_s=3.0" in out


def test_app_not_running_after_reopen_reports_crash(tmp_path, capsys):
    code, out = go(FakeAdb(running=False), tmp_path, capsys)
    assert code == 1 and "app không chạy sau khi mở lại" in out and "boom" in out


def test_expo_go_is_refused_before_touching_device(tmp_path, capsys):
    f = FakeAdb()
    code, out = go(f, tmp_path, capsys, pkg="host.exp.exponent")
    assert code == 1 and "RESULT: FAIL expo-go" in out and f.calls == []


def test_no_device_and_unauthorized(tmp_path, capsys):
    code, out = go(FakeAdb(devices="SER9\tunauthorized"), tmp_path, capsys)
    assert code == 1 and "SER9" in out and "RESULT: FAIL no-device" in out


def test_every_connected_phone_is_checked(tmp_path, capsys):
    code, out = go(FakeAdb(devices="A1\tdevice\nB2\tdevice"), tmp_path, capsys, repeat=2)
    assert code == 0 and "devices=2 rounds=4" in out


def test_install_failure_fails(tmp_path, capsys):
    code, out = go(FakeAdb(install_ok=False), tmp_path, capsys, apk="app.apk")
    assert code == 1 and "INSTALL_FAILED" in out


def test_missing_adb_binary(tmp_path, capsys):
    code = D.check(D.real_runner(adb=str(tmp_path / "khong-co-adb")), "com.team.app", "myapp", out_dir=str(tmp_path))
    assert code == 1 and "RESULT: FAIL no-adb" in capsys.readouterr().out
