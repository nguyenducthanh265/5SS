"""Deterministic Rule Engine for Hanoi Waste Sorter (QĐ 87/2025/QĐ-UBND)."""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_RULES_PATH = Path(__file__).resolve().parents[1] / "data" / "hanoi_rules_87_2025.json"

DEFAULT_ITEM_NAMES_VI: dict[str, str] = {
    "milk_carton": "Vỏ hộp sữa giấy",
    "plastic_bottle": "Chai nhựa",
    "aluminum_can": "Lon nhôm",
    "cardboard_paper": "Giấy, bìa carton",
    "oily_plastic_bag": "Túi nilon dính dầu mỡ",
    "clean_plastic_bag": "Túi nilon sạch",
    "medicine_blister": "Vỉ thuốc rỗng",
    "battery": "Pin thải",
    "light_bulb": "Bóng đèn huỳnh quang",
    "small_ewaste": "Thiết bị điện tử nhỏ",
    "food_waste": "Chất thải thực phẩm",
    "other_non_recyclable": "Rác thải sinh hoạt khác",
}

GROUP_SPOKEN_VI: dict[str, str] = {
    "group_1_recyclable": "Nhóm 1, rác tái chế",
    "group_2_food": "Nhóm 2, rác thực phẩm",
    "group_3_other": "Nhóm 3, rác thải còn lại",
    "group_3_hazardous": "Nhóm 3, rác nguy hại",
    "group_3_bulky": "Nhóm 3, rác cồng kềnh",
}


@lru_cache(maxsize=4)
def _load_rules_cached(resolved_path: str) -> dict[str, Any]:
    return json.loads(Path(resolved_path).read_text(encoding="utf-8"))


def load_rules(path: Path | str | None = None) -> dict[str, Any]:
    """Load Hanoi waste sorting rules from JSON."""
    target = Path(path) if path is not None else DEFAULT_RULES_PATH
    return _load_rules_cached(str(target.resolve()))


def _coerce_bool(value: Any, default: bool = False) -> bool:
    """Safely coerce boolean-like LLM values (handling 'false'/'0'/'no' strings)."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return default
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "có", "co"}:
            return True
        if normalized in {"false", "0", "no", "n", "", "null", "none", "không", "khong"}:
            return False
    return default


def _normalize_item_key(value: Any) -> str:
    """Normalize raw Vision item_key to lowercase snake_case."""
    if not isinstance(value, str):
        return ""
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def _resolve_item(raw_item: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    """Evaluate a single raw Vision item against hanoi_rules_87_2025.json."""
    item_rules = rules["item_rules"]
    groups = rules["groups"]
    dropoff_catalog = rules.get("dropoff_points", {})

    raw_key = _normalize_item_key(raw_item.get("item_key")) or "other_non_recyclable"
    dirty_oily = _coerce_bool(raw_item.get("dirty_oily", False))

    if raw_key == "clean_plastic_bag" and dirty_oily:
        effective_key = "oily_plastic_bag"
    elif raw_key in item_rules:
        effective_key = raw_key
    else:
        effective_key = "other_non_recyclable"

    if effective_key == "oily_plastic_bag":
        dirty_oily = True

    rule = item_rules[effective_key]
    if dirty_oily and "dirty_override_group" in rule:
        group_id = rule["dirty_override_group"]
    else:
        group_id = rule["default_group"]

    group_info = groups[group_id]
    rinse_required = bool(rule.get("rinse_required", False)) or (
        dirty_oily and bool(rule.get("rinse_required_if_dirty", False))
    )
    sell_for_recycling = bool(rule.get("sell_for_recycling", False)) and group_id == "group_1_recyclable"

    dropoff_cat = rule.get("dropoff_category")
    dropoff_points = [dict(pt) for pt in dropoff_catalog.get(dropoff_cat, [])] if dropoff_cat else []

    raw_name = raw_item.get("name_vi")
    name_vi = raw_name.strip() if isinstance(raw_name, str) and raw_name.strip() else DEFAULT_ITEM_NAMES_VI.get(effective_key, effective_key)
    raw_material = raw_item.get("material")
    material = raw_material.strip() if isinstance(raw_material, str) else ""

    return {
        "name_vi": name_vi,
        "item_key": effective_key,
        "material": material,
        "dirty_oily": dirty_oily,
        "group_id": group_id,
        "group_name_vi": group_info["name_vi"],
        "group_short_label": group_info["short_label"],
        "color_hex": group_info["color_hex"],
        "rinse_required": rinse_required,
        "sell_for_recycling": sell_for_recycling,
        "is_hazardous": bool(rule.get("is_hazardous", False)) or group_id == "group_3_hazardous",
        "dropoff_points": dropoff_points,
        "note_vi": str(rule.get("note_vi", "")),
    }


def _dedupe_dropoff_points(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collect unique dropoff points across all items while preserving order."""
    seen: set[tuple[str, str]] = set()
    summary: list[dict[str, Any]] = []
    for item in items:
        for pt in item["dropoff_points"]:
            key = (pt.get("name", ""), pt.get("area", ""))
            if key not in seen:
                seen.add(key)
                summary.append(pt)
    return summary


def _join_unique(values: list[str]) -> str:
    seen: list[str] = []
    for v in values:
        if v and v not in seen:
            seen.append(v)
    return ", ".join(seen)


