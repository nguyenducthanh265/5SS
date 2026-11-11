"""Tests for Hanoi Waste Sorter Rule Engine (mypkg.waste_rules) and Vision AI pipeline (mypkg.waste_ai)."""
import importlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mlkit.result import normalize  # noqa: E402
from mypkg import waste_ai, waste_rules  # noqa: E402

REQUIRED_TOP_KEYS = {
    "items",
    "mixed_bag",
    "mixed_bag_reason_vi",
    "has_hazardous",
    "dropoff_summary",
    "collection_window_vi",
    "speech_vi",
}

REQUIRED_ITEM_KEYS = {
    "name_vi",
    "item_key",
    "material",
    "dirty_oily",
    "group_id",
    "group_name_vi",
    "rinse_required",
    "sell_for_recycling",
    "dropoff_points",
    "note_vi",
}


def _assert_schema(res: dict) -> None:
    assert REQUIRED_TOP_KEYS <= set(res.keys())
    assert isinstance(res["items"], list)
    assert isinstance(res["mixed_bag"], bool)
    assert isinstance(res["mixed_bag_reason_vi"], str)
    assert isinstance(res["has_hazardous"], bool)
    assert isinstance(res["dropoff_summary"], list)
    assert isinstance(res["collection_window_vi"], str) and "18:00 - 22:00" in res["collection_window_vi"]
    assert isinstance(res["speech_vi"], str) and res["speech_vi"].strip()
    for it in res["items"]:
        assert REQUIRED_ITEM_KEYS <= set(it.keys())
        assert isinstance(it["dirty_oily"], bool)
        assert isinstance(it["rinse_required"], bool)
        assert isinstance(it["sell_for_recycling"], bool)
        assert isinstance(it["dropoff_points"], list)


def test_milk_carton_rule():
    res = waste_rules.evaluate_items([
        {"name_vi": "Vỏ hộp sữa giấy", "item_key": "milk_carton", "material": "Giấy tráng nhôm", "dirty_oily": False}
    ])
    _assert_schema(res)
    it = res["items"][0]
    assert it["group_id"] == "group_1_recyclable"
    assert it["rinse_required"] is True
    assert it["sell_for_recycling"] is True
    assert it["dropoff_points"] == []
    assert res["mixed_bag"] is False
    assert res["has_hazardous"] is False
    assert "tái chế" in res["speech_vi"].lower()
    assert "tráng" in res["speech_vi"].lower()
    assert "ve chai" in res["speech_vi"].lower() or "phế liệu" in res["speech_vi"].lower()


def test_battery_hazardous_and_dropoff():
    res = waste_rules.evaluate_items([
        {"name_vi": "Pin tiểu AA", "item_key": "battery", "material": "Kim loại/Hóa chất", "dirty_oily": False}
    ])
    _assert_schema(res)
    it = res["items"][0]
    assert it["group_id"] == "group_3_hazardous"
    assert it["rinse_required"] is False
    assert it["sell_for_recycling"] is False
    assert len(it["dropoff_points"]) >= 1
    assert res["has_hazardous"] is True
    assert res["mixed_bag"] is False
    assert len(res["dropoff_summary"]) == len(it["dropoff_points"])
    assert "nguy hại" in res["speech_vi"].lower()
    assert "pin" in res["speech_vi"].lower()


