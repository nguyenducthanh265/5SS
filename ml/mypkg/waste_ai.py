"""Vision AI + Hanoi Rule Engine pipeline compatible with serve/app_llm.py and mlkit/result.py."""
from __future__ import annotations

import json
import os
import re
from typing import Any

from examples import openai_system_template

from . import gemini_vision
from .waste_rules import evaluate_items, load_rules


def build_vision_system_prompt(rules: dict[str, Any] | None = None) -> str:
    """Build the Vision extraction system prompt from hanoi_rules_87_2025.json."""
    loaded = rules if rules is not None else load_rules()
    item_keys = ", ".join(loaded["item_rules"].keys())
    return (
        "Bạn là bộ nhận diện vật phẩm rác thải sinh hoạt từ ảnh hoặc mô tả. "
        "KHÔNG tự phân nhóm rác hay đưa ra lời khuyên xử lý. "
        "Chỉ trả về đúng một object JSON theo cấu trúc: "
        '{"items": [{"name_vi": str, "item_key": str, "material": str, "dirty_oily": bool, "confidence": float}]}. '
        f"Trường item_key BẮT BUỘC chọn đúng một trong danh mục: {item_keys}. "
        "Đặt dirty_oily=true nếu vật phẩm dính dầu mỡ, thức ăn hoặc chất lỏng bẩn; "
        "confidence là số thực từ 0.0 đến 1.0."
    )


_OUTER_FENCE_RE = re.compile(r"^```(?:json)?\s*([\s\S]*?)\s*```$", re.IGNORECASE)
_EMBEDDED_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def _strip_json_fences(raw_output: str) -> str:
    """Strip UTF-8 BOM, whitespace, and optional markdown ```json fences."""
    cleaned = raw_output.lstrip("\ufeff").strip()
    outer = _OUTER_FENCE_RE.match(cleaned)
    if outer:
        return outer.group(1).strip()
    return cleaned


def _parse_vision_items(raw_output: str) -> list[dict[str, Any]]:
    """Validate and extract the 'items' list from Vision LLM JSON output."""
    if not isinstance(raw_output, str):
        raise ValueError("Vision LLM returned invalid JSON: output must be a string")

    cleaned = _strip_json_fences(raw_output)
    try:
        parsed = json.loads(cleaned)
    except ValueError as exc:
        embedded = _EMBEDDED_FENCE_RE.search(raw_output)
        if embedded:
            try:
                parsed = json.loads(embedded.group(1).strip())
            except ValueError as inner_exc:
                raise ValueError(f"Vision LLM returned invalid JSON: {inner_exc}") from inner_exc
        else:
            raise ValueError(f"Vision LLM returned invalid JSON: {exc}") from exc

    if not isinstance(parsed, dict) or "items" not in parsed or not isinstance(parsed["items"], list):
        raise ValueError("Vision LLM JSON must be an object containing an 'items' list")

    for idx, item in enumerate(parsed["items"]):
        if not isinstance(item, dict):
            raise ValueError(f"Vision LLM 'items[{idx}]' must be a JSON object")

    return parsed["items"]


def resolve_provider(
    provider: str | None = None,
    model: str | None = None,
    client: Any = None,
) -> str:
    """Resolve whether to call Gemini (`gemini`) or OpenAI (`openai`)."""
    explicit = (provider or os.environ.get("LLM_PROVIDER") or "auto").strip().lower()
    if explicit in {"gemini", "google"}:
        return "gemini"
    if explicit == "openai":
        return "openai"
    if explicit != "auto":
        raise ValueError(f"Unsupported LLM_PROVIDER: {explicit!r} (expected auto, gemini, or openai)")

    if client is not None:
        if hasattr(client, "interactions") and not hasattr(client, "responses"):
            return "gemini"
        return "openai"

    model_hint = (model or "").strip().lower()
    if model_hint.startswith(("gemini", "gemma")):
        return "gemini"

    if gemini_vision.get_gemini_api_key() and not (os.environ.get("OPENAI_API_KEY") or "").strip():
        return "gemini"
    if (os.environ.get("OPENAI_API_KEY") or "").strip():
        return "openai"
    if gemini_vision.get_gemini_api_key():
        return "gemini"

    return "gemini" if (os.environ.get("GEMINI_MODEL") or "").strip() else "openai"


def run(
    text: str,
    model: str | None = None,
    timeout: float = 20.0,
    client: Any = None,
    provider: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Call Vision LLM (Gemini or OpenAI) to extract items, then apply Hanoi QĐ 87/2025 rules."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Input must be a non-empty string")

    chosen = resolve_provider(provider=provider, model=model, client=client)
    runner = gemini_vision.run if chosen == "gemini" else openai_system_template.run
    vision_resp = runner(
        text,
        model=model,
        system=build_vision_system_prompt(),
        timeout=timeout,
        json_output=True,
        client=client,
        **extra,
    )
    if vision_resp.get("source", "ai") != "ai":
        raise RuntimeError(f"Unexpected non-AI response source: {vision_resp.get('source')}")

    raw_items = _parse_vision_items(vision_resp.get("output"))
    evaluated = evaluate_items(raw_items)
    return {
        "output": json.dumps(evaluated, ensure_ascii=False),
        "tokens": int(vision_resp.get("tokens") or 0),
        "source": "ai",
    }