def _build_mixed_bag_reason(items: list[dict[str, Any]], has_hazardous: bool) -> str:
    group_labels = _join_unique([it["group_short_label"] for it in items])
    if has_hazardous:
        haz_names = _join_unique([it["name_vi"] for it in items if it["is_hazardous"]])
        other_labels = _join_unique([it["group_short_label"] for it in items if not it["is_hazardous"]])
        other_part = f" với {other_labels}" if other_labels else ""
        return (
            f"CẢNH BÁO NGUY HẠI: Túi rác đang để lẫn chất thải nguy hại ({haz_names}){other_part}. "
            "Tuyệt đối không bỏ chung rác sinh hoạt; hãy tách riêng ngay và mang tới điểm thu hồi."
        )
    return (
        f"Túi rác đang để lẫn nhiều nhóm ({group_labels}). "
        "Cần tách riêng theo Quyết định 87/2025/QĐ-UBND để tránh bị đơn vị thu gom từ chối."
    )


def _build_speech_vi(
    items: list[dict[str, Any]],
    mixed_bag: bool,
    has_hazardous: bool,
    dropoff_summary: list[dict[str, Any]],
) -> str:
    """Compose natural, concise Vietnamese speech for expo-speech."""
    if not items:
        return "Chưa nhận diện được món rác nào trong ảnh. Bạn vui lòng chụp lại rõ hơn nhé."

    parts: list[str] = []
    distinct_groups = list(dict.fromkeys(it["group_id"] for it in items))

    if mixed_bag:
        if has_hazardous:
            haz_names = _join_unique([it["name_vi"] for it in items if it["is_hazardous"]])
            parts.append(
                f"Cảnh báo: túi rác đang để lẫn chất thải nguy hại gồm {haz_names} với nhóm rác khác. "
                "Không bỏ chung rác sinh hoạt, hãy tách riêng ngay."
            )
        else:
            group_spoken = _join_unique([GROUP_SPOKEN_VI.get(gid, gid) for gid in distinct_groups])
            parts.append(
                f"Cảnh báo túi rác đang để lẫn {len(distinct_groups)} nhóm gồm {group_spoken}. "
                "Bạn cần tách riêng từng loại trước khi bỏ."
            )
    else:
        gid = distinct_groups[0]
        group_spoken = GROUP_SPOKEN_VI.get(gid, items[0]["group_name_vi"])
        if len(items) == 1:
            parts.append(f"Đây là {items[0]['name_vi']}, thuộc {group_spoken}.")
        else:
            names = _join_unique([it["name_vi"] for it in items])
            parts.append(f"Các món gồm {names}, đều thuộc {group_spoken}.")

    keys = {it["item_key"] for it in items}
    if any(it["rinse_required"] for it in items):
        if "milk_carton" in keys:
            parts.append("Bạn nhớ đổ cạn, tráng sạch và ép dẹp trước khi bỏ.")
        else:
            parts.append("Bạn nhớ tráng sạch trước khi bỏ.")

    if any(it["sell_for_recycling"] for it in items):
        parts.append("Có thể gom bán ve chai hoặc phế liệu.")

    if dropoff_summary:
        first_point = dropoff_summary[0]["name"]
        if "battery" in keys:
            parts.append(f"Pin thải cần dán băng keo hai đầu và mang tới {first_point}.")
        elif has_hazardous:
            parts.append(f"Bọc kỹ chất thải nguy hại và mang tới {first_point}.")
        else:
            parts.append(f"Có thể mang tới {first_point}.")
    elif not mixed_bag:
        if "oily_plastic_bag" in keys or any(it["item_key"] == "cardboard_paper" and it["dirty_oily"] for it in items):
            parts.append("Đồ dính dầu mỡ không tái chế được, bỏ vào thùng rác thải còn lại.")
        elif "medicine_blister" in keys:
            parts.append("Vỉ thuốc ghép nhôm nhựa khó tách tái chế, bỏ vào nhóm rác thải còn lại.")

    return " ".join(parts)


def evaluate_items(raw_items: list[dict[str, Any]], rules: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate raw Vision LLM items using Hanoi QĐ 87/2025/QĐ-UBND rules."""
    if not isinstance(raw_items, list):
        raise ValueError("raw_items must be a list of item dicts")

    for idx, item in enumerate(raw_items):
        if not isinstance(item, dict):
            raise ValueError(f"raw_items[{idx}] must be a dict")

    loaded_rules = rules if rules is not None else load_rules()
    evaluated = [_resolve_item(item, loaded_rules) for item in raw_items]

    distinct_groups = {it["group_id"] for it in evaluated}
    mixed_bag = len(distinct_groups) >= 2
    has_hazardous = any(it["is_hazardous"] for it in evaluated)
    mixed_bag_reason_vi = _build_mixed_bag_reason(evaluated, has_hazardous) if mixed_bag else ""
    dropoff_summary = _dedupe_dropoff_points(evaluated)
    collection_window_vi = loaded_rules["regulation"]["collection_window_urban"]
    speech_vi = _build_speech_vi(evaluated, mixed_bag, has_hazardous, dropoff_summary)

    return {
        "items": evaluated,
        "mixed_bag": mixed_bag,
        "mixed_bag_reason_vi": mixed_bag_reason_vi,
        "has_hazardous": has_hazardous,
        "dropoff_summary": dropoff_summary,
        "collection_window_vi": collection_window_vi,
        "speech_vi": speech_vi,
    }
