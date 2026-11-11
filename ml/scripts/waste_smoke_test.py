#!/usr/bin/env python3
"""End-to-end smoke test for Hanoi Waste Sorter API (serve/app_llm.py + mypkg/waste_ai.py).

Usage:
  python -X utf8 scripts/waste_smoke_test.py --local
  python -X utf8 scripts/waste_smoke_test.py --url https://your-service.onrender.com [--check-fallback]
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except Exception:
        pass

ML_ROOT = Path(__file__).resolve().parents[1]

ADAPTER_CODE = '''"""Deterministic mock OpenAI transport adapter for local waste_smoke_test."""
from __future__ import annotations

import json
import httpx
import openai

from mypkg import waste_ai


def _select_vision_payload(prompt_text: str) -> str:
    lower = prompt_text.lower()
    if "mixed" in lower or "lẫn" in lower:
        data = {
            "items": [
                {
                    "name_vi": "Thức ăn thừa",
                    "item_key": "food_waste",
                    "material": "Hữu cơ",
                    "dirty_oily": True,
                    "confidence": 0.91,
                },
                {
                    "name_vi": "Pin tiểu",
                    "item_key": "battery",
                    "material": "Kim loại",
                    "dirty_oily": False,
                    "confidence": 0.95,
                },
            ]
        }
        return json.dumps(data, ensure_ascii=False)
    if "oily" in lower or "dầu mỡ" in lower:
        data = {
            "items": [
                {
                    "name_vi": "Túi nilon dính dầu mỡ",
                    "item_key": "clean_plastic_bag",
                    "material": "Nhựa",
                    "dirty_oily": "true",
                    "confidence": "0.89",
                }
            ]
        }
        return "```json\\n" + json.dumps(data, ensure_ascii=False) + "\\n```"
    if "battery" in lower or "pin" in lower:
        data = {
            "items": [
                {
                    "name_vi": "Pin tiểu AA",
                    "item_key": "battery",
                    "material": "Kim loại/Hóa chất",
                    "dirty_oily": False,
                    "confidence": 0.97,
                }
            ]
        }
        return json.dumps(data, ensure_ascii=False)
    data = {
        "items": [
            {
                "name_vi": "Vỏ hộp sữa giấy",
                "item_key": "milk_carton",
                "material": "Giấy tráng nhôm/nhựa",
                "dirty_oily": False,
                "confidence": 0.96,
            }
        ]
    }
    return json.dumps(data, ensure_ascii=False)


def _make_mock_client() -> openai.OpenAI:
    def handler(req: httpx.Request) -> httpx.Response:
        req_body = json.loads(req.content.decode("utf-8"))
        prompt_text = ""
        for msg in req_body.get("input", []):
            for part in msg.get("content", []):
                if part.get("type") == "input_text":
                    prompt_text += " " + str(part.get("text", ""))
        output_text = _select_vision_payload(prompt_text)
        body = {
            "id": "resp_smoke_local",
            "object": "response",
            "created_at": 0,
            "status": "completed",
            "model": "vision-smoke-mock",
            "output": [
                {
                    "type": "message",
                    "id": "msg_smoke_1",
                    "status": "completed",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": output_text, "annotations": []}],
                }
            ],
            "incomplete_details": None,
            "usage": {"input_tokens": 12, "output_tokens": 18, "total_tokens": 30},
            "parallel_tool_calls": True,
            "tool_choice": "auto",
            "tools": [],
        }
        return httpx.Response(200, json=body)

    return openai.OpenAI(
        api_key="smoke-test-key",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        max_retries=0,
    )


def run(text: str, timeout: float = 20.0) -> dict:
    client = _make_mock_client()
    return waste_ai.run(text, model="vision-smoke-mock", timeout=timeout, client=client)
'''


def _sample_jpeg_data_url() -> str:
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (34, 139, 34)).save(buf, format="JPEG", quality=80)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{b64}"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http_json(
    url: str,
    *,
    method: str = "GET",
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict[str, Any]]:
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = {"raw": raw}
        return exc.code, payload


def _validate_waste_result(data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return [f"WasteResult must be a JSON object, got {type(data).__name__}"]

    required_top_types: dict[str, type] = {
        "items": list,
        "mixed_bag": bool,
        "mixed_bag_reason_vi": str,
        "has_hazardous": bool,
        "dropoff_summary": list,
        "collection_window_vi": str,
        "speech_vi": str,
    }
    for key, expected_type in required_top_types.items():
        if key not in data:
            errors.append(f"missing top-level key {key!r}")
        elif not isinstance(data[key], expected_type):
            errors.append(f"top-level {key!r} expected {expected_type.__name__}, got {type(data[key]).__name__}")

    if isinstance(data.get("speech_vi"), str) and not data["speech_vi"].strip():
        errors.append("speech_vi must be non-empty")

    required_item_types: dict[str, type] = {
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
    for idx, item in enumerate(data.get("items", []) if isinstance(data.get("items"), list) else []):
        if not isinstance(item, dict):
            errors.append(f"items[{idx}] must be an object")
            continue
        for key, expected_type in required_item_types.items():
            if key not in item:
                errors.append(f"items[{idx}] missing key {key!r}")
            elif not isinstance(item[key], expected_type):
                errors.append(
                    f"items[{idx}].{key} expected {expected_type.__name__}, got {type(item[key]).__name__}"
                )
        for non_empty_key in ("name_vi", "group_id", "group_name_vi"):
            val = item.get(non_empty_key)
            if isinstance(val, str) and not val.strip():
                errors.append(f"items[{idx}].{non_empty_key} must be non-empty")
    return errors


def _wait_for_health(base_url: str, timeout_s: float = 15.0) -> tuple[int, dict[str, Any]]:
    deadline = time.time() + timeout_s
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            status, payload = _http_json(f"{base_url}/health", timeout=2.0)
            if status == 200:
                return status, payload
        except Exception as exc:
            last_err = exc
        time.sleep(0.2)
    raise RuntimeError(f"Server did not become healthy within {timeout_s}s: {last_err}")


def _run_checks(base_url: str, *, local_mode: bool, check_fallback: bool) -> int:
    passed = True

    def check(label: str, cond: bool, detail: str = "") -> None:
        nonlocal passed
        passed &= bool(cond)
        print(f"{'PASS' if cond else 'FAIL'} {label}" + (f" ({detail})" if detail else ""))

    # 1. GET /health
    status, health = _http_json(f"{base_url}/health")
    check("GET /health returns 200 ok", status == 200 and health.get("status") == "ok", f"status={status} body={health}")

    # Baseline /stats
    stats_status, stats_before = _http_json(f"{base_url}/stats")
    check("GET /stats baseline returns 200", stats_status == 200 and "ai_requests" in stats_before, str(stats_before))

    # 2. POST /predict invalid bodies -> 422
    bad_status_json, _ = _http_json(
        f"{base_url}/predict",
        method="POST",
        body=b"{not-valid-json",
        headers={"Content-Type": "application/json"},
    )
    check("POST /predict malformed JSON returns 422", bad_status_json == 422, f"status={bad_status_json}")

    bad_status_empty, _ = _http_json(
        f"{base_url}/predict",
        method="POST",
        body=json.dumps({"input": ""}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    check("POST /predict empty input returns 422", bad_status_empty == 422, f"status={bad_status_empty}")

    # 3. POST /predict valid image+prompt payloads
    img_url = _sample_jpeg_data_url()
    device_ai = f"smoke-dev-ai-{uuid.uuid4().hex[:8]}"
    device_fb = f"smoke-dev-fb-{uuid.uuid4().hex[:8]}"

    if local_mode:
        scenarios = [
            (
                "milk_carton",
                "Nhận diện milk carton / vỏ hộp sữa giấy trong ảnh.",
                lambda wr: (
                    len(wr["items"]) == 1
                    and wr["items"][0]["item_key"] == "milk_carton"
                    and wr["items"][0]["group_id"] == "group_1_recyclable"
                    and wr["items"][0]["rinse_required"] is True
                    and wr["items"][0]["sell_for_recycling"] is True
                ),
            ),
            (
                "hazardous_battery",
                "Nhận diện battery / pin tiểu trong ảnh.",
                lambda wr: (
                    len(wr["items"]) == 1
                    and wr["items"][0]["item_key"] == "battery"
                    and wr["items"][0]["group_id"] == "group_3_hazardous"
                    and wr["has_hazardous"] is True
                    and len(wr["items"][0]["dropoff_points"]) >= 1
                    and len(wr["dropoff_summary"]) >= 1
                ),
            ),
            (
                "oily_plastic_bag_override",
                "Nhận diện oily / túi nilon dính dầu mỡ trong ảnh.",
                lambda wr: (
                    len(wr["items"]) == 1
                    and wr["items"][0]["item_key"] == "oily_plastic_bag"
                    and wr["items"][0]["dirty_oily"] is True
                    and wr["items"][0]["group_id"] == "group_3_other"
                    and wr["items"][0]["sell_for_recycling"] is False
                ),
            ),
            (
                "mixed_bag_warning",
                "Nhận diện mixed / túi rác để lẫn nhiều loại trong ảnh.",
                lambda wr: (
                    wr["mixed_bag"] is True
                    and wr["has_hazardous"] is True
                    and bool(wr["mixed_bag_reason_vi"].strip())
                    and len(wr["items"]) == 2
                ),
            ),
        ]
    else:
        scenarios = [
            (
                "live_image_prompt",
                "Nhận diện các món rác thải trong ảnh để phân loại theo Quyết định 87/2025/QĐ-UBND Hà Nội. Trả về JSON.",
                lambda wr: isinstance(wr["items"], list),
            )
        ]

    expected_ai_delta = 0
    for name, prompt, extra_assert in scenarios:
        payload = {"input": json.dumps({"prompt": prompt, "image": img_url, "json": True}, ensure_ascii=False)}
        st, resp = _http_json(
            f"{base_url}/predict",
            method="POST",
            body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-Device-Id": device_ai},
            timeout=60.0,
        )
        is_ai = st == 200 and resp.get("source") == "ai" and not resp.get("error")
        parsed_wr: Any = None
        schema_errors: list[str] = []
        if isinstance(resp.get("output"), str):
            try:
                parsed_wr = json.loads(resp["output"])
                schema_errors = _validate_waste_result(parsed_wr)
            except ValueError as exc:
                schema_errors = [f"output is not valid JSON: {exc}"]
        else:
            schema_errors = ["missing string 'output' field"]

        domain_ok = bool(parsed_wr is not None and not schema_errors and extra_assert(parsed_wr))
        check(
            f"POST /predict [{name}] source=ai & WasteResult schema",
            is_ai and not schema_errors and domain_ok,
            f"http={st} source={resp.get('source')!r} schema_errors={schema_errors}",
        )
        expected_ai_delta += 1

    # 4. Force fallback check
    expected_fb_delta = 0
    if local_mode or check_fallback:
        fb_payload = {"input": json.dumps({"prompt": "test fallback", "image": img_url, "json": True})}
        fb_st, fb_resp = _http_json(
            f"{base_url}/predict",
            method="POST",
            body=json.dumps(fb_payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "X-Force-Fallback": "1",
                "X-Device-Id": device_fb,
            },
        )
        check(
            "POST /predict X-Force-Fallback=1 returns source='fallback'",
            fb_st == 200 and fb_resp.get("source") == "fallback" and fb_resp.get("error") == "forced",
            f"http={fb_st} resp={fb_resp}",
        )
        expected_fb_delta = 1

    # 5. GET /stats verification
    st_after, stats_after = _http_json(f"{base_url}/stats")
    ai_ok = stats_after.get("ai_requests", 0) >= stats_before.get("ai_requests", 0) + expected_ai_delta
    fb_ok = stats_after.get("fallback", 0) >= stats_before.get("fallback", 0) + expected_fb_delta
    dev_total_ok = stats_after.get("devices_total", 0) >= stats_before.get("devices_total", 0) + (
        2 if (local_mode or check_fallback) else 1
    )
    dev_ai_ok = stats_after.get("devices_ai", 0) >= stats_before.get("devices_ai", 0) + 1
    check(
        "GET /stats incremented ai_requests, fallback, and device counters",
        st_after == 200 and ai_ok and fb_ok and dev_total_ok and dev_ai_ok,
        f"before={stats_before} after={stats_after}",
    )

    print("RESULT:", "PASS" if passed else "FAIL")
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test for Hanoi Waste Sorter backend API.")
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--url", help="Live Render/HTTP base URL (e.g. https://hanoi-waste-ai.onrender.com)")
    mode_group.add_argument(
        "--local",
        "--local-mock",
        dest="local",
        action="store_true",
        help="Start temporary local uvicorn serve.app_llm:app with deterministic mock adapter (default).",
    )
    parser.add_argument("--check-fallback", action="store_true", help="Also verify X-Force-Fallback: 1 in --url mode.")
    args = parser.parse_args()

    if args.url:
        base_url = args.url.rstrip("/")
        _wait_for_health(base_url, timeout_s=60.0)
        return _run_checks(base_url, local_mode=False, check_fallback=args.check_fallback)

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    with tempfile.TemporaryDirectory(prefix="waste_smoke_") as tmpdir:
        adapter_path = Path(tmpdir) / "_waste_smoke_adapter.py"
        adapter_path.write_text(ADAPTER_CODE, encoding="utf-8")

        env = {
            **os.environ,
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "SYSTEM": "_waste_smoke_adapter:run",
            "ALLOW_FORCE_FALLBACK": "1",
            "MAX_CHARS": "1500000",
            "PYTHONPATH": os.pathsep.join(p for p in [tmpdir, str(ML_ROOT), os.environ.get("PYTHONPATH", "")] if p),
        }
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "serve.app_llm:app", "--host", "127.0.0.1", "--port", str(port)],
            cwd=ML_ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            _wait_for_health(base_url, timeout_s=15.0)
            return _run_checks(base_url, local_mode=True, check_fallback=True)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5.0)


if __name__ == "__main__":
    sys.exit(main())
