"""Hệ thống giả để chạy thử pipeline. Thay bằng hàm gọi LLM/agent/RAG của bạn."""
KB = {"thủ đô của việt nam": "Hà Nội", "thủ đô của nhật bản": "Tokyo", "thủ đô của pháp": "Paris", "thủ đô của ý": "Milan"}


def run(text, **params):
    return {"output": f"Đáp án: {KB.get(text.lower().strip(' ?'), 'không biết')}", "tokens": len(text.split())}
