# PLAN — Phân loại rác Hà Nội (QĐ 87/2025/QĐ-UBND)

- [x] Khởi tạo dự án từ `hackathon-kit` (`--profile mobile-ai --no-monitor`) và chạy `pytest` kit
- [ ] Kiểm chứng 1 request Vision thật + deploy backend lên Render (`smoke_test.py` PASS)
- [ ] Dựng khung Expo tối thiểu + build APK cài lên 2 máy Android (`demo_check.py` PASS với selftest tạm)
- [ ] Hoàn thiện `evidence/` (khảo sát 20–30 người, 3 phỏng vấn, kênh 100 user đầu) + bộ 20–30 ảnh `llm_eval`
- [ ] Ngày thi 0–60': Nối camera Expo (`askAIImage`) + `mypkg/waste_ai.py` (`hanoi_rules_87_2025.json`) + build APK
- [ ] Ngày thi 60–150': Hiển thị nhóm QĐ 87, tráng rửa, bán ve chai, điểm bỏ pin, cờ túi lẫn, giọng nói `expo-speech`, `app/selftest.tsx`
- [ ] Ngày thi 150–210': Chạy `llm_eval`, review bảo mật/lỗi mạng, mời 10–20 người dùng thử + chụp `GET /stats`
- [ ] Ngày thi 210–300': Đóng băng tính năng, `demo_check.py --repeat 3` trên 2 máy, tập pitch 5 phút

