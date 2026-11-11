"""Kiểm mẫu gọi OpenAI bằng SDK `openai` THẬT nhưng transport HTTP giả: không tốn tiền, kiểm request đi ra
(chữ, ảnh, JSON mode, không có tham số lấy mẫu) và cách đọc response (text, từ chối, hết token)."""
import base64
import json

import pytest

openai = pytest.importorskip("openai")
try:  # SDK mới có thể dùng httpx2
    import httpx2 as httpx
except ImportError:
    httpx = pytest.importorskip("httpx")

from examples import openai_system_template as T  # noqa: E402
from mlkit.result import normalize  # noqa: E402


def make_client(content=None, status="completed", captured=None, incomplete=None):
    def handler(req):
        if captured is not None:
            captured.append(json.loads(req.content))
        output = [] if content is None else [{"type": "message", "id": "msg_1", "status": "completed", "role": "assistant", "content": content}]
        body = {"id": "resp_1", "object": "response", "created_at": 0, "status": status, "model": "m", "output": output,
                "incomplete_details": incomplete, "usage": {"input_tokens": 11, "output_tokens": 7, "total_tokens": 18},
                "parallel_tool_calls": True, "tool_choice": "auto", "tools": []}
        return httpx.Response(200, json=body)
    return openai.OpenAI(api_key="test", http_client=httpx.Client(transport=httpx.MockTransport(handler)), max_retries=0)


def text(t):
    return [{"type": "output_text", "text": t, "annotations": []}]


def test_text_request_and_contract(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "model-from-env")
    cap = []
    r = T.run("Xin chào", client=make_client(text("Chào bạn"), captured=cap))
    body = cap[0]
    assert body["model"] == "model-from-env"
    assert not set(body) & {"temperature", "top_p", "top_k"} and "text" not in body
    assert body["input"][0]["content"] == [{"type": "input_text", "text": "Xin chào"}]
    assert r["output"] == "Chào bạn" and r["source"] == "ai" and r["tokens"] == 18 and r["truncated"] is False
    assert normalize(r)["ok"] is True


def test_missing_model_fails_before_any_request(monkeypatch):
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    cap = []
    with pytest.raises(ValueError, match="OPENAI_MODEL"):
        T.run("x", client=make_client(text("y"), captured=cap))
    assert cap == []


def test_unknown_params_rejected():
    with pytest.raises(TypeError, match="temperature"):
        T.run("x", model="m", temperature=0, client=make_client(text("y")))


def test_image_from_app_with_json_mode():
    cap = []
    payload = json.dumps({"prompt": "Đọc thành phần", "image": "data:image/jpeg;base64,AAAA", "json": True})
    r = T.run(payload, model="m", client=make_client(text('{"allergens": ["sữa"]}'), captured=cap))
    body = cap[0]
    parts = body["input"][0]["content"]
    assert parts[0] == {"type": "input_text", "text": "Đọc thành phần"}
    assert parts[1] == {"type": "input_image", "image_url": "data:image/jpeg;base64,AAAA"}
    assert body["text"] == {"format": {"type": "json_object"}} and "JSON" in body["instructions"]
    assert json.loads(r["output"]) == {"allergens": ["sữa"]}


def test_image_path_for_llm_eval(tmp_path):
    img = tmp_path / "a.png"
    img.write_bytes(b"\x89PNGfake")
    cap = []
    T.run(json.dumps({"prompt": "p", "image_path": str(img)}), model="m", client=make_client(text("ok"), captured=cap))
    url = cap[0]["input"][0]["content"][1]["image_url"]
    assert url == "data:image/png;base64," + base64.b64encode(b"\x89PNGfake").decode()


def test_plain_text_that_looks_like_json_is_kept():
    cap = []
    T.run('{"a": 1}', model="m", client=make_client(text("ok"), captured=cap))
    assert cap[0]["input"][0]["content"] == [{"type": "input_text", "text": '{"a": 1}'}]


def test_refusal_and_incomplete_are_errors():
    with pytest.raises(T.NoTextError, match="refusal"):
        T.run("q", model="m", client=make_client([{"type": "refusal", "refusal": "Không thể"}]))
    with pytest.raises(T.NoTextError, match="max_output_tokens"):
        T.run("q", model="m", client=make_client(None, status="incomplete", incomplete={"reason": "max_output_tokens"}))