def test_oily_plastic_bag_and_clean_bag_dirty_override():
    res_clean_dirty = waste_rules.evaluate_items([
        {"name_vi": "Túi nilon đựng đồ ăn", "item_key": "clean_plastic_bag", "material": "Nhựa", "dirty_oily": True}
    ])
    _assert_schema(res_clean_dirty)
    it = res_clean_dirty["items"][0]
    assert it["item_key"] == "oily_plastic_bag"
    assert it["group_id"] == "group_3_other"
    assert it["sell_for_recycling"] is False
    assert it["rinse_required"] is False

    res_oily = waste_rules.evaluate_items([
        {"name_vi": "Túi nilon dính dầu mỡ", "item_key": "oily_plastic_bag", "material": "Nhựa", "dirty_oily": True}
    ])
    _assert_schema(res_oily)
    assert res_oily["items"][0]["group_id"] == "group_3_other"
    assert res_oily["items"][0]["sell_for_recycling"] is False

    res_clean = waste_rules.evaluate_items([
        {"name_vi": "Túi nilon khô sạch", "item_key": "clean_plastic_bag", "material": "Nhựa", "dirty_oily": False}
    ])
    _assert_schema(res_clean)
    assert res_clean["items"][0]["item_key"] == "clean_plastic_bag"
    assert res_clean["items"][0]["group_id"] == "group_1_recyclable"


def test_cardboard_and_bottle_dirty_oily_rules():
    res_card_dirty = waste_rules.evaluate_items([
        {"name_vi": "Hộp pizza dính dầu", "item_key": "cardboard_paper", "material": "Bìa carton", "dirty_oily": True}
    ])
    _assert_schema(res_card_dirty)
    assert res_card_dirty["items"][0]["group_id"] == "group_3_other"
    assert res_card_dirty["items"][0]["sell_for_recycling"] is False

    res_card_clean = waste_rules.evaluate_items([
        {"name_vi": "Thùng carton sạch", "item_key": "cardboard_paper", "material": "Bìa carton", "dirty_oily": False}
    ])
    _assert_schema(res_card_clean)
    assert res_card_clean["items"][0]["group_id"] == "group_1_recyclable"
    assert res_card_clean["items"][0]["sell_for_recycling"] is True

    res_bottle_dirty = waste_rules.evaluate_items([
        {"name_vi": "Chai nhựa còn nước ngọt", "item_key": "plastic_bottle", "material": "Nhựa PET", "dirty_oily": True}
    ])
    _assert_schema(res_bottle_dirty)
    assert res_bottle_dirty["items"][0]["group_id"] == "group_1_recyclable"
    assert res_bottle_dirty["items"][0]["rinse_required"] is True
    assert res_bottle_dirty["items"][0]["sell_for_recycling"] is True


def test_medicine_blister_rule():
    res = waste_rules.evaluate_items([
        {"name_vi": "Vỉ thuốc rỗng", "item_key": "medicine_blister", "material": "Nhôm-nhựa", "dirty_oily": False}
    ])
    _assert_schema(res)
    it = res["items"][0]
    assert it["group_id"] == "group_3_other"
    assert it["rinse_required"] is False
    assert it["sell_for_recycling"] is False
    assert res["has_hazardous"] is False
    assert "rác thải còn lại" in res["speech_vi"].lower()


def test_mixed_bag_regular_plus_battery_and_non_hazardous_mixed():
    res_haz = waste_rules.evaluate_items([
        {"name_vi": "Thức ăn thừa", "item_key": "food_waste", "material": "Hữu cơ", "dirty_oily": True},
        {"name_vi": "Pin tiểu", "item_key": "battery", "material": "Kim loại", "dirty_oily": False},
    ])
    _assert_schema(res_haz)
    assert res_haz["mixed_bag"] is True
    assert res_haz["has_hazardous"] is True
    assert "CẢNH BÁO NGUY HẠI" in res_haz["mixed_bag_reason_vi"]
    assert "Pin tiểu" in res_haz["mixed_bag_reason_vi"]
    assert len(res_haz["dropoff_summary"]) >= 1
    assert "cảnh báo" in res_haz["speech_vi"].lower()
    assert "nguy hại" in res_haz["speech_vi"].lower()

    res_non_haz = waste_rules.evaluate_items([
        {"name_vi": "Chai nhựa", "item_key": "plastic_bottle", "material": "Nhựa", "dirty_oily": False},
        {"name_vi": "Vỏ chuối", "item_key": "food_waste", "material": "Hữu cơ", "dirty_oily": False},
    ])
    _assert_schema(res_non_haz)
    assert res_non_haz["mixed_bag"] is True
    assert res_non_haz["has_hazardous"] is False
    assert res_non_haz["mixed_bag_reason_vi"] != ""
    assert "cảnh báo" in res_non_haz["speech_vi"].lower()

    res_same_group = waste_rules.evaluate_items([
        {"name_vi": "Hộp sữa", "item_key": "milk_carton", "material": "Giấy", "dirty_oily": False},
        {"name_vi": "Lon bia", "item_key": "aluminum_can", "material": "Nhôm", "dirty_oily": False},
    ])
    _assert_schema(res_same_group)
    assert res_same_group["mixed_bag"] is False
    assert res_same_group["mixed_bag_reason_vi"] == ""


