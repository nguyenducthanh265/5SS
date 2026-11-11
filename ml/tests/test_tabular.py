import pytest

np = pytest.importorskip("numpy")
pd = pytest.importorskip("pandas")
for _m in ("sklearn", "joblib"):
    pytest.importorskip(_m)

from mlkit import runs
from mlkit.tasks import tabular


def cfg_for(tmp_path, csv, **kw):
    base = {"csv": str(csv), "target": "y", "task": "auto", "group_col": None, "drop_cols": [], "text_cols": [], "model": "logreg",
            "class_weights": "none", "ratios": [0.6, 0.2, 0.2], "split_file": str(tmp_path / "split.json"), "seed": 0,
            "runs_dir": str(tmp_path / "runs"), "tag": "t"}
    base.update(kw)
    return base


def make_df(n=400, seed=0):
    rng = np.random.default_rng(seed)
    x1, x2 = rng.normal(size=n), rng.normal(size=n)
    cat = rng.choice(["a", "b", "c"], n)
    y = (x1 + 0.5 * x2 + rng.normal(0, 0.5, n) > 0).astype(int)
    return pd.DataFrame({"x1": x1, "x2": x2, "cat": cat, "subject": rng.integers(0, 40, n), "y": y})


def test_classification_beats_baseline_and_test_is_locked(tmp_path):
    p = tmp_path / "d.csv"
    make_df().to_csv(p, index=False)
    out = tabular.train(cfg_for(tmp_path, p, model="hgb"))
    m = runs.load_json(out / "metrics.json")
    assert m["primary"] == "macro_f1" and m["val"]["macro_f1"] > m["baseline_val"]["macro_f1"] + 0.2
    tabular.evaluate(out, "val")
    tabular.evaluate(out, "test")
    assert (out / "test_errors.csv").exists() and (out / "importance.csv").exists()
    with pytest.raises(SystemExit):
        tabular.evaluate(out, "test")  # test chỉ mở một lần


def test_group_col_keeps_groups_apart_and_split_is_frozen(tmp_path):
    p = tmp_path / "d.csv"
    df = make_df()
    df.to_csv(p, index=False)
    out = tabular.train(cfg_for(tmp_path, p, group_col="subject"))
    cfg = runs.load_json(out / "config.json")
    from mlkit import data
    _, split = data.load_split(cfg["split_file"])
    owner = {}
    for name, idx in split.items():
        for i in idx:
            assert owner.setdefault(int(df.subject[int(i)]), name) == name
    tabular.train(cfg_for(tmp_path, p, group_col="subject", seed=99))  # seed khác, split vẫn đóng băng
    assert data.load_split(cfg["split_file"])[1] == split


def test_duplicate_rows_across_splits_are_rejected(tmp_path):
    df = make_df(200)
    df = pd.concat([df, df], ignore_index=True)  # mỗi dòng xuất hiện hai lần -> chắc chắn rơi vào hai tập khác nhau
    p = tmp_path / "d.csv"
    df.to_csv(p, index=False)
    with pytest.raises(SystemExit, match="RÒ RỈ"):
        tabular.train(cfg_for(tmp_path, p))


def test_label_leak_column_warns(tmp_path, capsys):
    df = make_df()
    df["leak"] = df["y"] * 2.0 + np.random.default_rng(1).normal(0, 0.01, len(df))
    p = tmp_path / "d.csv"
    df.to_csv(p, index=False)
    tabular.train(cfg_for(tmp_path, p))
    assert "rò rỉ nhãn" in capsys.readouterr().out


def test_regression_uses_rmse_and_beats_mean_baseline(tmp_path):
    rng = np.random.default_rng(2)
    x = rng.normal(size=(500, 2))
    df = pd.DataFrame({"x1": x[:, 0], "x2": x[:, 1], "y": 3 * x[:, 0] - x[:, 1] + rng.normal(0, 0.3, 500)})
    p = tmp_path / "d.csv"
    df.to_csv(p, index=False)
    out = tabular.train(cfg_for(tmp_path, p, model="ridge", task="regression"))
    m = runs.load_json(out / "metrics.json")
    assert m["primary"] == "rmse" and m["higher_is_better"] is False
    assert m["val"]["rmse"] < 0.5 * m["baseline_val"]["rmse"]


def test_text_column_tfidf(tmp_path):
    rng = np.random.default_rng(3)
    pos, neg = ["tuyệt vời", "rất tốt", "thích"], ["tệ hại", "rất dở", "chán"]
    rows = [(f"{rng.choice(pos if k else neg)} sản phẩm số {i}", k) for i, k in enumerate(rng.integers(0, 2, 300))]
    p = tmp_path / "d.csv"
    pd.DataFrame(rows, columns=["text", "y"]).to_csv(p, index=False)
    out = tabular.train(cfg_for(tmp_path, p, text_cols=["text"]))
    assert runs.load_json(out / "metrics.json")["val"]["macro_f1"] > 0.9
    with pytest.raises(SystemExit, match="logreg/ridge"):
        tabular.train(cfg_for(tmp_path, p, text_cols=["text"], model="rf", split_file=str(tmp_path / "s2.json")))
