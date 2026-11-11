# Phần có trước sự kiện (khai báo với BTC)

Luật: được dùng thư viện, SDK, API, starter template; phải nói rõ phần có trước và cho thấy phần làm mới trong ngày là đáng kể.

## Có trước ngày 14/11
- Bộ công cụ `hackathon-kit`: agent/skill cho Claude Code, Codex và Antigravity, backend mẫu `ml/serve/app_llm.py`, client `ml/client/aiClient.ts` (đã chép sang `app/aiClient.ts`), script `smoke_test.py`, `preflight.py`, `demo_check.py`, cấu hình deploy `render.yaml` và `eas.json`.
- Khung app Expo trống (điều hướng, quyền camera/âm thanh, chưa có luồng chính) để kiểm chứng build APK và `demo_check.py` trước ngày thi.
- Dữ liệu tĩnh: Bảng tra phân loại chất thải rắn sinh hoạt theo Quyết định 87/2025/QĐ-UBND của UBND TP Hà Nội và điểm thu hồi pin/rác nguy hại (`ml/data/hanoi_rules_87_2025.json`), bộ ảnh test `ml/data/image_eval.jsonl` ([điền số mẫu sau khi chụp]).
- Nghiên cứu người dùng: khảo sát ([điền số người]), phỏng vấn ([điền số người]) lưu trong `evidence/evidence-log.csv`.

## Làm trong ngày (14/11, 11:00–16:00)
- Luồng chính của app Expo: chụp ảnh món rác hoặc túi rác mở, thu nhỏ ảnh, gọi backend, hiển thị nhóm phân loại + cảnh báo túi lẫn + phát giọng nói tiếng Việt (`expo-speech`).
- Hàm AI (`mypkg/waste_ai.py`): prompt nhận diện đa phương thức (món, chất liệu, tình trạng dầu mỡ/còn sót) kết hợp rule engine ánh xạ Quyết định 87/2025/QĐ-UBND và tổng hợp câu đọc tiếng Việt.
- Giao diện, xử lý lỗi (`ai`/`fallback`/`busy`/`timeout`/`network`/`http`), màn `app/src/app/selftest.tsx`, bộ đếm người dùng `X-Device-Id` (`GET /stats`).
