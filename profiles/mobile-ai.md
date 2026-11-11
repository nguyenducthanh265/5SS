# Profile: mobile + AI API (hackathon ngắn, ví dụ Codex Community Hackathon Hà Nội 14/11/2026)

Dùng khi: app mobile (Expo) có một tính năng AI thiết yếu, build trong vài giờ, demo trên điện thoại thật.
Luật sự kiện thắng mọi hướng dẫn ở đây: luồng mobile cốt lõi và tính năng AI phải làm trong giờ thi; phần có trước (template, kit) phải công bố theo thể lệ. Kit là công cụ, không phải sản phẩm làm sẵn.

## Thang điểm (đọc trước mọi việc khác)
Giải có thang điểm công bố thì mọi quyết định tối ưu theo thang đó. Codex Community Hackathon Hà Nội (BTC gửi 10/11/2026), tối đa 100, BGK chấm theo bằng chứng thực tế, không theo slide hay độ tự tin:
| Tiêu chí | Điểm | Hệ quả cho đội |
|---|---|---|
| 1. Demo AI trên điện thoại thật | 40 / 20 / 0 | 40: **đóng hẳn rồi mở lại** app trên máy thật, luồng AI chính chạy trực tiếp. 20: mở lại được nhưng AI chạy một phần/chập chờn. **0: không mở lại được, AI không chạy trực tiếp, hoặc demo bằng trình duyệt, giả lập, ảnh hay video** |
| 2. Vấn đề thật của người dùng | 35 / 18 / 0 | nêu rõ người dùng và khó khăn, **có bằng chứng**, AI giúp trực tiếp |
| 3. Khả năng mở rộng thị trường | 25 / 13 / 0 | cách tiếp cận người dùng đầu tiên cụ thể, hướng ra toàn cầu; **đã có người dùng thực tế là lợi thế**; "ai cũng cần" = 0 |
Hòa điểm: ưu tiên tiêu chí 1, rồi 2, rồi 3. Nên khi hai việc tranh nhau, chọn việc bảo vệ tiêu chí 1.

Hệ quả kỹ thuật:
- **Demo bằng APK cài thẳng**, không bằng Expo Go: đóng Expo Go rồi mở lại phải nạp lại từ máy tính, dễ hỏng ngay trước BGK. `eas build -p android --profile preview` (file mẫu `ml/client/eas.json`).
- **Video dự phòng không cứu được điểm** (0 ở tiêu chí 1). Dự phòng bằng **máy thứ hai đã cài APK** và **4G phát từ điện thoại khác**.
- **Fallback chỉ là lưới an toàn**: nếu lúc demo app hiện nhãn "mẫu/offline" thì AI không chạy trực tiếp. Làm nóng backend trước khi lên (gọi `/health`), không demo khi chưa thấy một lượt `source: "ai"`.
- `ml/scripts/demo_check.py` diễn lại đúng việc BGK làm (force-stop, mở lại, chạy AI thật, chụp màn hình) trên mọi máy cắm USB. Cần app có deep link `<scheme>://selftest` (mục Kỹ thuật).
- Bằng chứng người dùng và người dùng thực tế: `profiles/codex-hanoi/` (khảo sát, phỏng vấn, nhật ký bằng chứng, lịch, kịch bản pitch). Backend đếm người dùng thật qua `GET /stats`.

## Đội (2–3 worker chạy song song, không hơn)
| Vai | Claude, Antigravity / Codex | Việc |
|---|---|---|
| Agent chính (bạn đang nói chuyện) | — | chốt vấn đề, `PLAN.md` ngắn, hợp đồng API trong `ARCHITECTURE.md`, ghép nối |
| Mobile builder | `fullstack-dev` / `fullstack_dev` | luồng Expo chạy trên máy thật; trạng thái loading/lỗi/hết mạng; camera/mic nếu đề cần; deep link selftest |
| AI engineer | `ml-engineer` / `ml_engineer` | một năng lực AI qua backend (`ml/serve/app_llm.py`; ảnh gửi qua `askAIImage` + `examples/openai_system_template.py`), 10–20 ví dụ đánh giá, timeout + fallback có nhãn |
| Build + demo trên máy | `devops-deployer` / `devops_deployer` | backend lên URL thật; APK; `demo_check.py` sau mỗi tính năng ghép xong và mỗi giờ |
| Reviewer/QA | `code-reviewer` + `security-reviewer` | chạy luồng trên điện thoại, kiểm tra key không nằm trong app, quyền camera/mic, lỗi chặn demo |
| Pitch | `pitch-coach` (gọi ở ~70% thời gian) | pitch 5 phút chia thời gian theo điểm, mọi số liệu có nguồn trong `evidence/` |

