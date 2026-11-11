# DEPLOY — Hanoi Waste Sorter (Windows PowerShell)

Hướng dẫn thực chiến đưa backend AI lên Render, build APK bằng EAS, kiểm chứng trên điện thoại Android thật qua `adb`, và dự phòng khi thi đấu.

---

## 1. Deploy Backend lên Render Blueprint

1. Đảm bảo `render.yaml` nằm ở **thư mục gốc của git repository** trước khi push (nếu repo git nằm ở thư mục cha của `hanoi-waste-app/`, chép `render.yaml` ra gốc repo và đổi `rootDir: hanoi-waste-app/ml`).
2. Push code lên GitHub, vào **Render Dashboard > New > Blueprint**, chọn repo chứa `render.yaml`.
3. Khi Render hỏi biến `sync: false`, điền:
   - `GEMINI_API_KEY`: API key Gemini từ Google AI Studio (chỉ lưu trên Render, tuyệt đối không đưa vào code hay `app/`).
   - `GEMINI_MODEL` mặc định trong `render.yaml` là `gemini-3.8-flash` (nếu dùng OpenAI thay thế, đặt `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_MODEL=gpt-4o-mini`).
4. Biến `SYSTEM` trong `render.yaml` đã được đặt sẵn là `mypkg.waste_ai:run` (gọi Vision AI rồi áp bộ quy tắc QĐ 87/2025/QĐ-UBND trong `ml/mypkg/waste_ai.py`).
5. *(Chỉ khi cần test nhánh fallback trên URL thật)*: tạm thêm `ALLOW_FORCE_FALLBACK=1` trên Render Environment, test xong **bắt buộc xóa/đặt `0` trước khi demo**.

Kiểm tra nhanh `/health` từ PowerShell (lần đầu gói `free` có thể mất 30–60 giây để thức dậy):

```powershell
$API_URL = "https://hanoi-waste-ai.onrender.com"
Invoke-RestMethod "$API_URL/health"
```

---

## 2. Kiểm chứng Backend đã deploy (`smoke_test.py` & `preflight.py`)

Chạy trong thư mục `hanoi-waste-app\ml\`:

```powershell
cd "c:\Users\ThinkPad\OneDrive - MSFT\Desktop\hackathon codex\hanoi-waste-app\ml"

# 1) Smoke test JSON + yêu cầu source=ai thật (tăng --max-ms lên 20000 cho lần gọi model thật / cold start)
python -X utf8 scripts/smoke_test.py $API_URL --kind json --payload '{"input":"{\"prompt\":\"Nhận diện chai nhựa PET\",\"json\":true}"}' --max-ms 20000

# 2) Nếu đang bật ALLOW_FORCE_FALLBACK=1 trên Render để kiểm nhánh fallback:
python -X utf8 scripts/smoke_test.py $API_URL --kind json --payload '{"input":"xin chào"}' --check-fallback --max-ms 20000

# 3) Preflight tổng hợp (cần đặt biến môi trường local tương ứng khi chạy --real):
$env:SYSTEM = "mypkg.waste_ai:run"
$env:LLM_PROVIDER = "gemini"
$env:GEMINI_API_KEY = "<key-gemini-của-bạn>"
$env:GEMINI_MODEL = "gemini-3.8-flash"
python -X utf8 scripts/preflight.py --real --url $API_URL --app-dir ../app
```

Đọc dòng cuối phải thấy `RESULT: PASS source=ai` (smoke test) và `RESULT: GO-TECH` (preflight). Kiểm tra `GET /stats` để xác nhận bộ đếm:

```powershell
Invoke-RestMethod "$API_URL/stats"
```

---

## 3. Cài đặt `adb` (Android platform-tools) trên Windows

`demo_check.py` cần `adb` nằm trong `PATH`:

1. Tải **Android SDK Platform-Tools for Windows** (`platform-tools-latest-windows.zip`) từ trang chính thức của Android Developer (`developer.android.com/tools/releases/platform-tools`) và giải nén, ví dụ vào `C:\Android\platform-tools`.
   *(Hoặc dùng winget nếu máy có sẵn: `winget install Google.PlatformTools`)*
2. Thêm `C:\Android\platform-tools` vào `PATH` (tạm thời trong phiên PowerShell hiện tại hoặc vĩnh viễn trong System Environment Variables):

```powershell
$env:Path += ";C:\Android\platform-tools"
adb version
```

3. Trên **cả 2 điện thoại Android**:
   - Bật **Developer Options** (Cài đặt > Giới thiệu điện thoại > chạm 7 lần vào *Build number* / *Số hiệu bản tạo*).
   - Bật **USB Debugging** (Gỡ lỗi USB).
   - Cắm cáp USB vào laptop và bấm **Allow / Cho phép** trên hộp thoại xác nhận RSA fingerprint trên màn hình điện thoại.
4. Kiểm tra kết nối:

```powershell
adb devices
```

Phải thấy mã serial ở trạng thái `device` (nếu hiện `unauthorized`, mở khóa màn hình điện thoại và bấm *Cho phép*).

---

## 4. Cấu hình `EXPO_PUBLIC_API_URL` & Build APK bằng EAS

Không demo bằng Expo Go (đóng hẳn rồi mở lại sẽ mất kết nối bundler). Dùng bản APK cài độc lập:

1. Mở `hanoi-waste-app\app\eas.json`, cập nhật URL backend Render thật vào profile `preview`:

```json
{
  "cli": { "version": ">= 12.0.0" },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    },
    "preview": {
      "distribution": "internal",
      "android": { "buildType": "apk" },
      "env": {
        "EXPO_PUBLIC_API_URL": "https://hanoi-waste-ai.onrender.com"
      }
    }
  }
}
```

> Lưu ý bảo mật: `EXPO_PUBLIC_API_URL` chỉ chứa URL backend công khai. Tuyệt đối **không** đặt `GEMINI_API_KEY`, `OPENAI_API_KEY` hay bất kỳ secret nào vào `EXPO_PUBLIC_*`.

2. Cài EAS CLI (nếu chưa có), đăng nhập và build APK từ thư mục `hanoi-waste-app\app\`:

```powershell
cd "c:\Users\ThinkPad\OneDrive - MSFT\Desktop\hackathon codex\hanoi-waste-app\app"
npm install -g eas-cli
eas login
eas build -p android --profile preview
```

3. Sau khi EAS build xong, tải file `.apk` về máy (ví dụ `hanoi-waste.apk`) và cài lên **cả 2 điện thoại Android** đang cắm USB:

```powershell
adb -s <SERIAL_MAY_1> install -r .\hanoi-waste.apk
adb -s <SERIAL_MAY_2> install -r .\hanoi-waste.apk
```

---

## 5. Kiểm chứng trên điện thoại thật (`demo_check.py --repeat 3`)

`demo_check.py` tự động lặp lại đúng thao tác của BGK: `force-stop` -> mở lại app từ launcher -> gọi deep link `hanoiwaste://selftest` -> đợi `HACKCHECK SELFTEST PASS` -> chụp ảnh màn hình.

