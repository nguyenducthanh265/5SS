# ARCHITECTURE — Hanoi Waste Sorter (QĐ 87/2025/QĐ-UBND)

## 1. Luồng tổng thể
`Expo Mobile App (APK)` -> `askAIImage` (`POST /predict`) -> `serve/app_llm.py` -> `mypkg/waste_ai.py:run` -> `(Vision LLM JSON)` + `(Python Rule Engine: ml/data/hanoi_rules_87_2025.json)` -> JSON response -> UI + `expo-speech` (`vi-VN`).

## 2. Hợp đồng API (`POST /predict` trên `serve/app_llm.py`)
- **Header:** `Content-Type: application/json`, `X-Device-Id: <uuid_luu_AsyncStorage>`
- **Request body:**
  ```json
  {
    "input": "{\"prompt\": \"...\", \"image\": \"data:image/jpeg;base64,...\", \"json\": true}"
  }
  ```
  - Ảnh resize trên app còn ~1024px JPEG (`expo-image-manipulator`) để nằm gọn dưới `MAX_CHARS=1500000`.
- **Response (`source: "ai"`):**
  `output` là chuỗi JSON có cấu trúc cố định do backend Python tổng hợp sau khi tra `hanoi_rules_87_2025.json`:
  ```json
  {
    "items": [
      {
        "name_vi": "Vỏ hộp sữa giấy",
        "item_key": "milk_carton",
        "material": "Giấy tráng nhôm/nhựa",
        "dirty_oily": false,
        "group_id": "group_1_recyclable",
        "group_name_vi": "Nhóm 1: Chất thải rắn tái sử dụng, tái chế",
        "rinse_required": true,
        "sell_for_recycling": true,
        "dropoff_points": [],
        "note_vi": "Đổ cạn sữa, tráng nhanh và ép dẹp trước khi bỏ."
      }
    ],
    "mixed_bag": false,
    "mixed_bag_reason_vi": "",
    "has_hazardous": false,
    "dropoff_summary": [],
    "collection_window_vi": "18:00 - 22:00 (khu vực nội đô, theo điểm quy định của UBND xã/phường)",
    "speech_vi": "Đây là vỏ hộp sữa giấy, thuộc nhóm tái chế. Bạn nhớ tráng sạch, ép dẹp; có thể gom bán phế liệu."
  }
  ```
- **Các trạng thái lỗi bắt buộc app xử lý (`ml/client/aiClient.ts`):**
  - `kind === "ai"`: `JSON.parse(output)` và kiểm schema trước khi hiển thị + phát `expo-speech`.
  - `kind === "fallback"`: hiện badge `"mẫu/offline"`, không trình bày như kết quả AI thật.
  - `kind === "busy"` (HTTP 503): `"Máy chủ AI đang bận, thử lại sau vài giây."`
  - `kind === "timeout" | "network" | "http"`: thông báo lỗi tiếng Việt rõ ràng, không crash.

## 3. Tách trách nhiệm AI vs Code
- **Vision LLM** chỉ nhận diện từng món trong ảnh (`name_vi`, `item_key` theo danh mục chuẩn, `material`, `dirty_oily`, `confidence`).
- **Python Rule Engine** quyết định 100% logic pháp lý/hành động:
  - Phân nhóm theo Quyết định 87/2025/QĐ-UBND (Nhóm 1 Tái chế, Nhóm 2 Thực phẩm, Nhóm 3 Rác thải khác / Cồng kềnh / Nguy hại).
  - Xử lý ca dễ nhầm: túi nilon dính dầu mỡ -> chuyển Nhóm 3 (không tái chế); vỉ thuốc nhôm-nhựa -> Nhóm 3 (chất thải khác/đặc thù); pin/bóng đèn -> Nhóm 3 (Chất thải nguy hại) + gợi ý điểm thu hồi tại Hà Nội.
  - Cờ `mixed_bag = true` khi phát hiện >= 2 món thuộc các `group_id` khác nhau (cảnh báo mạnh nếu lẫn chất thải nguy hại).

## 4. Selftest & Kiểm chứng
- Deep link `<scheme>://selftest` (`app/selftest.tsx`) gọi đúng `askAIImage` trên 1 ảnh mẫu đóng gói trong app; in `HACKCHECK SELFTEST PASS` chỉ khi `kind === "ai"` và parse JSON hợp lệ.
- `GET /stats` đếm `devices_ai` và `ai_requests` qua `X-Device-Id`.

