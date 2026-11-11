"""API suy luận ONNX. Chạy: MODEL_DIR=serve/model uvicorn serve.app:app --host 0.0.0.0 --port 8000"""
from __future__ import annotations

import io
import json
import os
import time
from pathlib import Path

import numpy as np
import onnxruntime as ort
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError

MODEL_DIR = Path(os.environ.get("MODEL_DIR", Path(__file__).parent / "model"))
MAX_BYTES = 10 * 1024 * 1024

classes = json.loads((MODEL_DIR / "labels.json").read_text(encoding="utf-8"))
pre = json.loads((MODEL_DIR / "preprocess.json").read_text(encoding="utf-8"))
session = ort.InferenceSession(str(MODEL_DIR / "model.onnx"), providers=["CPUExecutionProvider"])

app = FastAPI(title="Model API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def preprocess(img):
    img = img.convert("RGB").resize((pre["size"], pre["size"]), Image.BILINEAR)
    x = np.asarray(img, dtype=np.float32) / 255.0
    x = (x - np.array(pre["mean"], dtype=np.float32)) / np.array(pre["std"], dtype=np.float32)
    return x.transpose(2, 0, 1)[None].astype(np.float32)


@app.get("/health")
def health():
    return {"status": "ok", "classes": classes}


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "Ảnh quá lớn (tối đa 10 MB).")
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "File không phải ảnh hợp lệ.")
    t = time.time()
    logits = session.run(None, {"input": preprocess(img)})[0][0]
    e = np.exp(logits - logits.max())
    probs = e / e.sum()
    top = np.argsort(-probs)[:3]
    return {
        "label": classes[int(top[0])],
        "confidence": float(probs[top[0]]),
        "top3": [{"label": classes[int(i)], "confidence": float(probs[i])} for i in top],
        "latency_ms": round((time.time() - t) * 1000, 1),
    }
