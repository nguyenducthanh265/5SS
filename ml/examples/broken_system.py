"""Hệ thống giả luôn lỗi: dùng để kiểm tra smoke test không PASS khi AI hỏng."""


def run(text, **_):
    raise RuntimeError("AI provider down")