def test_empty_and_unknown_items_handled_gracefully():
    res_empty = waste_rules.evaluate_items([])
    _assert_schema(res_empty)
    assert res_empty["items"] == []
    assert res_empty["mixed_bag"] is False

    res_unknown = waste_rules.evaluate_items([
        {"name_vi": "Đồ lạ", "item_key": "unknown_xyz", "material": "Không rõ", "dirty_oily": False}
    ])
    _assert_schema(res_unknown)
    assert res_unknown["items"][0]["item_key"] == "other_non_recyclable"
    assert res_unknown["items"][0]["group_id"] == "group_3_other"


def _make_fake_openai_client(output_text: str, captured: list | None = None):
    openai = pytest.importorskip("openai")
    try:
        import httpx2 as httpx
    except ImportError:
        httpx = pytest.importorskip("httpx")

    def handler(req):
        if captured is not None:
            captured.append(json.loads(req.content))
        body = {
            "id": "resp_test",
            "object": "response",
            "created_at": 0,
            "status": "completed",
            "model": "vision-test",
            "output": [
                {
                    "type": "message",
                    "id": "msg_1",
                    "status": "completed",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": output_text, "annotations": []}],
                }
            ],
            "incomplete_details": None,
            "usage": {"input_tokens": 10, "output_tokens": 8, "total_tokens": 18},
            "parallel_tool_calls": True,
            "tool_choice": "auto",
            "tools": [],
        }
        return httpx.Response(200, json=body)

    return openai.OpenAI(api_key="test", http_client=httpx.Client(transport=httpx.MockTransport(handler)), max_retries=0)


def test_vision_prompt_includes_all_rule_keys():
    rules = waste_rules.load_rules()
    prompt = waste_ai.build_vision_system_prompt(rules)
    assert "JSON" in prompt
    for key in rules["item_rules"]:
        assert key in prompt


def test_waste_ai_run_and_result_contract_with_fake_client():
    captured = []
    vision_json = json.dumps({
        "items": [
            {
                "name_vi": "Vỏ hộp sữa giấy",
                "item_key": "milk_carton",
                "material": "Giấy tráng nhôm/nhựa",
                "dirty_oily": False,
                "confidence": 0.96,
            }
        ]
    })
    client = _make_fake_openai_client(vision_json, captured=captured)
    payload = json.dumps({"prompt": "Phân loại rác trong ảnh", "image": "data:image/jpeg;base64,AAAA", "json": True})

    r = waste_ai.run(payload, model="vision-test", timeout=15.0, client=client)
    n = normalize(r)
    assert n["ok"] is True
    assert n["source"] == "ai"
    assert n["tokens"] == 18

    body = captured[0]
    assert body["text"] == {"format": {"type": "json_object"}}
    assert body["input"][0]["content"][1] == {"type": "input_image", "image_url": "data:image/jpeg;base64,AAAA"}

    evaluated = json.loads(n["output"])
    _assert_schema(evaluated)
    assert evaluated["items"][0]["item_key"] == "milk_carton"
    assert evaluated["items"][0]["rinse_required"] is True
    assert evaluated["items"][0]["sell_for_recycling"] is True


