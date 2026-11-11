"""Hợp đồng kết quả chung cho mọi "hệ thống AI" mà kit gọi (llm_eval và serve/app_llm.py). Chỉ dùng thư viện chuẩn.

Hàm hệ thống trả về một trong hai dạng:
  - str: câu trả lời
  - dict: {"output": str, "tokens"?: int, "source"?: str, "error"?: str, ...}
Kết quả CHỈ được coi là AI thành công khi: output là chuỗi không rỗng, không có "error" (khác rỗng),
và "source" (nếu có) bằng "ai". Mọi trường hợp khác (fallback, lỗi, rỗng, sai kiểu) là thất bại và giữ nguyên lý do,
để không bao giờ có chuyện câu mẫu được gắn nhãn "ai" hay được tính vào số liệu AI thật.
Lỗi nặng (không gọi được nhà cung cấp, không có text...) nên ném exception thay vì trả dict.
"""
from __future__ import annotations


def normalize(r):
    """-> {"ok": bool, "output": str, "tokens": int, "source": str, "error": str | None}"""
    if isinstance(r, str):
        ok = bool(r.strip())
        return {"ok": ok, "output": r, "tokens": 0, "source": "ai" if ok else "invalid", "error": None if ok else "empty_output"}
    if not isinstance(r, dict):
        return {"ok": False, "output": "", "tokens": 0, "source": "invalid", "error": f"bad_return_type:{type(r).__name__}"}
    out = r.get("output")
    try:
        tokens = int(r.get("tokens") or 0)
    except (TypeError, ValueError):
        tokens = 0
    src = r.get("source", "ai")
    err = r.get("error") or None
    if not isinstance(out, str):
        return {"ok": False, "output": "" if out is None else str(out), "tokens": tokens, "source": "invalid",
                "error": err or f"bad_output_type:{type(out).__name__}"}
    if err:
        return {"ok": False, "output": out, "tokens": tokens, "source": src if src != "ai" else "error", "error": str(err)}
    if src != "ai":
        return {"ok": False, "output": out, "tokens": tokens, "source": str(src), "error": f"system_source:{src}"}
    if not out.strip():
        return {"ok": False, "output": out, "tokens": tokens, "source": "invalid", "error": "empty_output"}
    return {"ok": True, "output": out, "tokens": tokens, "source": "ai", "error": None}
