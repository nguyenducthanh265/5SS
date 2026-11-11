import json

import pytest

from mlkit import runs
from mlkit.tasks import llm_eval

CALLS = []


def good(text, **kw):
    CALLS.append(text)
    return {"output": f"đáp án: ĐÁP {text.split()[-1]}", "tokens": 3}


def flaky(text, **kw):
    if text.endswith("0"):
        raise RuntimeError("API timeout")
    return f"ĐÁP {text.split()[-1]}"


def make_cfg(tmp_path, system, **kw):
    ds = tmp_path / "d.jsonl"
    ds.write_text("\n".join(json.dumps({"id": f"i{i}", "input": f"câu {i}", "expected": f"ĐÁP {i}"}, ensure_ascii=False) for i in range(60)), encoding="utf-8")
    cfg = {"dataset": str(ds), "system": system, "params": {}, "scorer": "contains", "judge": None, "normalize": True, "dev_ratio": 0.7,
           "pass_threshold": 1.0, "workers": 4, "retries": 1, "cache_dir": str(tmp_path / "cache"), "seed": 0, "runs_dir": str(tmp_path / "runs"), "tag": "t"}
    cfg.update(kw)
    return cfg


def test_scorers():
    s = llm_eval.score_one
    assert s("exact", "Hà Nội!", "hà nội") == 1.0 and s("exact", "Thủ đô Hà Nội", "hà nội") == 0.0
    assert s("contains", "Thủ đô là Hà Nội.", ["Paris", "hà nội"]) == 1.0
    assert s("regex", "abc 123", r"\d+") == 1.0
    assert 0.0 < s("f1", "the cat sat", "the cat ran") < 1.0 and s("f1", "xyz", "abc") == 0.0
    assert s("judge", "x", "y", {"input": "q"}, judge=lambda i, o, e: 0.5) == 0.5


def test_split_is_stable_disjoint_and_order_independent():
    items = [{"id": f"x{i}", "input": f"câu hỏi số {i}", "expected": ""} for i in range(200)]
    cfg = {"dev_ratio": 0.7, "seed": 0}
    a = llm_eval.split_items(items, cfg)
    b = llm_eval.split_items(list(reversed(items)), cfg)
    assert {i["id"] for i in a["val"]} == {i["id"] for i in b["val"]}
    assert not {i["id"] for i in a["val"]} & {i["id"] for i in a["test"]}
    assert 100 < len(a["val"]) < 170


def test_train_beats_echo_baseline_and_caches(tmp_path):
    CALLS.clear()
    out = llm_eval.train(make_cfg(tmp_path, f"{__name__}:good"))
    m = runs.load_json(out / "metrics.json")
    assert m["primary"] == "score" and m["val"]["score"] == 1.0 and m["val"]["score"] > m["baseline_val"]["score"]
    n_first = len(CALLS)
    llm_eval.train(make_cfg(tmp_path, f"{__name__}:good", tag="again"))
    assert len(CALLS) == n_first  # lần hai lấy từ cache, không gọi lại hệ thống


def test_failures_score_zero_and_are_counted(tmp_path):
    out = llm_eval.train(make_cfg(tmp_path, f"{__name__}:flaky", retries=0))
    m = runs.load_json(out / "metrics.json")["val"]
    assert m["failures"] > 0 and m["score"] < 1.0
    assert "API timeout" in (out / "val_errors.csv").read_text(encoding="utf-8")


def test_test_split_is_opened_once(tmp_path):
    out = llm_eval.train(make_cfg(tmp_path, f"{__name__}:good"))
    llm_eval.evaluate(out, "test")
    assert (out / "test_results.jsonl").exists()
    with pytest.raises(SystemExit):
        llm_eval.evaluate(out, "test")


def test_duplicate_ids_rejected(tmp_path):
    ds = tmp_path / "d.jsonl"
    ds.write_text('{"id":"a","input":"x","expected":"y"}\n{"id":"a","input":"x2","expected":"y"}', encoding="utf-8")
    with pytest.raises(SystemExit):
        llm_eval.load_dataset(ds)


def test_judge_scorer_requires_judge(tmp_path):
    with pytest.raises(SystemExit, match="judge"):
        llm_eval.train(make_cfg(tmp_path, f"{__name__}:good", scorer="judge"))


def test_example_pipeline_runs(tmp_path, monkeypatch):
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    monkeypatch.chdir(root)
    from mlkit.tasks.common import load_config
    c = load_config(root / "configs/llm_eval.yaml", [f"runs_dir={tmp_path}/runs", f"cache_dir={tmp_path}/cache"])
    out = llm_eval.train(c)
    assert 0 < runs.load_json(out / "metrics.json")["val"]["score"] < 1  # toy_system cố tình sai câu về Ý


def test_same_content_different_id_stays_in_one_split():
    items = [{"id": f"d{i}", "input": "Cùng một câu hỏi?", "expected": "x"} for i in range(100)]
    p = llm_eval.split_items(items, {"dev_ratio": 0.7, "seed": 0})
    assert (len(p["val"]), len(p["test"])) in ((100, 0), (0, 100))
    assert llm_eval.duplicate_report(items) == 99