def test_waste_ai_rejects_bad_vision_json_and_missing_items():
    bad_json_client = _make_fake_openai_client("not-json")
    with pytest.raises(ValueError, match="invalid JSON"):
        waste_ai.run("mô tả rác", model="vision-test", client=bad_json_client)

    missing_items_client = _make_fake_openai_client(json.dumps({"objects": []}))
    with pytest.raises(ValueError, match="items"):
        waste_ai.run("mô tả rác", model="vision-test", client=missing_items_client)

    with pytest.raises(ValueError):
        waste_ai.run("   ", model="vision-test", client=missing_items_client)


def test_waste_ai_timeout_forwarded_and_app_llm_fallback_contract(monkeypatch):
    from fastapi.testclient import TestClient

    seen = {}

    def fake_openai_run(text, model=None, system="", timeout=20.0, json_output=False, client=None, **extra):
        seen["timeout"] = timeout
        seen["json_output"] = json_output
        return {
            "output": json.dumps({
                "items": [
                    {"name_vi": "Pin tiểu", "item_key": "battery", "material": "Kim loại", "dirty_oily": False, "confidence": 0.9},
                    {"name_vi": "Vỏ chuối", "item_key": "food_waste", "material": "Hữu cơ", "dirty_oily": False, "confidence": 0.9},
                ]
            }),
            "tokens": 25,
            "source": "ai",
        }

    monkeypatch.setattr(waste_ai.openai_system_template, "run", fake_openai_run)
    monkeypatch.chdir(ROOT)
    monkeypatch.setenv("SYSTEM", "mypkg.waste_ai:run")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("TIMEOUT_S", "11")
    sys.modules.pop("serve.app_llm", None)
    app_mod = importlib.import_module("serve.app_llm")
    c = TestClient(app_mod.app)

    resp = c.post("/predict", json={"input": json.dumps({"prompt": "Rác gì?", "image": "data:image/jpeg;base64,AA", "json": True})}).json()
    assert resp["source"] == "ai"
    assert seen["timeout"] == 11.0
    assert seen["json_output"] is True
    out = json.loads(resp["output"])
    _assert_schema(out)
    assert out["mixed_bag"] is True and out["has_hazardous"] is True

    # Invalid Vision JSON must trigger fallback in serve/app_llm.py, never "ai"
    def bad_openai_run(*args, **kwargs):
        return {"output": '{"wrong_key": 1}', "tokens": 5, "source": "ai"}

    monkeypatch.setattr(waste_ai.openai_system_template, "run", bad_openai_run)
    resp_err = c.post("/predict", json={"input": "ảnh rác"}).json()
    assert resp_err["source"] == "fallback"
    assert resp_err["error"] == "ValueError"


def test_dirty_oily_string_coercion_and_oily_bag_flag():
    for false_val in ("false", "False", "0", "no", "không", "", None):
        res = waste_rules.evaluate_items([
            {"name_vi": "Túi nilon sạch", "item_key": "clean_plastic_bag", "material": "Nhựa", "dirty_oily": false_val}
        ])
        _assert_schema(res)
        it = res["items"][0]
        assert it["item_key"] == "clean_plastic_bag"
        assert it["dirty_oily"] is False
        assert it["group_id"] == "group_1_recyclable"

    for true_val in ("true", "1", "yes", "có"):
        res = waste_rules.evaluate_items([
            {"name_vi": "Túi nilon", "item_key": "clean_plastic_bag", "material": "Nhựa", "dirty_oily": true_val}
        ])
        _assert_schema(res)
        it = res["items"][0]
        assert it["item_key"] == "oily_plastic_bag"
        assert it["dirty_oily"] is True
        assert it["group_id"] == "group_3_other"

    res_oily_false = waste_rules.evaluate_items([
        {"name_vi": "Túi nilon dính dầu mỡ", "item_key": "oily_plastic_bag", "dirty_oily": False}
    ])
    assert res_oily_false["items"][0]["dirty_oily"] is True
    assert res_oily_false["items"][0]["group_id"] == "group_3_other"


