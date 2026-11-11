"""Đánh giá LLM / agent / RAG / prompt như một thí nghiệm có đối chứng (không cần torch).

Hệ thống cần đánh giá là một hàm Python `module:function(input: str, **params) -> str | {"output": str, "tokens": int, "source"?, "error"?}`
(hợp đồng đầy đủ: mlkit/result.py; trả fallback/error thì bị chấm 0 và đếm là lỗi, không bao giờ tính là AI).
Hàm đó có thể gọi API LLM, chạy agent hay pipeline RAG; framework lo chia dev/test, cache, thử lại, chấm điểm, ghi lại và so baseline.

  python -m mlkit.tasks.llm_eval train --config configs/llm_eval.yaml [--set system=my_pkg.mod:run tag=prompt-v2]
  python -m mlkit.tasks.llm_eval evaluate --run runs/<id> --split test      # chỉ một lần
Dataset là file .jsonl, mỗi dòng {"id": "...", "input": "...", "expected": "..." hoặc ["đáp án 1", "đáp án 2"]}.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import string
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

from .. import runs
from ..result import normalize as normalize_result
from .common import cli, write_errors


def resolve(spec):
    mod, fn = spec.split(":")
    if "" not in sys.path:
        sys.path.insert(0, "")
    return getattr(importlib.import_module(mod), fn)


def norm(s):
    s = str(s).lower()
    s = "".join(ch for ch in s if ch not in string.punctuation)
    return " ".join(s.split())


def expected_list(e):
    return e if isinstance(e, list) else [e]


def score_one(scorer, output, expected, item=None, judge=None, normalize=True):
    n = norm if normalize else str
    outs = n(output)
    if scorer == "judge":
        return float(judge(item["input"], output, expected))
    if scorer == "regex":
        return float(any(re.search(e, output) for e in expected_list(expected)))
    if scorer == "exact":
        return float(any(outs == n(e) for e in expected_list(expected)))
    if scorer == "contains":
        return float(any(n(e) in outs for e in expected_list(expected)))
    if scorer == "f1":
        best = 0.0
        for e in expected_list(expected):
            a, b = outs.split(), n(e).split()
            common = sum((Counter(a) & Counter(b)).values())
            if common:
                p, r = common / len(a), common / len(b)
                best = max(best, 2 * p * r / (p + r))
        return best
    raise SystemExit(f"scorer không hợp lệ: {scorer}")


def load_dataset(path):
    items = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    ids = [it["id"] for it in items]
    if len(set(ids)) != len(ids):
        raise SystemExit("Có id trùng trong dataset.")
    return items


def components(items):
    """Nối các mẫu cùng `group` HOẶC cùng nội dung input (đã chuẩn hóa) thành một thành phần liên thông.
    Cả hai ràng buộc được giữ đồng thời: không có nhóm nào và không có nội dung nào nằm ở hai tập."""
    parent = list(range(len(items)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    first = {}
    for i, it in enumerate(items):
        keys = ["in:" + norm(it["input"])]
        if it.get("group") not in (None, ""):
            keys.append("g:" + str(it["group"]))
        for k in keys:
            if k in first:
                parent[find(i)] = find(first[k])
            else:
                first[k] = i
    comp = {}
    for i in range(len(items)):
        comp.setdefault(find(i), []).append(i)
    # khóa ổn định của thành phần: nội dung nhỏ nhất theo thứ tự chữ, không phụ thuộc thứ tự file
    return {i: min("in:" + norm(items[m]["input"]) for m in members) for members in comp.values() for i in members}


def bucket(key, seed):
    return int(hashlib.sha1(f"{seed}:{key}".encode()).hexdigest(), 16) % 100


def split_items(items, cfg):
    """Chia dev/test theo hash của thành phần liên thông (cùng group hoặc cùng nội dung input):
    ổn định khi đổi thứ tự file, và mẫu trùng nội dung hay cùng nhóm không bao giờ nằm ở hai tập."""
    cut = int(cfg["dev_ratio"] * 100)
    key = components(items)
    b = [(it, bucket(key[i], cfg["seed"])) for i, it in enumerate(items)]
    return {"val": [i for i, x in b if x < cut], "test": [i for i, x in b if x >= cut]}


def duplicate_report(items):
    """Số dòng trùng nội dung input (tính độc lập với group)."""
    seen, dup = set(), 0
    for it in items:
        k = norm(it["input"])
        dup += k in seen
        seen.add(k)
    return dup


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def fingerprint(cfg):
    """Dấu vân tay của hệ thống đang đánh giá: đổi code, prompt, corpus, params hay phiên bản đều đổi dấu vân tay.
    Gồm nội dung file nguồn của system/judge, mọi file trong `fingerprint_files` (prompt, corpus...) và `system_version`."""
    h = hashlib.sha256()
    h.update(json.dumps([cfg["system"], cfg.get("judge"), cfg.get("params") or {}, str(cfg.get("system_version", ""))], sort_keys=True, default=str).encode())
    paths = []
    for spec in (cfg["system"], cfg.get("judge")):
        if spec:
            f = getattr(importlib.import_module(spec.split(":")[0]), "__file__", None)
            if f:
                paths.append(f)
    for pat in cfg.get("fingerprint_files") or []:
        paths += [str(x) for x in sorted(Path().glob(pat)) if x.is_file()]
    for p in sorted(set(paths)):
        h.update(p.encode() + Path(p).read_bytes())
    return h.hexdigest()[:16]


# Phiên bản định dạng + ngữ nghĩa của record cache. TĂNG số này mỗi khi đổi cách diễn giải kết quả hệ thống.
# v1 (kit trước 06/11/2026): không lưu source, từng lưu cả kết quả fallback như thành công -> không bao giờ được dùng lại.
CACHE_SCHEMA = 2


def cache_key(cfg, item):
    return hashlib.sha256(f"cache-v{CACHE_SCHEMA}|{cfg['_fp']}|{item['input']}".encode()).hexdigest()  # _fp: dấu vân tay hệ thống


def valid_cached(rec):
    """Chỉ dùng record đúng schema hiện tại VÀ vẫn đạt hợp đồng kết quả hiện tại; mọi thứ khác coi như chưa có cache."""
    if not isinstance(rec, dict) or rec.get("schema") != CACHE_SCHEMA:
        return None
    n = normalize_result({"output": rec.get("output"), "tokens": rec.get("tokens"), "source": rec.get("source"), "error": rec.get("error")})
    if not n["ok"]:
        return None
    return {"output": n["output"], "tokens": n["tokens"], "latency_ms": float(rec.get("latency_ms") or 0.0), "error": None,
            "source": "ai", "cached": True}


def call_system(fn, item, cfg):
    cache = Path(cfg["cache_dir"]) / f"{cache_key(cfg, item)}.json"
    if cfg.get("cache", True):
        try:
            hit = valid_cached(json.loads(cache.read_text(encoding="utf-8")))
            if hit:
                return hit
        except (OSError, ValueError):
            pass  # chưa có cache, file hỏng, hoặc đang được luồng khác ghi: coi như chưa có
    # Thử lại: hữu hạn (`retries`), CHỈ khi hàm hệ thống ném exception. Kết quả trả về dạng fallback/error không thử lại.
    err = None
    for attempt in range(cfg["retries"] + 1):
        t = time.time()
        try:
            raw = fn(item["input"], **(cfg.get("params") or {}))
        except Exception as e:  # lỗi hệ thống thì chấm 0 chứ không làm sập cả lần chạy
            err = f"{type(e).__name__}: {e}"
            time.sleep(0.2 * (attempt + 1))
            continue
        n = normalize_result(raw)
        res = {"output": n["output"], "tokens": n["tokens"], "latency_ms": (time.time() - t) * 1000,
               "error": None if n["ok"] else n["error"], "source": n["source"]}
        if n["ok"]:  # chỉ cache kết quả AI thành công; lỗi ghi cache không làm gọi lại hệ thống
            try:
                cache.parent.mkdir(parents=True, exist_ok=True)
                tmp = cache.with_name(f"{cache.name}.{threading.get_ident()}.tmp")
                tmp.write_text(json.dumps({**res, "schema": CACHE_SCHEMA}, ensure_ascii=False), encoding="utf-8")
                os.replace(tmp, cache)  # ghi nguyên tử để luồng khác không đọc phải file dở
            except OSError as e:
                print(f"Cảnh báo: không ghi được cache ({e}); kết quả vẫn được dùng.")
        return res
    return {"output": "", "tokens": 0, "latency_ms": 0.0, "error": err, "source": "error"}


def run_split(items, cfg, fn, judge):
    with ThreadPoolExecutor(cfg["workers"]) as ex:
        results = list(ex.map(lambda it: call_system(fn, it, cfg), items))
    rows = []
    for it, r in zip(items, results):
        s, jerr = 0.0, None
        if not r["error"]:
            try:
                s = score_one(cfg["scorer"], r["output"], it["expected"], it, judge, cfg["normalize"])
                if not 0.0 <= s <= 1.0:
                    raise ValueError(f"điểm ngoài [0,1]: {s}")
            except SystemExit:
                raise
            except Exception as e:  # judge (thường là LLM) lỗi: chấm 0, ghi rõ, không làm sập cả lần chạy
                s, jerr = 0.0, f"judge_error: {type(e).__name__}: {e}"
        rows.append({"id": it["id"], "input": it["input"], "expected": it["expected"], **r, "score": s, "judge_error": jerr})
    return rows


def summarize(rows, cfg):
    sc = np.array([r["score"] for r in rows])
    lat = [r["latency_ms"] for r in rows if not r["error"] and not r.get("cached")]
    rng = np.random.default_rng(0)
    boots = [sc[rng.integers(0, len(sc), len(sc))].mean() for _ in range(1000)] if len(sc) else [0.0]
    return {
        "n": len(rows), "score": float(sc.mean()) if len(sc) else 0.0,
        "score_ci95": [float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))],
        "pass_rate": float((sc >= cfg["pass_threshold"]).mean()) if len(sc) else 0.0,
        "failures": sum(1 for r in rows if r["error"]), "judge_errors": sum(1 for r in rows if r.get("judge_error")),
        "cached": sum(1 for r in rows if r.get("cached")),
        "latency_p50_ms": float(np.percentile(lat, 50)) if lat else None, "latency_p95_ms": float(np.percentile(lat, 95)) if lat else None,
        "tokens_total": sum(r["tokens"] for r in rows if not r.get("cached")),  # chỉ token thực sự phát sinh ở lần chạy này
        "tokens_reused_from_cache": sum(r["tokens"] for r in rows if r.get("cached")),
    }


def baseline_score(items, cfg, judge):
    """Baseline: trả lại nguyên câu hỏi. Hệ thống phải thắng được cách 'không làm gì'. Judge lỗi ở baseline thì chấm 0 và đếm."""
    scores, errs = [], 0
    for it in items:
        try:
            scores.append(score_one(cfg["scorer"], it["input"], it["expected"], it, judge, cfg["normalize"]))
        except SystemExit:
            raise
        except Exception:
            scores.append(0.0); errs += 1
    return {"score": float(np.mean(scores)) if scores else 0.0, "judge_errors": errs}


def load_system(cfg):
    judge = resolve(cfg["judge"]) if cfg.get("judge") else None
    if cfg["scorer"] == "judge" and judge is None:
        raise SystemExit("scorer=judge cần đặt khóa judge: module:function")
    cfg["_fp"] = fingerprint(cfg)
    return resolve(cfg["system"]), judge


def train(cfg):
    items = load_dataset(cfg["dataset"])
    parts = split_items(items, cfg)
    dup = duplicate_report(items)
    print(f"{len(items)} mẫu: dev {len(parts['val'])}, test {len(parts['test'])} (chia theo nhóm/nội dung input)"
          + (f"; {dup} dòng trùng nội dung được giữ cùng một tập" if dup else ""))
    cfg["dataset_sha"] = sha_file(cfg["dataset"])
    fn, judge = load_system(cfg)
    t0 = time.time()
    rows = run_split(parts["val"], cfg, fn, judge)
    val, base = summarize(rows, cfg), baseline_score(parts["val"], cfg, judge)
    out = runs.new_run_dir(cfg["runs_dir"], cfg["tag"], "llm")
    runs.save_json({**cfg, "task": "llm_eval", "model": cfg["system"], "system_fp": cfg["_fp"]}, out / "config.json")
    runs.save_json([], out / "labels.json")
    (out / "val_results.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    worst = sorted(rows, key=lambda r: r["score"])[:30]
    write_errors(out / "val_errors.csv", [(r["id"], f"{r['score']:.2f}", r["error"] or r.get("judge_error") or "", r["output"][:200]) for r in worst], ["id", "score", "error", "output"])
    runs.write_metrics(out, "score", True, val, base, seconds=time.time() - t0)
    lo, hi = val["score_ci95"]
    print(f"dev score={val['score']:.3f} (CI95 {lo:.3f}-{hi:.3f}) baseline={base['score']:.3f}; lỗi hệ thống {val['failures']}; "
          f"p50 {val['latency_p50_ms'] and round(val['latency_p50_ms'])} ms. Xem {out / 'val_errors.csv'}")
    return out


def evaluate(run, split_name, force=False):
    run = Path(run)
    cfg = runs.load_json(run / "config.json")
    if cfg.get("dataset_sha") and sha_file(cfg["dataset"]) != cfg["dataset_sha"] and not force:
        raise SystemExit("Dataset đã đổi so với lúc train (khác dấu vân tay); số liệu sẽ không so sánh được. Train lại, hoặc --force nếu cố ý.")
    fn, judge = load_system(cfg)
    if cfg.get("system_fp") and cfg["_fp"] != cfg["system_fp"] and not force:
        raise SystemExit("Code/prompt/corpus của hệ thống đã đổi sau lần train này; đánh giá sẽ không phải của run này. Train run mới, hoặc --force.")
    marker = runs.open_test_once(run, force) if split_name == "test" else run / "val_metrics.json"
    items = split_items(load_dataset(cfg["dataset"]), cfg)[split_name]
    rows = run_split(items, cfg, fn, judge)
    m = summarize(rows, cfg)
    runs.save_json(m, marker)
    (run / f"{split_name}_results.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    print(f"{split_name}: score={m['score']:.3f} pass_rate={m['pass_rate']:.3f} lỗi hệ thống {m['failures']}")


if __name__ == "__main__":
    cli(train, evaluate, "configs/llm_eval.yaml")
