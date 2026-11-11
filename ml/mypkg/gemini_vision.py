"""Gemini Vision adapter using the official google-genai Interactions API."""
from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Any

from examples import openai_system_template

from .waste_rules import load_rules

DEFAULT_GEMINI_MODEL = "gemini-3.5-flash-lite"
_LOCAL_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"

VISION_ITEMS_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "description": "Danh sách các vật phẩm rác thải nhận diện được trong ảnh hoặc mô tả.",
            "items": {
                "type": "object",
                "properties": {
                    "name_vi": {"type": "string", "description": "Tên tiếng Việt ngắn gọn của vật phẩm."},
                    "item_key": {
                        "type": "string",
                        "description": "Khóa phân loại chuẩn trong danh mục Quy định 87/2025/QĐ-UBND.",
                    },
                    "material": {"type": "string", "description": "Chất liệu chính (nhựa, giấy, pin, ...)."},
                    "dirty_oily": {
                        "type": "boolean",
                        "description": "True nếu dính dầu mỡ, thức ăn hoặc chất lỏng bẩn.",
                    },
                    "confidence": {"type": "number", "description": "Độ tin cậy từ 0.0 đến 1.0."},
                },
                "required": ["name_vi", "item_key", "material", "dirty_oily", "confidence"],
            },
        }
    },
    "required": ["items"],
}


def build_gemini_item_schema(rules: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a JSON schema with allowed item_key descriptions from hanoi_rules_87_2025.json."""
    loaded = rules if rules is not None else load_rules()
    keys_hint = ", ".join(loaded["item_rules"].keys())
    schema = {
        "type": "object",
        "properties": {
            "items": {
                **VISION_ITEMS_JSON_SCHEMA["properties"]["items"],
                "items": {
                    **VISION_ITEMS_JSON_SCHEMA["properties"]["items"]["items"],
                    "properties": {
                        **VISION_ITEMS_JSON_SCHEMA["properties"]["items"]["items"]["properties"],
                        "item_key": {
                            "type": "string",
                            "description": f"Bắt buộc chọn một trong các khóa: {keys_hint}",
                        },
                    },
                },
            }
        },
        "required": ["items"],
    }
    return schema


def _read_dotenv_var(names: tuple[str, ...], env_path: Path | None = None) -> str:
    """Safely look up missing local .env secrets without printing or logging values."""
    target = env_path if env_path is not None else _LOCAL_ENV_PATH
    if not target.is_file():
        return ""
    for line in target.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        k, _, v = stripped.partition("=")
        if k.strip() in names:
            cleaned = v.strip().strip("'\"")
            if cleaned:
                return cleaned
    return ""


def get_gemini_api_key(env_path: Path | None = None) -> str:
    """Resolve Gemini Developer API key from environment or local ml/.env."""
    direct = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
    if direct:
        return direct
    return _read_dotenv_var(("GEMINI_API_KEY", "GOOGLE_API_KEY"), env_path=env_path)


def _build_image_part(image: str) -> dict[str, str]:
    """Convert a data URI, URL, or raw base64 string to a Gemini Interaction image block."""
    raw = image.strip()
    if raw.startswith("data:"):
        header, sep, payload = raw.partition(",")
        if not sep or not payload:
            raise ValueError("Data URI ảnh không hợp lệ.")
        mime_type = header[5:].split(";", 1)[0].strip() or "image/jpeg"
        return {"type": "image", "data": payload.strip(), "mime_type": mime_type}
    if raw.startswith(("http://", "https://", "gs://")):
        mime_type = mimetypes.guess_type(raw.split("?", 1)[0])[0] or "image/jpeg"
        return {"type": "image", "uri": raw, "mime_type": mime_type}
    return {"type": "image", "data": raw, "mime_type": "image/jpeg"}


def run(
    text: str,
    model: str | None = None,
    system: str = "Trả lời ngắn gọn bằng tiếng Việt.",
    timeout: float = 20.0,
    json_output: bool = False,
    client: Any = None,
    **extra: Any,
) -> dict[str, Any]:
    """Call Gemini Interactions API (google-genai) for text or multimodal waste extraction."""
    if extra:
        raise TypeError(f"Tham số không hỗ trợ: {sorted(extra)}")

    resolved_model = (model or os.environ.get("GEMINI_MODEL") or DEFAULT_GEMINI_MODEL).strip()
    prompt, image, want_json = openai_system_template.parse_input(text)
    want_json = want_json or json_output

    contents: list[dict[str, Any]] = [
        {"type": "text", "text": prompt or "Nhận diện các món rác thải trong ảnh này."}
    ]
    if image:
        contents.append(_build_image_part(image))

    if client is None:
        from google import genai

        api_key = get_gemini_api_key()
        if not api_key:
            raise ValueError("Thiếu API key Gemini: đặt GEMINI_API_KEY hoặc GOOGLE_API_KEY.")
        client = genai.Client(api_key=api_key)

    kwargs: dict[str, Any] = {
        "model": resolved_model,
        "input": contents,
        "system_instruction": system,
        "store": False,
        "timeout": timeout,
    }
    thinking_level = (
        os.environ.get("GEMINI_THINKING_LEVEL")
        or ("low" if resolved_model.startswith(("gemini-3.7", "gemini-3.8", "gemini-4")) else "")
    ).strip().lower()
    if thinking_level:
        kwargs["generation_config"] = {"thinking_level": thinking_level}
    if want_json:
        kwargs["response_format"] = {
            "type": "text",
            "mime_type": "application/json",
            "schema": build_gemini_item_schema(),
        }

    interaction = client.interactions.create(**kwargs)
    status = getattr(interaction, "status", None)
    if status in {"failed", "cancelled"}:
        raise RuntimeError(f"Gemini interaction {status}")

    output = (getattr(interaction, "output_text", None) or "").strip()
    if not output:
        raise RuntimeError(f"Gemini trả về rỗng (status={status})")

    usage = getattr(interaction, "usage", None)
    total_tokens = int(getattr(usage, "total_tokens", 0) or 0)
    return {"output": output, "tokens": total_tokens, "source": "ai"}

