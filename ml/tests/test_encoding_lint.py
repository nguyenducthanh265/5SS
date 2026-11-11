"""Mọi đọc/ghi file văn bản phải ghi rõ encoding="utf-8": Windows mặc định cp1252 làm vỡ tiếng Việt.
Quét AST các file mã của kit (không phải chạy thử), nên bắt được cả chỗ test thường không đi qua."""
import ast
from pathlib import Path

ML = Path(__file__).resolve().parents[1]
KIT = ML.parent
FILES = [p for d in ("mlkit", "serve", "scripts", "examples", "tests") for p in (ML / d).rglob("*.py")]
FILES += [p for p in KIT.glob("*.py")] + list((KIT / ".claude" / "monitor").glob("*.py"))


def is_binary_mode(call, pos):
    args = list(call.args)
    mode = args[pos] if len(args) > pos else next((k.value for k in call.keywords if k.arg == "mode"), None)
    return isinstance(mode, ast.Constant) and isinstance(mode.value, str) and "b" in mode.value


def problems(path):
    out = []
    for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
        has_enc = any(k.arg == "encoding" for k in n.keywords)
        if name == "open" and isinstance(f, ast.Name) and not has_enc and not is_binary_mode(n, 1):
            out.append(n.lineno)
        elif name in ("read_text", "write_text") and isinstance(f, ast.Attribute) and not has_enc:
            out.append(n.lineno)
    return out


def test_all_text_io_declares_utf8():
    bad = {str(p.relative_to(KIT)): problems(p) for p in FILES}
    bad = {k: v for k, v in bad.items() if v}
    assert not bad, f"thiếu encoding='utf-8': {bad}"


def subprocess_problems(path):
    """Mọi subprocess.run/Popen trong test phải đặt env (để tiến trình con xuất UTF-8); run(text=True) phải có encoding."""
    out = []
    for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("run", "Popen") \
                and isinstance(n.func.value, ast.Name) and n.func.value.id == "subprocess":
            kw = {k.arg for k in n.keywords}
            text = any(k.arg == "text" and isinstance(k.value, ast.Constant) and k.value.value for k in n.keywords)
            if "env" not in kw or (text and "encoding" not in kw):
                out.append(n.lineno)
    return out


def test_test_subprocesses_use_utf8_on_both_sides():
    files = list((ML / "tests").glob("*.py")) + list((KIT / "tests_kit").glob("*.py"))
    bad = {str(p.relative_to(KIT)): subprocess_problems(p) for p in files}
    bad = {k: v for k, v in bad.items() if v}
    assert not bad, f"subprocess thiếu env/encoding UTF-8: {bad}"
