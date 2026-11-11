from mlkit import report, runs


def fake_run(base, name, f1, test=None):
    d = base / name
    d.mkdir(parents=True)
    runs.save_json({"backbone": "resnet18", "augment": "basic", "lr": 0.001}, d / "config.json")
    runs.save_json({"val": {"accuracy": f1, "macro_f1": f1}, "baseline_val": {"macro_f1": 0.2}, "history": [1, 2, 3],
                    "params_m": 11.2, "train_seconds": 123.4}, d / "metrics.json")
    if test is not None:
        runs.save_json({"macro_f1": test}, d / "test_metrics.json")


def test_report_sorts_by_val_f1_and_shows_test_only_when_present(tmp_path):
    fake_run(tmp_path, "r1", 0.70)
    fake_run(tmp_path, "r2", 0.90, test=0.88)
    rows = report.collect(tmp_path)
    assert [r["run"] for r in rows] == ["r2", "r1"]
    text = report.render(rows)
    assert "0.880" in text and "Baseline" in text
    assert text.count("| - |") >= 1  # r1 chưa có test


def test_empty_report(tmp_path):
    assert "Chưa có run" in report.render(report.collect(tmp_path))


def test_mixed_tasks_sorted_by_direction(tmp_path):
    def run(name, task, prim, higher, v, base):
        d = tmp_path / name
        d.mkdir()
        runs.save_json({"task": task, "model": name}, d / "config.json")
        runs.save_json({"primary": prim, "higher_is_better": higher, "val": {prim: v}, "baseline_val": {prim: base}, "history": [],
                        "params_m": None, "train_seconds": 1.0}, d / "metrics.json")
    run("a", "tabular", "rmse", False, 0.50, 1.2)
    run("b", "tabular", "rmse", False, 0.30, 1.2)
    run("c", "llm_eval", "score", True, 0.6, 0.1)
    run("d", "llm_eval", "score", True, 0.8, 0.1)
    rows = report.collect(tmp_path)
    by_metric = {}
    for r in rows:
        by_metric.setdefault(r["metric"], []).append(r["run"])
    assert by_metric == {"rmse": ["b", "a"], "score": ["d", "c"]}  # rmse thấp hơn là tốt hơn; score cao hơn là tốt hơn
    assert "llm_eval" in report.render(rows)


def test_new_run_dir_never_collides(tmp_path):
    dirs = {runs.new_run_dir(tmp_path, "t", "m") for _ in range(5)}
    assert len(dirs) == 5
