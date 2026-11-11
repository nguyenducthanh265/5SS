import importlib
import json
import sys

import pytest

from mlkit import runs
from mlkit.result import normalize


@pytest.mark.parametrize("raw,ok,src", [
    ("đáp án", True, "ai"),
    ({"output": "đáp án", "tokens": 3}, True, "ai"),
    ({"output": "đáp án", "source": "ai"}, True, "ai"),
    ({"output": "câu mẫu", "source": "fallback", "error": "provider_down"}, False, "fallback"),
    ({"output": "câu mẫu", "source": "fallback"}, False, "fallback"),
    ({"output": "x", "error": "boom"}, False, "error"),
    ({"output": "   "}, False, "invalid"),
    ("", False, "invalid"),
    ({"output": 5}, False, "invalid"),
    ({"text": "thiếu output"}, False, "invalid"),
    (None, False, "invalid"),
])
def test_normalize(raw, ok, src):
    n = normalize(raw)
    assert n["ok"] is ok and n["source"] == src
    assert (n["error"] is None) == ok


@pytest.fixture()
def api(monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("SYSTEM", "examples.toy_system:run")
    sys.modules.pop("serve.app_llm", None)
    m = importlib.import_module("serve.app_llm")
    return m, TestClient(m.app)


@pytest.mark.parametrize("ret", [
    {"output": "câu mẫu", "source": "fallback", "error": "provider_down"},
    {"output": "câu mẫu", "source": "fallback"},
    {"output": "x", "error": "boom"},
    {"output": ""},
    {"output": None},
    42,
])
def test_api_never_relabels_failure_as_ai(api, ret):
    """Lỗi đã báo: dict fallback từ hệ thống bị API đổi thành source=ai."""
    m, c = api
    m.system = lambda x: ret
    r = c.post("/predict", json={"input": "a"}).json()
    assert r["source"] == "fallback" and r["error"]


def test_api_calls_system_exactly_once_on_typeerror(api):
    """Lỗi đã báo: TypeError trong thân hàm làm hệ thống bị gọi lại không timeout."""
    m, c = api
    calls = []
    def f(x, timeout=None):
        calls.append(timeout)
        raise TypeError("lỗi trong công việc thật")
    m.system = f
    r = c.post("/predict", json={"input": "a"}).json()
    assert calls == [m.TIMEOUT_S]
    assert r["source"] == "fallback" and r["error"] == "TypeError"
    calls.clear()
    def g(x, timeout=None):
        calls.append(timeout); raise ValueError("v")
    m.system = g
    assert c.post("/predict", json={"input": "a"}).json()["error"] == "ValueError" and calls == [m.TIMEOUT_S]


def test_api_passes_timeout_to_kwargs_systems_and_not_to_plain(api):
    m, c = api
    seen = []
    m.system = lambda x, **kw: seen.append(kw) or "ok"
    c.post("/predict", json={"input": "a"})
    m.system = lambda x: seen.append("plain") or "ok"
    c.post("/predict", json={"input": "a"})
    assert seen == [{"timeout": m.TIMEOUT_S}, "plain"]


def _cfg(tmp_path, system, **kw):
    ds = tmp_path / "d.jsonl"
    ds.write_text("\n".join(json.dumps({"id": f"i{i}", "input": f"câu {i}", "expected": f"ĐÁP {i}"}, ensure_ascii=False) for i in range(30)), encoding="utf-8")
    c = {"dataset": str(ds), "system": system, "params": {}, "scorer": "contains", "judge": None, "normalize": True, "dev_ratio": 0.7,
         "pass_threshold": 1.0, "workers": 2, "retries": 2, "cache_dir": str(tmp_path / "cache"), "seed": 0, "runs_dir": str(tmp_path / "runs"), "tag": "t"}
    c.update(kw)
    return c


CALLS = []


def fallback_sys(text, **kw):
    CALLS.append(text)
    return {"output": f"ĐÁP {text.split()[-1]}", "source": "fallback", "error": "provider_down"}  # câu mẫu trùng đáp án


def test_llm_eval_scores_system_fallback_as_failure_and_does_not_cache_or_retry(tmp_path):
    from mlkit.tasks import llm_eval
    CALLS.clear()
    out = llm_eval.train(_cfg(tmp_path, f"{__name__}:fallback_sys"))
    v = runs.load_json(out / "metrics.json")["val"]
    assert v["score"] == 0.0 and v["failures"] == v["n"]
    n = len(CALLS)
    assert n == v["n"]  # không thử lại kết quả fallback
    llm_eval.train(_cfg(tmp_path, f"{__name__}:fallback_sys", tag="again"))
    assert len(CALLS) == 2 * n  # không cache kết quả thất bại


def ok_sys(text, **kw):
    CALLS.append(text)
    return f"ĐÁP {text.split()[-1]}"


def test_cache_write_failure_does_not_call_system_again(tmp_path):
    from mlkit.tasks import llm_eval
    CALLS.clear()
    blocker = tmp_path / "cache"
    blocker.write_text("tôi là file, không phải thư mục", encoding="utf-8")  # mkdir sẽ lỗi
    out = llm_eval.train(_cfg(tmp_path, f"{__name__}:ok_sys"))
    v = runs.load_json(out / "metrics.json")["val"]
    assert v["score"] == 1.0 and len(CALLS) == v["n"]


def bad_judge(inp, out, exp):
    raise RuntimeError("judge API down")


def test_judge_errors_are_counted_not_crashing(tmp_path):
    from mlkit.tasks import llm_eval
    out = llm_eval.train(_cfg(tmp_path, f"{__name__}:ok_sys", scorer="judge", judge=f"{__name__}:bad_judge"))
    v = runs.load_json(out / "metrics.json")["val"]
    assert v["judge_errors"] == v["n"] and v["score"] == 0.0
    assert "judge_error" in (out / "val_errors.csv").read_text(encoding="utf-8")


def test_cache_written_by_old_kit_version_is_never_reused(tmp_path):
    """Lỗi đã báo: cache do kit bản trước ghi (lưu kết quả fallback như thành công, không có source/schema)
    được bản mới đọc lại và chấm 1.0. Ghi record đúng ĐỊNH DẠNG và ĐÚNG ĐƯỜNG DẪN của bản cũ rồi kiểm tra."""
    import hashlib
    from mlkit.tasks import llm_eval
    CALLS.clear()
    cfg = _cfg(tmp_path, f"{__name__}:fallback_sys")
    llm_eval.load_system(cfg)  # tính _fp như lúc train
    items = [json.loads(l) for l in open(cfg["dataset"], encoding="utf-8")]
    (tmp_path / "cache").mkdir()
    for it in items:  # khóa và định dạng của bản cũ: sha256(f"{fp}|{input}"), {"output","tokens","latency_ms","error": null}
        old_key = hashlib.sha256(f"{cfg['_fp']}|{it['input']}".encode()).hexdigest()
        (tmp_path / "cache" / f"{old_key}.json").write_text(
            json.dumps({"output": it["expected"], "tokens": 0, "latency_ms": 1.0, "error": None}, ensure_ascii=False), encoding="utf-8")
    out = llm_eval.train(_cfg(tmp_path, f"{__name__}:fallback_sys"))
    v = runs.load_json(out / "metrics.json")["val"]
    assert v["cached"] == 0 and v["score"] == 0.0 and v["failures"] == v["n"] and len(CALLS) == v["n"]


@pytest.mark.parametrize("rec", [
    {"output": "ĐÁP 1", "tokens": 0, "error": None},                                  # thiếu schema (bản cũ)
    {"schema": 1, "output": "ĐÁP 1", "error": None, "source": "ai"},                 # schema cũ
    {"schema": 2, "output": "ĐÁP 1", "error": "provider_down", "source": "fallback"},  # đúng schema nhưng là lỗi
    {"schema": 2, "output": "ĐÁP 1", "error": None},                                 # thiếu source
    {"schema": 2, "output": "", "error": None, "source": "ai"},                      # rỗng
    "không phải dict",
])
def test_invalid_cache_records_are_misses(rec):
    from mlkit.tasks import llm_eval
    assert llm_eval.valid_cached(rec) is None


def test_valid_current_cache_record_is_a_hit():
    from mlkit.tasks import llm_eval
    hit = llm_eval.valid_cached({"schema": llm_eval.CACHE_SCHEMA, "output": "ĐÁP 1", "tokens": 3, "latency_ms": 5, "error": None, "source": "ai"})
    assert hit["cached"] and hit["source"] == "ai" and hit["output"] == "ĐÁP 1"