Không bật mặc định: reviewer từng ngôn ngữ, performance-optimizer, tdd-guide, planner (đã có `writing-plans`), e2e-runner (Playwright chỉ cho web), dashboard. Training ảnh/y sinh chỉ khi đề thật sự cần và có dữ liệu.

## Khung 5 giờ (đề xuất; lịch thật theo ban tổ chức)
| Phút | Việc | Xong khi |
|---|---|---|
| 0–20 | chốt 1 luồng người dùng, hợp đồng `POST /predict` | `PLAN.md` ≤ 10 dòng, schema request/response viết ra |
| 20–60 | skeleton: app Expo (APK) mở trên điện thoại + backend `/health` trên URL thật | điện thoại gọi được URL deploy; APK đầu tiên build xong |
| 60–150 | ghép AI vào luồng dọc UI → API → AI, thêm deep link selftest | `demo_check.py` PASS lần đầu |
| 150–210 | chấm 10–20 ví dụ, sửa lỗi, xử lý lỗi mạng/timeout; mời người tham dự dùng thử APK | `llm_eval` in số; smoke `RESULT: PASS source=ai`; `/stats` có người dùng thật |
| 210–300 | đóng băng tính năng từ phút 210; sửa lỗi chặn, `demo_check.py --repeat 3` trên cả 2 máy, tập pitch | không thêm tính năng sau phút 210 |

## Trước ngày thi (bắt buộc, không làm trong giờ thi)
Làm theo từng lệnh trong `QUICKSTART.md` của kit. Tóm tắt:
1. Cài vào dự án sạch: `./install.sh <dự án> --profile mobile-ai --no-monitor`, mã thoát phải là 0.
2. Cài thư viện, đặt key ở biến môi trường, chạy MỘT request thật tới model bạn sẽ dùng (`examples/openai_system_template.py` hoặc `examples/llm_system_template.py`) và ghi lại kết quả. Hệ thống giả trả `source: "ai"` không phải bằng chứng.
3. Giao thử một task nhỏ cho agent trên host chính (Claude Code, Codex hoặc Antigravity) từ đầu đến khi nhận báo cáo; dùng cả hai thì thử riêng từng host.
4. Build một APK khung (chưa có luồng chính) bằng EAS, cài vào **2 điện thoại Android**, chạy `demo_check.py` với một selftest tạm. Ghi lại build mất bao nhiêu phút.
5. Chạy luồng điện thoại → backend đã deploy → AI ba lần liên tiếp, gồm lần đầu khi server nguội.
6. `python -X utf8 scripts/preflight.py --real --url <URL deploy> --app-dir ../app` phải in `RESULT: GO-TECH`.
7. Thu bằng chứng người dùng theo `profiles/codex-hanoi/USER-RESEARCH.md` (khảo sát, 3 phỏng vấn, kênh người dùng đầu tiên).

Có sẵn để dùng (phần làm trước, công bố theo thể lệ, mẫu khai báo ở `profiles/codex-hanoi/DISCLOSURE.md`): backend `ml/serve/app_llm.py`, deploy `ml/deploy/render.yaml` hoặc `ml/Dockerfile`, client Expo `ml/client/aiClient.ts` (phân biệt ai / fallback / busy / timeout / network / http), `ml/client/eas.json`, `ml/scripts/demo_check.py`.

