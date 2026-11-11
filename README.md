# 5SS — Điều Hòa Dòng Rác (Hanoi Waste Sorter)

Ứng dụng di động & backend AI hỗ trợ hộ gia đình và sinh viên tại Hà Nội phân loại rác thải sinh hoạt tại nguồn ngay tại thùng rác theo **Quyết định 87/2025/QĐ-UBND** (áp dụng từ **08/01/2026**).

## Tính năng chính
- **Soi 1 món rác & Quét túi rác mở:** Nhận diện vật phẩm, chất liệu và tình trạng dính dầu mỡ/thức ăn từ ảnh camera hoặc thư viện.
- **Ánh xạ quy tắc xác định QĐ 87/2025 (`ml/mypkg/waste_rules.py`):**
  - **Nhóm 1 — Rác tái chế:** vỏ hộp sữa giấy (tráng sạch, ép dẹt), chai nhựa sạch, lon nhôm, giấy/carton khô, hướng dẫn bán ve chai.
  - **Nhóm 2 — Chất thải thực phẩm:** thức ăn thừa, vỏ rau củ, bã cà phê (chắt ráo nước).
  - **Nhóm 3 — Rác sinh hoạt khác & Nguy hại:** túi nilon dính dầu mỡ, vỉ thuốc nhôm-nhựa; tách riêng tuyệt đối **pin thải / bóng đèn huỳnh quang / rác nguy hại** kèm điểm thu hồi tại Hà Nội.
  - **Cảnh báo túi lẫn (`mixed_bag`):** phát hiện và cảnh báo ngay khi túi rác chứa hỗn hợp nhiều nhóm hoặc lẫn rác nguy hại.
- **Trả lời bằng giọng nói tiếng Việt (`expo-speech`):** đọc hướng dẫn ngay tại thùng rác (bỏ nhóm nào, có cần tráng không, bán ve chai hay mang tới điểm thu hồi).
- **An toàn demo & vận hành:**
  - Giao diện **Light / Dark Mode** tối ưu tương phản và bảng tra nhanh **QĐ 87** trực tiếp trong app.
  - Không lưu API key trong mã ứng dụng (`app/`); mọi lệnh gọi AI đi qua FastAPI backend (`/predict`, `/health`, `/stats`) với timeout, giới hạn đồng thời (`MAX_INFLIGHT`), fallback có nhãn, và đếm máy dùng ẩn danh (`X-Device-Id`).

## Cấu trúc thư mục
- `app/` — Ứng dụng Expo React Native / Web (`expo-router`, TypeScript).
- `ml/` — FastAPI server (`serve/app_llm.py`), Gemini Vision adapter (`mypkg/gemini_vision.py`), OpenAI Vision template (`examples/openai_system_template.py`), rule engine (`mypkg/waste_rules.py`), và dữ liệu QĐ 87 (`data/hanoi_rules_87_2025.json`).
- `scripts/` — Smoke test end-to-end (`e2e_smoke.py`, `e2e_smoke.ps1`).
- `evidence/` — Tài liệu khảo sát, phỏng vấn người dùng và khai báo hackathon.
- `render.yaml` & `DEPLOY.md` — Cấu hình deploy Render Blueprint và build APK qua EAS.

## Chạy thử trên máy (Local Development)

### 1. Chạy Backend AI (mặc định dùng Gemini API)
```powershell
cd ml
pip install -r requirements-llm.txt
$env:SYSTEM = "mypkg.waste_ai:run"
$env:LLM_PROVIDER = "gemini"
$env:GEMINI_API_KEY = "<your-gemini-api-key>"
$env:GEMINI_MODEL = "gemini-3.5-flash-lite"
$env:MAX_CHARS = "1500000"
uvicorn serve.app_llm:app --host 0.0.0.0 --port 8000
```
*(Nếu dùng OpenAI thay thế, đặt `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, và `OPENAI_MODEL=gpt-4o-mini`.)*

### 2. Chạy App Expo (Web / Mobile)
```powershell
cd app
npm install
# Tạo file app/.env (không commit) theo app/.env.example:
# EXPO_PUBLIC_API_URL=http://127.0.0.1:8000
npx expo start --web --port 8085
```

## Kiểm thử tự động
```powershell
# Backend unit tests & rule engine
cd ml
python -X utf8 -m pytest -q
python -X utf8 scripts/waste_smoke_test.py --local

# Mobile typecheck, lint & smoke test
cd ../app
npx tsc --noEmit
npx eslint .
npm run smoke

# Cross-stack E2E smoke test (JPEG base64 -> /predict -> /stats + secret scan)
cd ..
python -X utf8 scripts/e2e_smoke.py --local
```

Xem chi tiết quy trình deploy Render Blueprint, build APK và `demo_check.py` trên Android tại [`DEPLOY.md`](./DEPLOY.md).
