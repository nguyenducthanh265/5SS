import pytest

np = pytest.importorskip("numpy")
for _m in ("sklearn", "joblib", "yaml"):  # phần train: requirements.txt
    pytest.importorskip(_m)

from mlkit import data, runs
from mlkit.tasks import biosignal as signal


def make_npz(path, n_subj=30, per=20, fs=100, T=200, seed=0):
    """Lớp 0: sóng 5 Hz, lớp 1: sóng 20 Hz; mỗi đối tượng có độ lệch biên độ/offset riêng."""
    rng = np.random.default_rng(seed)
    t = np.arange(T) / fs
    X, y, s = [], [], []
    for sid in range(n_subj):
        amp, off = rng.uniform(0.5, 3), rng.normal(0, 2)
        for k in range(per):
            label = k % 2
            f = 5 if label == 0 else 20
            X.append(np.stack([amp * np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) + off + rng.normal(0, 0.5, T) for _ in range(2)]))
            y.append(label)
            s.append(f"s{sid}")
    np.savez(path, X=np.array(X, dtype=np.float32), y=np.array(y), subject=np.array(s))


def cfg_for(tmp_path, **kw):
    base = {"npz": str(tmp_path / "w.npz"), "classes": ["a", "b"], "fs": 100, "model": "logreg", "class_weights": "none", "epochs": 6,
            "batch_size": 32, "lr": 0.003, "patience": 3, "ratios": [0.6, 0.2, 0.2], "split_file": str(tmp_path / "split.json"),
            "seed": 0, "runs_dir": str(tmp_path / "runs"), "tag": "t"}
    base.update(kw)
    return base


def test_make_windows_shapes():
    w = signal.make_windows(np.zeros((3, 1000)), 200, 100)
    assert w.shape == (9, 3, 200)
    assert signal.make_windows(np.zeros((3, 50)), 200, 100).shape == (0, 3, 200)


def test_features_separate_frequencies():
    t = np.arange(200) / 100
    slow = np.sin(2 * np.pi * 5 * t)[None, None]  # theta/alpha thấp
    fast = np.sin(2 * np.pi * 20 * t)[None, None]  # beta
    names = list(signal.BANDS)
    f_slow, f_fast = signal.features(slow, 100)[0], signal.features(fast, 100)[0]
    k = 4  # 4 khối thống kê đầu, sau đó là các băng tần
    assert f_slow[k + names.index("theta")] > 0.9 and f_fast[k + names.index("beta")] > 0.9


def test_zscore_uses_only_given_stats():
    tr = np.random.default_rng(0).normal(5, 2, (50, 2, 100))
    stats = signal.zscore_fit(tr)
    z = signal.zscore_apply(tr, stats)
    assert abs(z.mean()) < 1e-6 and abs(z.std() - 1) < 1e-3


def test_subject_independent_split_and_features_beat_baseline(tmp_path):
    make_npz(tmp_path / "w.npz")
    out = signal.train(cfg_for(tmp_path))
    m = runs.load_json(out / "metrics.json")
    assert m["val"]["macro_f1"] > 0.95 > m["baseline_val"]["macro_f1"] + 0.3 and "auroc" in m["val"]
    _, split = data.load_split(tmp_path / "split.json")
    d = np.load(tmp_path / "w.npz")
    owner = {}
    for name, idx in split.items():
        for i in idx:
            assert owner.setdefault(str(d["subject"][int(i)]), name) == name  # không đối tượng nào ở hai tập
    signal.evaluate(out, "val")
    signal.evaluate(out, "test")
    assert (out / "test_by_subject.csv").exists()
    with pytest.raises(SystemExit):
        signal.evaluate(out, "test")


def test_leak_is_caught_when_split_file_is_tampered(tmp_path):
    make_npz(tmp_path / "w.npz")
    signal.train(cfg_for(tmp_path))
    classes, split = data.load_split(tmp_path / "split.json")
    split["val"].append(split["train"][0])  # cố tình để một cửa sổ train lọt vào val
    data.save_split(split, classes, tmp_path / "split.json")
    with pytest.raises(SystemExit, match="RÒ RỈ"):
        signal.train(cfg_for(tmp_path, tag="again"))


def test_cnn_trains_and_predicts(tmp_path):
    pytest.importorskip("torch")
    make_npz(tmp_path / "w.npz", n_subj=20, per=16)
    out = signal.train(cfg_for(tmp_path, model="cnn"))
    assert runs.load_json(out / "metrics.json")["val"]["macro_f1"] > 0.8
    signal.evaluate(out, "val")
