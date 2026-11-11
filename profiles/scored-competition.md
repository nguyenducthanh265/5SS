# Profile: thi mô hình theo scorer của ban tổ chức (Kaggle, Codabench, challenge ở hội nghị)
- Split và metric chính thức thắng mọi mặc định của kit. Dùng `ml/` cho phần val nội bộ (chia theo nhóm/đối tượng giống cách ban tổ chức chia), report và lưu run.
- Leaderboard công khai là một tập test bị mở nhiều lần: không chọn mô hình chỉ theo leaderboard; giữ val nội bộ làm căn cứ chính.
- Nếu có paper: mọi con số trong paper truy được về một thư mục `runs/<id>`; ghi seed, phiên bản dữ liệu, cấu hình.
- Đội: agent chính, `ml-engineer`, `mle-reviewer`; viết paper do bạn chủ trì, AI chỉ hỗ trợ thực thi và đọc soát.