def test_item_key_normalization_and_weird_field_types():
    res = waste_rules.evaluate_items([
        {"name_vi": None, "item_key": "Milk_Carton", "material": 123, "dirty_oily": "false", "confidence": "0.91"},
        {"name_vi": "   ", "item_key": "plastic-bottle", "material": None, "dirty_oily": 0, "confidence": None},
        {"name_vi": 999, "item_key": " battery ", "material": "Kim loại", "dirty_oily": False, "confidence": "high"},
    ])
    _assert_schema(res)
    assert res["items"][0]["item_key"] == "milk_carton"
    assert res["items"][0]["name_vi"] == "Vỏ hộp sữa giấy"
    assert res["items"][0]["material"] == ""
    assert res["items"][1]["item_key"] == "plastic_bottle"
    assert res["items"][1]["name_vi"] == "Chai nhựa"
    assert res["items"][2]["item_key"] == "battery"
    assert res["items"][2]["name_vi"] == "Pin thải"
    assert res["has_hazardous"] is True
    assert res["mixed_bag"] is True

    with pytest.raises(ValueError, match="dict"):
        waste_rules.evaluate_items([None])  # type: ignore[list-item]
    with pytest.raises(ValueError, match="list"):
        waste_rules.evaluate_items("not-a-list")  # type: ignore[arg-type]


def test_clean_cardboard_with_dirty_bottle_keeps_recyclable_speech():
    res = waste_rules.evaluate_items([
        {"name_vi": "Bìa carton sạch", "item_key": "cardboard_paper", "material": "Giấy", "dirty_oily": False},
        {"name_vi": "Chai nhựa còn nước ngọt", "item_key": "plastic_bottle", "material": "Nhựa", "dirty_oily": True},
    ])
    _assert_schema(res)
    assert res["mixed_bag"] is False
    assert "không tái chế được" not in res["speech_vi"].lower()


def test_waste_ai_parses_fenced_markdown_json_and_bom():
    fenced_payload = (
        "```json\n"
        + json.dumps({
            "items": [
                {
                    "name_vi": "Pin tiểu AA",
                    "item_key": "battery",
                    "material": "Kim loại",
                    "dirty_oily": False,
                    "confidence": "0.95",
                }
            ]
        }, ensure_ascii=False)
        + "\n```"
    )
    client = _make_fake_openai_client(fenced_payload)
    r = waste_ai.run(json.dumps({"prompt": "Pin gì?", "image": "data:image/jpeg;base64,AA", "json": True}), model="vision-test", client=client)
    assert r["source"] == "ai"
    out = json.loads(r["output"])
    _assert_schema(out)
    assert out["has_hazardous"] is True
    assert len(out["dropoff_summary"]) >= 1

    bom_prose_payload = (
        "\ufeffKết quả nhận diện:\n```\n"
        + json.dumps({"items": [{"name_vi": "Túi nilon", "item_key": "clean_plastic_bag", "dirty_oily": "true", "confidence": None}]}, ensure_ascii=False)
        + "\n```"
    )
    client2 = _make_fake_openai_client(bom_prose_payload)
    r2 = waste_ai.run("ảnh túi nilon", model="vision-test", client=client2)
    out2 = json.loads(r2["output"])
    _assert_schema(out2)
    assert out2["items"][0]["item_key"] == "oily_plastic_bag"
    assert out2["items"][0]["group_id"] == "group_3_other"

    bad_fenced = "```json\n{not-valid-json\n```"
    with pytest.raises(ValueError, match="invalid JSON"):
        waste_ai.run("ảnh rác", model="vision-test", client=_make_fake_openai_client(bad_fenced))


