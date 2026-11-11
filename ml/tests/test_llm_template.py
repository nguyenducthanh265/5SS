"""Kiểm mẫu gọi Claude bằng SDK `anthropic` THẬT nhưng transport HTTP giả: không tốn tiền, kiểm đúng request đi ra
và cách đọc response theo định dạng tài liệu (thinking trước text, redacted_thinking, max_tokens, refusal)."""
import json

import pytest

anthropic = pytest.importorskip("anthropic")
try:  # SDK anthropic mới dùng httpx2, bản cũ dùng httpx
    import httpx2 as httpx
except ImportError:
    httpx = pytest.importorskip("httpx")

from examples import llm_system_template as T  # noqa: E402


def make_client(content, stop="end_turn", captured=None):
    def handler(req):
        if captured is not None:
            captured.append(json.loads(req.content))
        body = {"id": "msg_1", "type": "message", "role": "assistant", "model": "claude-sonnet-5-5", "content": content,
                "stop_reason": stop, "stop_sequence": None, "usage": {"input_tokens": 11, "output_tokens": 7}}
        return httpx.Response(200, json=body)
    return anthropic.Anthropic(api_key="test", http_client=httpx.Client(transport=httpx.MockTransport(handler)), max_retries=0)


THINK = {"type": "thinking", "thinking": "", "signature": "sig"}


def test_request_has_no_sampling_params():
    cap = []
    T.run("Xin chào", client=make_client([{"type": "text", "text": "Chào bạn"}], captured=cap))
    body = cap[0]
    assert not set(body) & {"temperature", "top_p", "top_k"}
    assert body["model"] == "claude-sonnet-5-5" and body["max_tokens"] >= 2048


def test_sampling_params_rejected_before_any_request():
    cap = []
    with pytest.raises(ValueError, match="temperature"):
        T.run("x", temperature=0.0, client=make_client([], captured=cap))
    assert cap == []


def test_text_only_and_thinking_then_text():
    r = T.run("q", client=make_client([{"type": "text", "text": "A"}]))
    assert r["output"] == "A" and r["source"] == "ai" and r["tokens"] == 18
    r = T.run("q", client=make_client([THINK, {"type": "redacted_thinking", "data": "xx"}, {"type": "text", "text": "Hà "}, {"type": "text", "text": "Nội"}]))
    assert r["output"] == "Hà Nội"


def test_no_text_is_an_error_with_stop_reason():
    with pytest.raises(T.NoTextError, match="max_tokens"):
        T.run("q", client=make_client([THINK], stop="max_tokens"))
    with pytest.raises(T.NoTextError, match="refusal"):
        T.run("q", client=make_client([{"type": "text", "text": "Xin lỗi"}], stop="refusal"))


def test_truncated_answer_is_flagged():
    r = T.run("q", client=make_client([THINK, {"type": "text", "text": "dở dang"}], stop="max_tokens"))
    assert r["truncated"] is True


def test_template_inside_api_gives_fallback_not_ai_when_no_text(monkeypatch):
    import importlib, sys
    from fastapi.testclient import TestClient
    sys.modules.pop("serve.app_llm", None)
    m = importlib.import_module("serve.app_llm")
    client = make_client([THINK], stop="max_tokens")
    m.system = lambda text, timeout=None: T.run(text, client=client)
    r = TestClient(m.app).post("/predict", json={"input": "q"}).json()
    assert r["source"] == "fallback" and "NoTextError" in r["error"]
