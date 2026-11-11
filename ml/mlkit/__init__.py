from __future__ import annotations

import sys

# In tiếng Việt ra terminal Windows (cp1252) không làm sập lệnh: ký tự không hiển thị được sẽ thay bằng "?".
for _st in (sys.stdout, sys.stderr):
    try:
        if (getattr(_st, "encoding", "") or "").lower().replace("-", "") != "utf8":
            _st.reconfigure(errors="replace")
    except Exception:
        pass
