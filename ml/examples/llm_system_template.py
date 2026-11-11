"""Hệ thống thật gọi Claude qua Messages API (SDK `anthropic`, cài: pip install anthropic).

Đã kiểm bằng SDK thật với transport HTTP giả (tests/test_llm_template.py): request tạo ra và cách đọc response.
CHƯA gọi API thật trong kit. Trước ngày thi, chạy một request thật bằng account của bạn:
    ANTHROPIC_API_KEY=... python -X utf8 -c "from examples.llm_system_template import run; print(run('Xin chào'))"

Theo tài liệu Anthropic cho claude-sonnet-5-5 (đọc ngày 05/11/2026):
  - đặt temperature / top_p / top_k trả lỗi 400 -> mẫu này không gửi và từ chối nếu bạn truyền vào;
  - adaptive thinking bật mặc định -> response thường có block `thinking` (có thể rỗng) TRƯỚC block `text`;
    có thể có `redacted_thinking`; chỉ nối các block `type == "text"`;
  - thinking tính vào max_tokens -> max_tokens nhỏ có thể hết trước khi có text (stop_reason = "max_tokens").
Đổi model khác thì đọc lại tài liệu của model đó; tham số hợp lệ khác nhau giữa các model.
Quy ước của kit (mlkit/result.py): thành công trả {"output", "tokens", "source": "ai"}; không có câu trả lời thì ném exception.
"""
import os

SAMPLING_PARAMS = ("temperature", "top_p", "top_k")


class NoTextError(RuntimeError):
    """Response không có câu trả lời dùng được (không có block text, bị từ chối, hoặc hết max_tokens khi chưa có text)."""


def extract_text(resp):
    """Nối mọi block text; bỏ qua thinking/redacted_thinking/tool blocks. Không có text thì ném NoTextError kèm stop_reason."""
    parts = [getattr(b, "text", "") for b in (resp.content or []) if getattr(b, "type", None) == "text"]
    text = "".join(parts).strip()
    stop = getattr(resp, "stop_reason", None)
    if stop == "refusal":
        raise NoTextError("refusal: model từ chối trả lời")
    if not text:
        hint = " (tăng max_tokens: thinking cũng tính vào max_tokens)" if stop == "max_tokens" else ""
        raise NoTextError(f"no_text: stop_reason={stop}{hint}")
    return text, stop


def run(text, model="claude-sonnet-5-5", system="Trả lời ngắn gọn bằng tiếng Việt.", max_tokens=4096, timeout=20.0,
        client=None, **extra):
    bad = [k for k in extra if k in SAMPLING_PARAMS]
    if bad:
        raise ValueError(f"{model} từ chối {bad} (HTTP 400 theo tài liệu Anthropic); xóa khỏi params.")
    if extra:
        raise TypeError(f"Tham số không hỗ trợ: {sorted(extra)}")
    if client is None:
        import anthropic

        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=timeout, max_retries=1)  # timeout thật nằm ở đây
    r = client.messages.create(model=model, max_tokens=max_tokens, system=system, messages=[{"role": "user", "content": text}])
    out, stop = extract_text(r)
    u = getattr(r, "usage", None)
    tokens = (getattr(u, "input_tokens", 0) or 0) + (getattr(u, "output_tokens", 0) or 0) if u else 0
    return {"output": out, "tokens": tokens, "source": "ai", "stop_reason": stop, "truncated": stop == "max_tokens"}