Chạy từ `hanoi-waste-app\ml\`:

```powershell
cd "c:\Users\ThinkPad\OneDrive - MSFT\Desktop\hackathon codex\hanoi-waste-app\ml"
python -X utf8 scripts/demo_check.py --package com.codexhanoi.wastesorter --scheme hanoiwaste --repeat 3
```

- Nếu muốn cài APK mới cùng lúc kiểm tra, thêm `--apk ..\app\hanoi-waste.apk`.
- Yêu cầu dòng cuối phải in `RESULT: PASS devices=... rounds=...` trên **cả 2 máy**.
- Kiểm tra thêm bằng tay trên máy (đóng app, mở lại, chụp ảnh rác thật qua **4G**, không dùng Wi-Fi chung với laptop).

---

## 6. Phương án dự phòng thi đấu (Bảo vệ Tiêu chí 1 - 40 điểm)

1. **Làm nóng (warm) `/health` trước khi lên sân khấu:**
   Gói Render `free` tự ngủ sau 15 phút rảnh. Trong lúc chờ tới lượt pitch/chấm, giữ một cửa sổ PowerShell ping `/health` mỗi 4 phút và kiểm tra 1 lượt AI thật trước khi lên:
   ```powershell
   while ($true) {
     $t = Get-Date -Format "HH:mm:ss"
     try { $r = Invoke-RestMethod "$API_URL/health"; Write-Host "$t OK $($r.system)" }
     catch { Write-Host "$t ERR $_" }
     Start-Sleep -Seconds 240
   }
   ```
   Trước giờ nộp/demo, chụp lại `Invoke-RestMethod "$API_URL/stats"` làm bằng chứng người dùng thật.
2. **2 máy Android đã cài sẵn APK:**
   Luôn mang theo 2 máy Android cùng cài bản APK đã pass `demo_check.py --repeat 3`, sạc đầy pin > 80%, tắt chế độ tiết kiệm pin/tối ưu mạng nền. Nếu máy chính trục trặc màn hình/mạng, rút máy dự phòng ra demo ngay.
3. **Phát 4G từ điện thoại phụ:**
   Không phụ thuộc Wi-Fi hội trường (thường nghẽn hoặc chặn port). Dùng SIM 4G riêng hoặc bật hotspot 4G từ điện thoại phụ cho máy demo.
4. **Fallback local server 1 lệnh (khi cần kiểm tra khẩn cấp hoặc mất kết nối cloud):**
   Chạy trực tiếp backend từ `hanoi-waste-app\ml\` trên laptop (đặt `SYSTEM=mypkg.waste_ai:run`):
   ```powershell
   cd "c:\Users\ThinkPad\OneDrive - MSFT\Desktop\hackathon codex\hanoi-waste-app\ml"; $env:SYSTEM="mypkg.waste_ai:run"; $env:LLM_PROVIDER="gemini"; $env:GEMINI_MODEL="gemini-3.8-flash"; $env:MAX_CHARS="1500000"; $env:TIMEOUT_S="20"; $env:MAX_INFLIGHT="8"; uvicorn serve.app_llm:app --host 0.0.0.0 --port 8000
   ```
   *(Nhớ đặt `$env:GEMINI_API_KEY` trước khi chạy, hoặc chuyển sang `LLM_PROVIDER=openai` với `OPENAI_API_KEY` + `OPENAI_MODEL`. Với bài thi chính thức nộp cho BGK, APK vẫn phải trỏ về URL deploy công khai qua HTTPS).*