## Kỹ thuật
- **Demo bằng APK** (`eas build -p android --profile preview`, chép `ml/client/eas.json` vào app). Expo Go chỉ để phát triển. iPhone: cài bản độc lập cần máy Mac + Xcode hoặc tài khoản Apple Developer; không có thì demo bằng Android.
- Mô hình chạy trên máy (tflite/onnxruntime-react-native) cần dev build, tốn thời gian: chỉ chọn nếu "chạy offline" là điểm cốt lõi. Model huấn luyện trước ngày thi phải khai báo.
- API key chỉ ở backend (biến môi trường của Render/Railway...). App gọi backend, không gọi nhà cung cấp LLM.
- Backend nhanh nhất: `SYSTEM=mypkg.ai:run uvicorn serve.app_llm:app` (trong `ml/`), hàm `run(input, timeout=...) -> str | dict` theo hợp đồng `mlkit/result.py`. Gọi OpenAI (chữ + ảnh): `examples/openai_system_template.py` (đặt `OPENAI_MODEL`, ảnh cần `MAX_CHARS` lớn, mặc định trong `render.yaml` là 1500000). Gọi Claude: `examples/llm_system_template.py`.
- Ảnh: app thu nhỏ còn ~1024 px rồi gọi `askAIImage(url, base64, prompt, { deviceId })`; output là chuỗi JSON, app `JSON.parse` và kiểm schema; logic quyết định (tra bảng, tính toán, màu kết quả) viết bằng code, không để model tự quyết.
- **Deep link selftest** (bắt buộc cho `demo_check.py`, làm trong giờ thi cùng luồng chính): `scheme` trong `app.json`; với expo-router, file `app/selftest.tsx` tự nhận `<scheme>://selftest`. Màn hình này chạy ĐÚNG hàm của luồng chính trên một ảnh/câu mẫu đóng gói trong app, rồi `console.log("HACKCHECK SELFTEST PASS")` chỉ khi kết quả `kind === "ai"` và parse được, ngược lại `console.log("HACKCHECK SELFTEST FAIL " + lý_do)`. Không có nhánh giả.
- **Đếm người dùng thật**: tạo id ngẫu nhiên lần đầu mở app (lưu AsyncStorage), truyền `deviceId` vào `askAI`/`askAIImage`. `GET <URL>/stats` trả `ai_requests`, `devices_ai`... Bộ đếm nằm trong RAM của server (mất khi restart), log `USAGE ...` trên Render là bản lưu lâu dài; chụp màn hình `/stats` ngay sau buổi dùng thử.
- Fallback trả `source: "fallback"`; app phải hiện nhãn "mẫu/offline". Không tính fallback vào số liệu AI.
- Smoke test: `python ml/scripts/smoke_test.py <URL> --kind json --payload '{"input":"..."}' --check-fallback` (đòi một lượt `source: "ai"` thật, và một ca fallback riêng khi server đặt `ALLOW_FORCE_FALLBACK=1`; tắt biến này trước khi demo). PASS chỉ chứng minh API; `demo_check.py` mới chứng minh trên máy.
- Request chậm: server không xếp hàng; quá `MAX_INFLIGHT` trả 503 `busy` ngay. App phải xử lý 503 (hiện "đang bận, thử lại").
- Gói free của Render ngủ khi rảnh: ngày thi gọi `/health` mỗi vài phút trong giờ demo, hoặc dùng gói trả phí cho ngày thi.
- Cài kit cho dự án này: `./install.sh <dự án> --profile mobile-ai --no-monitor` (bật monitor nếu muốn xem dashboard).

## Checklist QA trên thiết bị (Reviewer chạy trước khi nộp)
- [ ] App là **APK cài thẳng**, không phải Expo Go; mở trên điện thoại thật (4G, không phải Wi-Fi chung với laptop) và gọi URL deploy
- [ ] `python -X utf8 ml/scripts/demo_check.py --package <id> --scheme <scheme> --repeat 3` in `RESULT: PASS` trên **cả hai máy**
- [ ] Tự tay vuốt tắt app, mở lại, chạy luồng chính bằng đồ thật: ra kết quả AI (không phải nhãn "mẫu/offline")
- [ ] Luồng chính chạy 3 lần liên tiếp không lỗi; lần đầu sau khi server nguội vẫn ổn (gọi /health để làm nóng)
- [ ] Một lượt thật nhận `source: "ai"`; ép fallback thì app hiện nhãn "mẫu/offline"
- [ ] Gửi liên tiếp nhiều request khi AI chậm: app nhận 503/fallback có nhãn, không treo; request sau vẫn chạy khi AI hồi phục
- [ ] Tắt mạng: app báo lỗi rõ ràng, không treo, không crash
- [ ] Từ chối quyền camera/mic: app không crash
- [ ] `grep -r "sk-\|API_KEY" app/` không thấy key
- [ ] `GET /stats` có số người dùng thật trong ngày; đã chụp lại
- [ ] Checklist đã tick không phải bằng chứng: ghi kèm kết quả lệnh hoặc ảnh chụp cho từng mục
- [ ] Số liệu trong pitch lấy từ kết quả chấm thật và `evidence/`, ghi rõ số ví dụ