def test_all_rule_keys_satisfy_typescript_waste_result_contract():
    rules = waste_rules.load_rules()
    for key in rules["item_rules"]:
        res = waste_rules.evaluate_items([{"item_key": key}], rules=rules)
        _assert_schema(res)
        it = res["items"][0]
        assert isinstance(it["name_vi"], str) and it["name_vi"].strip()
        assert isinstance(it["group_id"], str) and it["group_id"].strip()
        assert isinstance(it["group_name_vi"], str) and it["group_name_vi"].strip()
        assert isinstance(it["group_short_label"], str) and it["group_short_label"].strip()
        assert isinstance(it["is_hazardous"], bool)
        for pt in it["dropoff_points"]:
            assert isinstance(pt, dict)
            assert isinstance(pt.get("name"), str) and pt["name"].strip()


class _FakeGeminiUsage:
    def __init__(self, total_tokens: int):
        self.total_tokens = total_tokens


class _FakeGeminiInteraction:
    def __init__(self, output_text: str, status: str = "completed", total_tokens: int = 33):
        self.output_text = output_text
        self.status = status
        self.usage = _FakeGeminiUsage(total_tokens)


class _FakeGeminiClient:
    def __init__(self, output_text: str, status: str = "completed"):
        self.calls: list[dict] = []
        self._output_text = output_text
        self._status = status
        self.interactions = self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeGeminiInteraction(self._output_text, status=self._status)


def test_waste_ai_gemini_interactions_client_and_schema():
    vision_json = json.dumps({
        "items": [
            {
                "name_vi": "Vỏ hộp sữa giấy",
                "item_key": "milk_carton",
                "material": "Giấy tráng nhôm",
                "dirty_oily": False,
                "confidence": 0.94,
            }
        ]
    }, ensure_ascii=False)
    fake_client = _FakeGeminiClient(vision_json)
    payload = json.dumps({"prompt": "Phân loại rác", "image": "data:image/jpeg;base64,/9j/4AAQ", "json": True})

    res = waste_ai.run(payload, timeout=14.0, client=fake_client)
    n = normalize(res)
    assert n["ok"] is True
    assert n["source"] == "ai"
    assert n["tokens"] == 33

    call = fake_client.calls[0]
    assert call["model"] == "gemini-3.8-flash"
    assert call["store"] is False
    assert call["timeout"] == 14.0
    assert call["response_format"]["type"] == "text"
    assert call["response_format"]["mime_type"] == "application/json"
    assert call["input"][1] == {"type": "image", "data": "/9j/4AAQ", "mime_type": "image/jpeg"}

    evaluated = json.loads(n["output"])
    _assert_schema(evaluated)
    assert evaluated["items"][0]["item_key"] == "milk_carton"
    assert evaluated["items"][0]["rinse_required"] is True


def test_waste_ai_provider_resolution_and_gemini_errors(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    assert waste_ai.resolve_provider() == "gemini"

    monkeypatch.setenv("LLM_PROVIDER", "openai")
    assert waste_ai.resolve_provider() == "openai"

    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    assert waste_ai.resolve_provider(model="gemini-3.8-flash") == "gemini"

    failed_client = _FakeGeminiClient("", status="failed")
    with pytest.raises(RuntimeError, match="failed"):
        waste_ai.run("mô tả rác", client=failed_client)

    empty_client = _FakeGeminiClient("   ", status="completed")
    with pytest.raises(RuntimeError, match="rỗng"):
        waste_ai.run("mô tả rác", client=empty_client)


def test_gemini_api_key_reads_local_dotenv_fallback(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("# comment\nGEMINI_API_KEY='demo-local-key'\n", encoding="utf-8")
    assert waste_ai.gemini_vision.get_gemini_api_key(env_path=env_file) == "demo-local-key"

    bom_env = tmp_path / ".env.bom"
    bom_env.write_bytes("\ufeffGEMINI_API_KEY=bom-local-key\n".encode("utf-8"))
    assert waste_ai.gemini_vision.get_gemini_api_key(env_path=bom_env) == "bom-local-key"

