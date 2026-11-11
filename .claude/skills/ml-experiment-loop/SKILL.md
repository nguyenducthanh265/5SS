---
name: ml-experiment-loop
description: Dùng khi huấn luyện, fine-tune, so sánh mô hình hoặc đánh giá prompt/agent/RAG trong bất kỳ cuộc thi AI nào (ảnh, bảng, văn bản, tín hiệu y sinh, LLM). Vòng lặp baseline -> một thay đổi -> đo -> ghi lại, kèm kiểm tra rò rỉ, phân tích lỗi và xuất mô hình để deploy.
---

# Vòng lặp thí nghiệm ML

Mục tiêu: có con số đáng tin để chứng minh mô hình tốt, không phải một bản fine-tune chạy được rồi thôi.
Mã nằm trong `ml/` (từ `ml-template/` của kit). Chạy mọi lệnh từ thư mục `ml/`.

## Chọn module theo loại giải
| Loại bài | Module (lệnh `python -m ...`) | Config | Chỉ số chính | Cách chia dữ liệu |
|---|---|---|---|---|
| Phân loại ảnh | `mlkit.train` / `mlkit.evaluate` / `mlkit.export` | `base.yaml` | macro-F1 | theo lớp, hoặc theo nhóm (`group_regex`) |
| Bảng, văn bản (TF-IDF), hồi quy | `mlkit.tasks.tabular train/evaluate` | `tabular.yaml` | macro-F1 hoặc RMSE | theo dòng, hoặc theo `group_col` |
| Tín hiệu y sinh, chuỗi thời gian (EEG, ECG, PSG, cảm biến) | `mlkit.tasks.biosignal train/evaluate` | `biosignal.yaml` | macro-F1 (+ AUROC, theo đối tượng) | **theo đối tượng** |
| LLM, agent, RAG, prompt | `mlkit.tasks.llm_eval train/evaluate` | `llm_eval.yaml` | score (0..1) | dev/test theo hash của id |
Đề không khớp loại nào (âm thanh, video, chuỗi-sang-chuỗi, học tăng cường...): vẫn áp dụng các luật cứng dưới đây; dùng lại `mlkit.data` (chia + rò rỉ), `mlkit.metrics`, `mlkit.runs` (lưu run, khóa test) và `mlkit.report`, chỉ viết phần mô hình theo mẫu của một module có sẵn. Kit chưa có sẵn huấn luyện cho âm thanh/video/transformer văn bản.

Mọi module cùng ghi `runs/<id>/` và cùng `python -m mlkit.report`, nên so sánh và báo cáo giống nhau.

## Luật cứng
1. **Chia dữ liệu một lần, đóng băng.** Ảnh: `python -m mlkit.data`; các module khác tự tạo split lần chạy đầu và dừng nếu có rò rỉ (trùng mẫu, trùng nhóm, trùng nội dung). Commit file split. Mẫu cùng video/người/bệnh nhân/cửa hàng phải cùng một tập (`group_regex`, `group_col`, hoặc chia theo đối tượng). Với tín hiệu y sinh, chia theo cửa sổ thay vì theo đối tượng là lỗi nặng nhất: điểm cao giả. Thống kê chuẩn hóa chỉ tính trên train.
2. **Có baseline trước.** Lần chạy đầu dùng cấu hình mặc định. Mô hình phải thắng baseline tự động: đoán lớp đông nhất (phân loại), đoán trung bình (hồi quy), trả lại nguyên câu hỏi (LLM).
3. **Mỗi thí nghiệm đổi đúng một thứ.** Dùng `--set khóa=giá_trị tag=tên`. Đổi hai thứ cùng lúc thì không biết cái nào có tác dụng.
4. **Chọn mô hình bằng val, mở test đúng một lần.** `evaluate --split test` bị khóa sau lần đầu cho mỗi run; run thứ hai mở test bị cảnh báo (chặn nếu `MLKIT_TEST_POLICY=strict`). Đây là hàng rào nhắc, không thay được kỷ luật: chọn trên val. Giải có split/scorer chính thức thì theo ban tổ chức. Mở test để chỉnh tiếp là tự lừa mình.
5. **Nhìn macro-F1, không chỉ accuracy,** nhất là khi lớp lệch (dùng `class_weights: balanced`). Chênh lệch nhỏ hơn khoảng tin cậy 95% thì coi như không khác nhau.
6. **Ghi lại mọi run.** Mỗi run lưu config, số liệu, môi trường vào `runs/<id>/`. Không sửa tay.

