#!/usr/bin/env python3
"""Cross-stack end-to-end smoke test for Hanoi Waste Sorter (App contract -> FastAPI -> Rule Engine).

Usage:
  python -X utf8 scripts/e2e_smoke.py --local
  python -X utf8 scripts/e2e_smoke.py --url https://hanoi-waste-ai.onrender.com
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

for _st in (sys.stdout, sys.stderr):
    try:
        _st.reconfigure(errors="replace")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parents[1]
ML_DIR = REPO_ROOT / "ml"
APP_DIR = REPO_ROOT / "app"
DEFAULT_IMAGE_PATH = APP_DIR / "assets" / "sample-waste.jpg"
MAX_CHARS_LIMIT = 1_500_000

DEFAULT_WASTE_PROMPT = (
    "Nhận diện các món rác thải trong ảnh để phân loại theo Quyết định 87/2025/QĐ-UBND Hà Nội. "
    "Trả về đúng JSON theo schema chuẩn."
)

ADAPTER_SOURCE = '''"""Temporary deterministic Vision test adapter exercising real mypkg.waste_rules."""
from __future__ import annotations

import base64
import json
from typing import Any

from mypkg.waste_rules import evaluate_items


def run(text: str, timeout: float = 20.0) -> dict[str, Any]:
    """Validate app/aiClient.ts payload format and run real Hanoi rule engine."""
    del timeout
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("Expected JSON object payload")
    prompt = payload.get("prompt")
    image = payload.get("image")
    want_json = payload.get("json")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("Missing non-empty prompt")
    if not isinstance(image, str) or not image.startswith("data:image/jpeg;base64,"):
        raise ValueError("Expected data:image/jpeg;base64,... image payload")
    if want_json is not True:
        raise ValueError("Expected json=true")

    raw_bytes = base64.b64decode(image.split(",", 1)[1], validate=True)
    if not raw_bytes.startswith(b"\\xff\\xd8"):
        raise ValueError("Decoded image is not valid JPEG")

    # Deterministic extracted Vision items spanning recyclable + hazardous dropoff rules
    raw_items = [
        {
            "name_vi": "Vỏ hộp sữa giấy",
            "item_key": "milk_carton",
            "material": "Giấy tráng nhôm/nhựa",
            "dirty_oily": False,
            "confidence": 0.96,
        },
        {
            "name_vi": "Pin tiểu AA",
            "item_key": "battery",
            "material": "Kim loại/Hóa chất",
            "dirty_oily": False,
            "confidence": 0.94,
        },
    ]
    evaluated = evaluate_items(raw_items)
    return {
        "output": json.dumps(evaluated, ensure_ascii=False),
        "tokens": 42,
        "source": "ai",
    }
'''


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http_json(
    url: str,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict[str, Any]]:
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else {}
        except ValueError:
            parsed = {"raw": raw}
        return exc.code, parsed


def _wait_for_health(base_url: str, proc: subprocess.Popen[str] | None, timeout_s: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_s
    last_err: str = "no response"
    while time.monotonic() < deadline:
        if proc is not None and proc.poll() is not None:
            out = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(f"uvicorn exited early (code={proc.returncode}): {out[-1000:]}")
        try:
            status, data = _http_json(f"{base_url}/health", timeout=2.0)
            if status == 200 and data.get("status") == "ok":
                return data
            last_err = f"status={status} body={data}"
        except Exception as exc:
            last_err = str(exc)
        time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for {base_url}/health ({last_err})")


def _build_image_predict_payload(image_path: Path) -> tuple[dict[str, str], int]:
    raw_bytes = image_path.read_bytes()
    if not raw_bytes.startswith(b"\xff\xd8"):
        raise ValueError(f"{image_path} is not a valid JPEG image")
    b64 = base64.b64encode(raw_bytes).decode("ascii")
    inner_input = json.dumps(
        {
            "prompt": DEFAULT_WASTE_PROMPT,
            "image": f"data:image/jpeg;base64,{b64}",
            "json": True,
        },
        ensure_ascii=False,
    )
    if len(inner_input) > MAX_CHARS_LIMIT:
        raise ValueError(f"Encoded payload length {len(inner_input)} exceeds MAX_CHARS={MAX_CHARS_LIMIT}")
    return {"input": inner_input}, len(raw_bytes)


def _strip_json_fence(text: str) -> str:
    trimmed = text.strip()
    if trimmed.startswith("```"):
        lines = trimmed.splitlines()
        if len(lines) >= 2 and lines[-1].strip() == "```":
            return "\n".join(lines[1:-1]).strip()
    return trimmed


def _validate_waste_schema(output_text: str) -> dict[str, Any]:
    """Validate backend JSON against app/src/types/waste.ts (WasteResult) & ml/mypkg/waste_rules.py."""
    data = json.loads(_strip_json_fence(output_text))
    if not isinstance(data, dict):
        raise AssertionError("Parsed output is not a JSON object")

    required_top = {
        "items": list,
        "mixed_bag": bool,
        "mixed_bag_reason_vi": str,
        "has_hazardous": bool,
        "dropoff_summary": list,
        "collection_window_vi": str,
        "speech_vi": str,
    }
    for key, expected_type in required_top.items():
        if key not in data:
            raise AssertionError(f"Missing top-level field: {key}")
        if not isinstance(data[key], expected_type):
            raise AssertionError(f"Field {key} expected {expected_type.__name__}, got {type(data[key]).__name__}")

    if not data["items"]:
        raise AssertionError("items list must be non-empty")
    if not data["collection_window_vi"].strip():
        raise AssertionError("collection_window_vi must be non-empty")
    if not data["speech_vi"].strip():
        raise AssertionError("speech_vi must be non-empty")
    if data["mixed_bag"] and not data["mixed_bag_reason_vi"].strip():
        raise AssertionError("mixed_bag_reason_vi must be non-empty when mixed_bag=True")

    required_item = {
        "name_vi": str,
        "item_key": str,
        "material": str,
        "dirty_oily": bool,
        "group_id": str,
        "group_name_vi": str,
        "rinse_required": bool,
        "sell_for_recycling": bool,
        "dropoff_points": list,
        "note_vi": str,
    }
    for idx, item in enumerate(data["items"]):
        if not isinstance(item, dict):
            raise AssertionError(f"items[{idx}] is not an object")
        for key, expected_type in required_item.items():
            if key not in item:
                raise AssertionError(f"items[{idx}] missing field: {key}")
            if not isinstance(item[key], expected_type):
                raise AssertionError(
                    f"items[{idx}].{key} expected {expected_type.__name__}, got {type(item[key]).__name__}"
                )
        for non_empty in ("name_vi", "item_key", "group_id", "group_name_vi"):
            if not item[non_empty].strip():
                raise AssertionError(f"items[{idx}].{non_empty} must be non-empty")

    for idx, pt in enumerate(data["dropoff_summary"]):
        if isinstance(pt, str):
            if not pt.strip():
                raise AssertionError(f"dropoff_summary[{idx}] string is empty")
        elif isinstance(pt, dict):
            if not isinstance(pt.get("name"), str) or not pt["name"].strip():
                raise AssertionError(f"dropoff_summary[{idx}].name must be a non-empty string")
        else:
            raise AssertionError(f"dropoff_summary[{idx}] has invalid type {type(pt).__name__}")

    return data


def _run_secret_scan(app_dir: Path) -> tuple[bool, str]:
    """Reuse ml/scripts/preflight.py secret scanner on app/ without duplicating patterns."""
    scripts_dir = ML_DIR / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    import preflight  # noqa: E402

    rep = preflight.Report()
    preflight.check_app(rep, argparse.Namespace(app_dir=str(app_dir)))
    _, status, detail, _ = rep.rows[-1]
    return status == "PASS", detail


def _terminate_proc(proc: subprocess.Popen[str] | None) -> str:
    if proc is None:
        return ""
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    out = ""
    if proc.stdout is not None:
        try:
            out = proc.stdout.read()
        finally:
            proc.stdout.close()
    return out


def run_smoke(base_url: str | None, image_path: Path, device_id: str, timeout_s: float) -> int:
    checks: list[tuple[str, bool, str]] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, bool(ok), detail))
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))

    is_local = base_url is None
    proc: subprocess.Popen[str] | None = None
    tmp_ctx: tempfile.TemporaryDirectory[str] | None = None

    try:
        if is_local:
            tmp_ctx = tempfile.TemporaryDirectory(prefix="hanoi_waste_e2e_")
            tmp_dir = Path(tmp_ctx.name)
            (tmp_dir / "e2e_vision_adapter.py").write_text(ADAPTER_SOURCE, encoding="utf-8")

            port = _find_free_port()
            target_url = f"http://127.0.0.1:{port}"
            env = {
                **os.environ,
                "SYSTEM": "e2e_vision_adapter:run",
                "MAX_CHARS": str(MAX_CHARS_LIMIT),
                "TIMEOUT_S": "20",
                "MAX_INFLIGHT": "8",
                "PYTHONUTF8": "1",
                "PYTHONIOENCODING": "utf-8",
                "PYTHONPATH": os.pathsep.join(
                    p for p in (str(tmp_dir), str(ML_DIR), os.environ.get("PYTHONPATH", "")) if p
                ),
            }
            proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "serve.app_llm:app", "--host", "127.0.0.1", "--port", str(port)],
                cwd=str(ML_DIR),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            health = _wait_for_health(target_url, proc, timeout_s=min(timeout_s, 20.0))
        else:
            target_url = base_url.rstrip("/")
            health = _wait_for_health(target_url, None, timeout_s=max(timeout_s, 60.0))

        record(
            "GET /health",
            health.get("status") == "ok",
            f"system={health.get('system')} max_inflight={health.get('max_inflight')}",
        )

        # Baseline /stats before /predict
        stats_status_0, stats_before = _http_json(f"{target_url}/stats", timeout=timeout_s)
        if stats_status_0 != 200:
            raise RuntimeError(f"GET /stats failed with status={stats_status_0}")
        before_ai = int(stats_before.get("ai_requests", 0))

        # Build sample-waste.jpg base64 payload matching app/aiClient.ts
        predict_body, img_bytes = _build_image_predict_payload(image_path)
        input_chars = len(predict_body["input"])
        record(
            "Image payload size within MAX_CHARS",
            input_chars <= MAX_CHARS_LIMIT,
            f"image={image_path.name} ({img_bytes} bytes), input={input_chars} chars <= {MAX_CHARS_LIMIT}",
        )

        # POST /predict with X-Device-Id
        t0 = time.monotonic()
        pred_status, pred_data = _http_json(
            f"{target_url}/predict",
            method="POST",
            body=json.dumps(predict_body).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Device-Id": device_id},
            timeout=timeout_s,
        )
        elapsed_ms = round((time.monotonic() - t0) * 1000)
        pred_ok = pred_status == 200 and pred_data.get("source") == "ai" and not pred_data.get("error")
        record(
            "POST /predict (sample-waste.jpg base64 + X-Device-Id)",
            pred_ok,
            f"status={pred_status} source={pred_data.get('source')!r} latency_ms={elapsed_ms}",
        )
        if not pred_ok:
            raise RuntimeError(f"/predict failed: {pred_data}")

        # Validate schema against app/src/types/waste.ts & ml/mypkg/waste_rules.py
        parsed_waste = _validate_waste_schema(str(pred_data.get("output", "")))
        record(
            "WasteResult schema alignment (app/src/types/waste.ts <-> waste_rules.py)",
            True,
            f"items={len(parsed_waste['items'])} mixed_bag={parsed_waste['mixed_bag']} "
            f"has_hazardous={parsed_waste['has_hazardous']} dropoff={len(parsed_waste['dropoff_summary'])}",
        )

        # Verify /stats telemetry
        stats_status_1, stats_after = _http_json(f"{target_url}/stats", timeout=timeout_s)
        devices_total = int(stats_after.get("devices_total", 0))
        devices_ai = int(stats_after.get("devices_ai", 0))
        ai_requests = int(stats_after.get("ai_requests", 0))
        stats_ok = (
            stats_status_1 == 200
            and devices_total >= 1
            and devices_ai >= 1
            and ai_requests >= max(1, before_ai + 1)
        )
        record(
            "GET /stats telemetry",
            stats_ok,
            f"devices_total={devices_total} devices_ai={devices_ai} ai_requests={ai_requests}",
        )

        # Verify 422 validation on malformed JSON and empty input
        bad_json_status, _ = _http_json(
            f"{target_url}/predict",
            method="POST",
            body=b"{not-json",
            headers={"Content-Type": "application/json"},
            timeout=timeout_s,
        )
        empty_input_status, _ = _http_json(
            f"{target_url}/predict",
            method="POST",
            body=json.dumps({"input": ""}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            timeout=timeout_s,
        )
        record(
            "422 validation on malformed/empty payloads",
            bad_json_status == 422 and empty_input_status == 422,
            f"malformed={bad_json_status}, empty_input={empty_input_status}",
        )

        # Secret-leak scan on app/
        scan_ok, scan_detail = _run_secret_scan(APP_DIR)
        record("Secret-leak scan (app/)", scan_ok, scan_detail)
    finally:
        server_logs = _terminate_proc(proc)
        if tmp_ctx is not None:
            tmp_ctx.cleanup()

    if is_local and server_logs:
        expected_hash = hashlib.sha256(device_id.encode("utf-8")).hexdigest()[:12]
        hash_logged = f"USAGE source=ai device={expected_hash}" in server_logs
        record("X-Device-Id SHA-256[:12] log verification", hash_logged, f"device_hash={expected_hash}")

    all_ok = all(ok for _, ok, _ in checks)
    print(f"RESULT: {'PASS' if all_ok else 'FAIL'} ({sum(1 for _, ok, _ in checks if ok)}/{len(checks)} checks)")
    return 0 if all_ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--local", action="store_true", help="Launch local uvicorn with deterministic Vision adapter (default)")
    mode.add_argument("--url", help="Target deployed backend URL (e.g. https://hanoi-waste-ai.onrender.com)")
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE_PATH, help="JPEG image path to send")
    parser.add_argument("--device-id", default="e2e-smoke-device-001", help="X-Device-Id header value")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP request timeout in seconds")
    args = parser.parse_args(argv)

    return run_smoke(
        base_url=args.url,
        image_path=args.image,
        device_id=args.device_id,
        timeout_s=args.timeout,
    )


if __name__ == "__main__":
    sys.exit(main())
