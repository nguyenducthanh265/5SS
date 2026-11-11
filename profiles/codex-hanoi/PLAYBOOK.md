# Codex Community Hackathon Hà Nội — thứ Bảy 14/11/2026

Thang điểm và hệ quả kỹ thuật: `profiles/mobile-ai.md`, mục "Thang điểm". Tóm tắt: **demo AI trên máy thật 40** (đóng hẳn rồi mở lại, AI chạy trực tiếp; video/giả lập/trình duyệt = 0) · vấn đề thật có bằng chứng 35 · tiếp cận người dùng đầu tiên và mở rộng 25.

## Trước ngày thi
| Ngày | Việc | Xong khi |
|---|---|---|
| Thứ Ba–Tư | QUICKSTART phần A bước 1–5: backend lên Render, một request thật | `smoke_test.py` in `RESULT: PASS source=ai` trên URL thật |
| Thứ Tư | APK khung (chưa có luồng chính) bằng `eas build --profile preview`, cài vào **2 máy Android** | mở app trên máy không cần laptop; biết build mất bao nhiêu phút |
| Thứ Tư | `demo_check.py` với một màn selftest tạm gọi `/predict` | `RESULT: PASS` trên cả 2 máy (sau đó xóa màn tạm) |
| Thứ Tư–Năm | 20–30 dữ liệu test thật + `llm_eval` (ảnh: `ml/configs/llm_eval_image.yaml`, cách ghi dataset ở đầu file) | có con số độ chính xác, ví dụ 26/30 |
| Thứ Tư–Năm | Khảo sát + 3 phỏng vấn theo `USER-RESEARCH.md` | `evidence-log.csv` có số liệu, trích dẫn, kênh người dùng đầu tiên |
| Thứ Năm tối | Tổng duyệt: tắt Wi-Fi, chỉ dùng 4G, chạy lại từ đầu | cả nhóm thấy quy trình trơn |
| Thứ Sáu | Điền `DISCLOSURE.md`, sạc pin, đóng đồ | đủ danh sách đồ |

Không có máy Android: cần máy Mac + Xcode để cài bản độc lập lên iPhone bằng cáp; không có cả hai thì mượn máy Android trước thứ Năm.

## Đồ mang theo
- 2 điện thoại Android đã bật USB debugging, đã cài APK khung, sạc đầy
- Cáp USB đúng cổng, sạc dự phòng, ổ cắm kéo dài
- 1 điện thoại phát 4G (không phụ thuộc Wi-Fi quán)
- Đồ demo thật theo ý tưởng (sản phẩm, giấy tờ...)
- Laptop: Node, `adb` (Android platform-tools), Python + thư viện backend, đã đăng nhập Expo/EAS và Render

## Trong ngày (giờ theo lịch BTC: build 11:00–16:00)
| Giờ | Mục tiêu | Kiểm tra |
|---|---|---|
| 11:00–11:20 | Chốt một luồng, hợp đồng `/predict`, `PLAN.md` | ≤ 10 dòng |
| 11:20–12:00 | Nối app với backend, bắt đầu build APK đầu tiên (EAS chạy nền) | điện thoại gọi được URL deploy |
| 12:00–13:30 | Luồng chính chạy đầu–cuối + deep link selftest | `demo_check.py` PASS lần 1 |
| 13:30–14:30 | Logic quyết định bằng code, kết quả rõ ràng, lỗi tiếng Việt | `demo_check.py` PASS mỗi giờ |
| 14:00–15:00 | Mời 10–20 người tham dự dùng thử APK | `/stats` có người dùng thật; chụp lại |
| 14:30 (phút 210) | **Chốt tính năng** | chỉ sửa lỗi |
| 14:30–15:50 | `demo_check.py --repeat 3` cả 2 máy, `llm_eval` lần cuối, pitch-coach soạn pitch, tập 2 lần | PASS cả 2 máy |
| 16:00 | Nộp bài | |

## Pitch 5 phút (chia theo điểm)
1. **0:00–0:40 Người dùng và nỗi đau (tiêu chí 2).** Một người thật, một khoảnh khắc thật, một trích dẫn nguyên văn.
2. **0:40–2:50 Demo trực tiếp (tiêu chí 1).** Câu đầu: *"Em xin đóng hẳn ứng dụng và mở lại."* Vuốt tắt app trước mặt BGK, mở lại, chạy luồng AI với đồ thật.
3. **2:50–3:50 Bằng chứng (tiêu chí 2).** Khảo sát, độ chính xác trên dữ liệu thật (`llm_eval`), số người dùng thử hôm nay (`/stats`).
4. **3:50–4:50 Tiếp cận và mở rộng (tiêu chí 3).** Kênh cụ thể cho 100 người dùng đầu tiên (tên nhóm, số thành viên, ai phụ trách), bước mở rộng tiếp theo (dữ liệu theo nước/thành phố là file riêng: thêm nơi mới = thêm file).
5. **4:50–5:00 Một câu chốt.**

Demo lỗi trên máy 1: chuyển ngay sang máy 2 ("em chuyển sang máy dự phòng"), không giải thích dài.
