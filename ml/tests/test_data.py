import pytest

np = pytest.importorskip("numpy")
Image = pytest.importorskip("PIL.Image")

from mlkit import data


def items(n_per_class=10, classes=("a", "b"), prefix=""):
    return [(f"{c}/{prefix}{c}{i}.png", ci) for ci, c in enumerate(classes) for i in range(n_per_class)]


def test_split_covers_everything_once_and_is_stratified():
    it = items(20)
    s = data.make_split(it, seed=1)
    all_paths = s["train"] + s["val"] + s["test"]
    assert sorted(all_paths) == sorted(p for p, _ in it)
    assert len(set(all_paths)) == len(all_paths)
    for name in s:
        assert {p.split("/")[0] for p in s[name]} == {"a", "b"}  # mỗi tập có đủ lớp


def test_split_is_deterministic_and_seed_changes_it():
    it = items(20)
    assert data.make_split(it, seed=1) == data.make_split(it, seed=1)
    assert data.make_split(it, seed=1) != data.make_split(it, seed=2)


def test_groups_stay_together():
    it = [(f"a/vid{v}_frame{f}.png", 0) for v in range(8) for f in range(5)] + [(f"b/vid{v}_frame{f}.png", 1) for v in range(8, 16) for f in range(5)]
    rx = r"^(vid\d+)_frame"
    s = data.make_split(it, seed=3, group_regex=rx)
    assert data.find_leaks(s, group_regex=rx) == []
    owner = {}
    for name, ps in s.items():
        for p in ps:
            assert owner.setdefault(data.group_of(p, rx), name) == name


def test_too_few_groups_raises():
    with pytest.raises(ValueError):
        data.make_split(items(2), seed=0)


def test_find_leaks_detects_path_overlap_and_group_split():
    bad = {"train": ["a/x_1.png", "a/y_1.png"], "val": ["a/x_2.png"], "test": ["a/y_1.png"]}
    msgs = data.find_leaks(bad, group_regex=r"^(\w)_\d")
    assert any("nằm ở cả" in m for m in msgs)
    assert any("Nhóm" in m for m in msgs)


def test_find_leaks_detects_duplicate_content(tmp_path):
    (tmp_path / "a").mkdir()
    img = Image.fromarray(np.full((8, 8, 3), 7, dtype="uint8"))
    img.save(tmp_path / "a" / "one.png")
    img.save(tmp_path / "a" / "copy.png")  # cùng nội dung, khác tên
    s = {"train": ["a/one.png"], "val": ["a/copy.png"], "test": []}
    assert any("Nội dung trùng" in m for m in data.find_leaks(s, tmp_path))


def test_prepare_freezes_split(tmp_path):
    for c in ("a", "b"):
        (tmp_path / "d" / c).mkdir(parents=True)
        for i in range(10):
            Image.fromarray(np.full((8, 8, 3), i * 10 + (c == "b") * 100, dtype="uint8")).save(tmp_path / "d" / c / f"{i}.png")
    cfg = {"data_dir": str(tmp_path / "d"), "split_file": str(tmp_path / "split.json"), "ratios": [0.6, 0.2, 0.2], "seed": 0}
    _, s1 = data.prepare(cfg)
    cfg["seed"] = 99  # đổi seed không được làm đổi cách chia đã đóng băng
    _, s2 = data.prepare(cfg)
    assert s1 == s2