def test_group_field_overrides_content(tmp_path):
    a = [{"id": "a", "input": "q1", "expected": "x", "group": "g"}, {"id": "b", "input": "q2", "expected": "x", "group": "g"}]
    p = llm_eval.split_items(a, {"dev_ratio": 0.5, "seed": 3})
    assert len(p["val"]) in (0, 2)


def test_cache_invalidates_when_system_code_changes(tmp_path):
    mod = tmp_path / "sysmod_x.py"
    mod.write_text("def run(t, **k):\n    return 'ĐÁP old'\n", encoding="utf-8")
    import sys
    sys.path.insert(0, str(tmp_path))
    try:
        cfg1 = make_cfg(tmp_path, "sysmod_x:run")
        o1 = llm_eval.train(cfg1)
        assert runs.load_json(o1 / "metrics.json")["val"]["cached"] == 0
        mod.write_text("def run(t, **k):\n    return 'ĐÁP brand-new'\n", encoding="utf-8")
        import importlib
        importlib.invalidate_caches(); sys.modules.pop("sysmod_x", None)
        o2 = llm_eval.train(make_cfg(tmp_path, "sysmod_x:run", tag="v2"))
        r = [json.loads(l) for l in (o2 / "val_results.jsonl").read_text(encoding="utf-8").splitlines()]
        assert all(x["output"] == "ĐÁP brand-new" and not x.get("cached") for x in r)
    finally:
        sys.path.remove(str(tmp_path)); sys.modules.pop("sysmod_x", None)


def test_system_version_and_no_cache(tmp_path):
    CALLS.clear()
    llm_eval.train(make_cfg(tmp_path, f"{__name__}:good"))
    n = len(CALLS)
    llm_eval.train(make_cfg(tmp_path, f"{__name__}:good", system_version="v2"))
    assert len(CALLS) == 2 * n  # đổi system_version -> không dùng cache cũ
    llm_eval.train(make_cfg(tmp_path, f"{__name__}:good", system_version="v2", cache=False))
    assert len(CALLS) == 3 * n


def test_tokens_split_fresh_vs_cached(tmp_path):
    llm_eval.train(make_cfg(tmp_path, f"{__name__}:good"))
    o = llm_eval.train(make_cfg(tmp_path, f"{__name__}:good", tag="again"))
    v = runs.load_json(o / "metrics.json")["val"]
    assert v["tokens_total"] == 0 and v["tokens_reused_from_cache"] > 0


def test_evaluate_refuses_after_dataset_or_system_changed(tmp_path):
    cfg = make_cfg(tmp_path, f"{__name__}:good")
    o = llm_eval.train(cfg)
    open(cfg["dataset"], "a", encoding="utf-8").write("\n" + json.dumps({"id": "new", "input": "mới", "expected": "x"}))
    with pytest.raises(SystemExit, match="Dataset"):
        llm_eval.evaluate(o, "test")


def test_second_run_opening_test_warns_and_strict_blocks(tmp_path, capsys, monkeypatch):
    o1 = llm_eval.train(make_cfg(tmp_path, f"{__name__}:good", tag="a"))
    o2 = llm_eval.train(make_cfg(tmp_path, f"{__name__}:good", tag="b"))
    llm_eval.evaluate(o1, "test")
    llm_eval.evaluate(o2, "test")
    assert "CẢNH BÁO" in capsys.readouterr().out
    o3 = llm_eval.train(make_cfg(tmp_path, f"{__name__}:good", tag="c"))
    monkeypatch.setenv("MLKIT_TEST_POLICY", "strict")
    with pytest.raises(SystemExit, match="strict"):
        llm_eval.evaluate(o3, "test")


def test_same_content_different_groups_stays_in_one_split():
    """Lỗi đã báo: 100 dòng cùng input, mỗi dòng một group, bị chia 68/32."""
    items = [{"id": f"d{i}", "input": "Cùng một câu hỏi?", "expected": "x", "group": f"g{i}"} for i in range(100)]
    p = llm_eval.split_items(items, {"dev_ratio": 0.7, "seed": 0})
    assert (len(p["val"]), len(p["test"])) in ((100, 0), (0, 100))
    assert llm_eval.duplicate_report(items) == 99


def test_group_and_content_constraints_hold_together():
    import random
    rng = random.Random(1)
    items = [{"id": f"i{i}", "input": f"q{rng.randrange(150)}", "expected": "x", "group": f"g{rng.randrange(120)}"} for i in range(400)]
    p = llm_eval.split_items(items, {"dev_ratio": 0.7, "seed": 0})
    side = {it["id"]: name for name in ("val", "test") for it in p[name]}
    for field in ("input", "group"):
        where = {}
        for it in items:
            where.setdefault(it[field], set()).add(side[it["id"]])
        assert all(len(v) == 1 for v in where.values()), field
    shuffled = items[:]; rng.shuffle(shuffled)
    q = llm_eval.split_items(shuffled, {"dev_ratio": 0.7, "seed": 0})
    assert {i["id"] for i in q["val"]} == {i["id"] for i in p["val"]}