## Các bước
1. `python -m mlkit.data` -> xem số ảnh mỗi lớp, cảnh báo lệch lớp, không có RÒ RỈ.
2. Chạy baseline bằng module phù hợp (bảng trên).
3. Phân tích lỗi trước khi thử thêm: chạy `evaluate --split val`, mở `val_errors.csv` (mẫu sai mà mô hình tự tin nhất; với LLM là các câu điểm thấp nhất; với tín hiệu có thêm `val_by_subject.csv`, đối tượng nào kém nhất). Lỗi do nhãn sai, dữ liệu thiếu hay mô hình yếu quyết định bước kế tiếp.
4. Thử theo thứ tự rẻ đến đắt: sửa dữ liệu/nhãn/đặc trưng -> augmentation hoặc prompt -> `class_weights` -> mô hình khác -> siêu tham số. Dữ liệu tốt thường thắng mô hình to hơn. Với LLM: đổi một thứ mỗi lần (prompt, model, top_k, cách retrieve). Cache tự làm mới khi code hàm, params, `system_version` hoặc file trong `fingerprint_files` đổi; prompt/corpus nằm ngoài file hàm thì phải khai báo ở `fingerprint_files` hoặc tăng `system_version`.
5. `python -m mlkit.report` -> `results.md` xếp các run theo val F1.
6. Chốt một mô hình: `evaluate --split test` (một lần). Với ảnh: `python -m mlkit.export --run runs/<id> --out serve/model` (ONNX, kiểm tra khớp PyTorch, in kích thước và độ trễ). Các loại khác: đóng gói `model.joblib` / `model.pt` / hàm hệ thống thành endpoint theo mẫu `serve/app.py`.
7. Đưa `results.md`, ảnh lỗi tiêu biểu, kích thước và độ trễ cho `pitch-coach`.

## Khi nào dừng
Đặt giới hạn thời gian cho vòng thử (ví dụ 3 giờ). Hết giờ thì chốt mô hình tốt nhất trên val. Nếu mọi thay đổi đều nằm trong khoảng nhiễu, dừng và dành thời gian cho dữ liệu hoặc demo.

## Bẫy hay gặp
- Ảnh gần giống nhau (khung hình liên tiếp) nằm ở cả train và test làm điểm cao giả.
- Augmentation phá nghĩa (lật ảnh với chữ hoặc ký hiệu trái/phải): đặt `hflip: false`.
- Tiền xử lý ở lúc phục vụ khác lúc train. Export lưu `preprocess.json` và API dùng đúng nó.
- Báo số trên val như thể là test.
- Cột "tương quan gần 1 với nhãn" trong dữ liệu bảng thường là rò rỉ nhãn (thông tin chỉ có sau khi biết kết quả).
- Chỉ số LLM chấm bằng LLM khác mà không kiểm tay một mẫu nhỏ: judge cũng có thể sai.
- Chỉ nhìn một số duy nhất mà không có baseline hay khoảng tin cậy.

## Xong khi
- [ ] `split.json` đã commit, không rò rỉ
- [ ] Có baseline và ít nhất 2 thí nghiệm có đối chứng trong `results.md`
- [ ] Đã xem ảnh lỗi và ghi một câu nhận xét
- [ ] Test chạy đúng một lần cho mô hình được chọn
- [ ] Đã đóng gói mô hình/hệ thống thành endpoint và `smoke_test` qua trên URL thật (nếu cần deploy)
