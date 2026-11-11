"""Hệ thống thật gọi OpenAI qua Responses API (SDK `openai`, cài: pip install openai). Nhận cả chữ lẫn ảnh.

Dùng cho giải có credit OpenAI (ví dụ Codex Community Hackathon Hà Nội). Cùng hợp đồng với mẫu Claude
(mlkit/result.py): thành công trả {"output", "tokens", "source": "ai"}; không có câu trả lời thì ném exception.

Model: KHÔNG đặt sẵn tên model trong kit (tên đổi theo thời gian). Truyền `model=` hoặc đặt biến môi trường OPENAI_MODEL
bằng đúng model bạn đã chạy thử. Thiếu model thì ném lỗi trước khi gửi request.

Đầu vào `text` có hai dạng:
  1. Chuỗi thường: câu hỏi chữ.
  2. Chuỗi JSON (app gửi ảnh qua serve/app_llm.py, hoặc dòng dữ liệu llm_eval):
       {"prompt": "...", "image": "data:image/jpeg;base64,..." | "https://...", "json": true}
       {"prompt": "...", "image_path": "photos/a.jpg", "json": true}      # chỉ dùng khi chạy llm_eval trên máy
     "json": true (hoặc json_output=True) -> yêu cầu model trả một object JSON (text.format = json_object);
     mẫu tự thêm chữ "JSON" vào instructions vì API yêu cầu từ này khi bật json_object.
Ảnh base64 dài: trên server đặt MAX_CHARS đủ lớn (ví dụ 1500000) và app thu nhỏ ảnh còn ~1024 px trước khi gửi.

Đã kiểm bằng SDK thật với transport HTTP giả (tests/test_openai_template.py). CHƯA gọi API thật trong kit. Trước ngày thi:
    OPENAI_API_KEY=... OPENAI_MODEL=<model của bạn> python -X utf8 -c "from examples.openai_system_template import run; print(run('Xin chào'))"
"""
import base64
import json
import mimetypes
import os


class NoTextError(RuntimeError):
    """Response không có câu trả lời dùng được (từ chối, hết max_output_tokens khi chưa có chữ, hoặc rỗng)."""


def parse_input(text):
    """-> (prompt, image_url hoặc None, want_json). Chuỗi không phải JSON object thì coi là câu hỏi chữ."""
    s = text.strip() if isinstance(text, str) else ""
    if s.startswith("{"):
        try:
            d = json.loads(s)
        except ValueError:
            d = None
        if isinstance(d, dict) and ("image" in d or "image_path" in d or "prompt" in d):
            prompt = str(d.get("prompt") or d.get("question") or "")
            image = d.get("image")
            if not image and d.get("image_path"):
                path = d["image_path"]
                mime = mimetypes.guess_type(path)[0] or "image/jpeg"
                with open(path, "rb") as f:
                    image = f"data:{mime};base64,{base64.b64encode(f.read()).decode()}"
            return prompt, image, bool(d.get("json"))
    return text, None, False


def extract_text(resp):
    """Lấy chữ trả lời; từ chối/hết token/rỗng thì ném NoTextError kèm lý do."""
    for item in getattr(resp, "output", None) or []:
        for part in getattr(item, "content", None) or []:
            if getattr(part, "type", None) == "refusal":
                raise NoTextError("refusal: model từ chối trả lời")
    text = (getattr(resp, "output_text", "") or "").strip()
    status = getattr(resp, "status", None)
    if not text:
        details = getattr(resp, "incomplete_details", None)
        reason = getattr(details, "reason", None) if details else None
        hint = " (tăng max_output_tokens)" if reason == "max_output_tokens" else ""
        raise NoTextError(f"no_text: status={status} reason={reason}{hint}")
    return text, status


def run(text, model=None, system="Trả lời ngắn gọn bằng tiếng Việt.", max_output_tokens=2048, timeout=20.0,
        json_output=False, client=None, **extra):
    if extra:
        raise TypeError(f"Tham số không hỗ trợ: {sorted(extra)}")
    model = model or os.environ.get("OPENAI_MODEL")
    if not model:
        raise ValueError("Thiếu model: truyền model=... hoặc đặt OPENAI_MODEL bằng model bạn đã chạy thử.")
    prompt, image, want_json = parse_input(text)
    want_json = want_json or json_output
    instructions = system + (" Trả về đúng một object JSON." if want_json else "")
    content = [{"type": "input_text", "text": prompt or "Mô tả ảnh này."}]
    if image:
        content.append({"type": "input_image", "image_url": image})
    kwargs = {"model": model, "instructions": instructions, "input": [{"role": "user", "content": content}],
              "max_output_tokens": max_output_tokens}
    if want_json:
        kwargs["text"] = {"format": {"type": "json_object"}}
    if client is None:
        import openai

        client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=timeout, max_retries=1)  # timeout thật nằm ở đây
    r = client.responses.create(**kwargs)
    out, status = extract_text(r)
    u = getattr(r, "usage", None)
    tokens = (getattr(u, "total_tokens", 0) or 0) if u else 0
    return {"output": out, "tokens": tokens, "source": "ai", "status": status, "truncated": status == "incomplete"}
