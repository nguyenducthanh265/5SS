<!-- hackathon-kit:begin -->
# Đội hackathon AI + Code (dùng chung cho Claude Code, Codex và Antigravity)

Ghép từ 3 nguồn: skill của Superpowers (quy trình), agent của ECC (lập kế hoạch/review), và 4 agent tự viết trong `.claude/agents/` (ml-engineer, fullstack-dev, pitch-coach, devops-deployer), cộng skill `ml-experiment-loop` và mã mẫu ML trong `ml/`.

## Bước 0: chọn profile trước khi làm gì khác
Đọc đúng một file trong `profiles/` theo loại giải, rồi chỉ dùng các vai mà profile đó liệt kê. Catalog đầy đủ bên dưới là kho để gọi khi cần, không phải luồng mặc định.
| Loại giải | Profile |
|---|---|
| App mobile có AI, hackathon vài giờ | `profiles/mobile-ai.md` |
| Web/chatbot dùng LLM, RAG | `profiles/web-rag.md` |
| Điểm dựa vào mô hình tự train/fine-tune | `profiles/ml-training.md` |
| Kaggle/Codabench/challenge có scorer chính thức | `profiles/scored-competition.md` |
Không rõ thì hỏi người dùng một câu. Luật và lịch của cuộc thi luôn thắng hướng dẫn trong kit.

## Ba công cụ, cùng một đội
- **Claude Code**: agent ở `.claude/agents/*.md` (tên có dấu gạch ngang, ví dụ `code-reviewer`), skill ở `.claude/skills/`. Skill tự kích hoạt theo ngữ cảnh.
- **Codex**: agent ở `.codex/agents/*.toml` (tên gạch dưới, ví dụ `code_reviewer`), skill ở `.agents/skills/`, gọi bằng `$tên-skill` (ví dụ `$brainstorming`).
- Codex chỉ spawn subagent khi được yêu cầu rõ. Câu mẫu: "Spawn fullstack_dev làm UI và ml_engineer làm API model song song, chờ cả hai xong rồi tóm tắt."
- Codex subagent kế thừa sandbox của phiên chính nên agent "chỉ đọc" chỉ tuân theo lời dặn, không bị chặn kỹ thuật.
- **Antigravity** (Google): đọc file này (AGENTS.md) làm quy tắc luôn bật, KHÔNG đọc CLAUDE.md. Skill ở `.agents/skills/` (chung với Codex), agent ở `.agents/agents/*.md` (tên giống Claude, ví dụ `code-reviewer`). Câu mẫu: "Dùng subagent fullstack-dev làm UI và ml-engineer làm API song song, xong thì tóm tắt."
- Antigravity: agent "chỉ đọc" vẫn có `run_command` nên cũng chỉ tuân theo lời dặn. Không thêm `.agents/` vào `.gitignore` (muốn giấu khỏi git thì dùng `.git/info/exclude`).
- Bảng dưới dùng tên Claude (Antigravity dùng y nguyên); với Codex đổi `-` thành `_`.

## Phân vai
| Việc | Dùng | Nguồn |
|---|---|---|
| Chốt ý tưởng, MVP (tối đa 3 tính năng) | skill `brainstorming` | Superpowers |
| Viết kế hoạch từng bước (ghi `PLAN.md`) | skill `writing-plans`; agent `planner` chỉ khi không dùng skill | Superpowers / ECC |
| Kiến trúc, chọn stack | agent `architect` | ECC |
| Viết code UI + backend | agent `fullstack-dev` | tự viết |
| Phần AI/ML (model, prompt, RAG) | agent `ml-engineer` | tự viết |
| Train/đánh giá có đối chứng, tránh rò rỉ (ảnh, bảng/văn bản, tín hiệu y sinh, LLM/agent/RAG) | skill `ml-experiment-loop` + mã mẫu `ml/` | tự viết |
| Deploy, smoke test trên URL thật, APK + `demo_check.py` trên điện thoại thật, phương án dự phòng | agent `devops-deployer` | tự viết |
| Chia nhiều task độc lập chạy song song | skills `subagent-driven-development`, `dispatching-parallel-agents` | Superpowers |
| Viết test trước khi code | skill `test-driven-development`; không gọi thêm `tdd-guide` | Superpowers |
| Lỗi/bug | skill `systematic-debugging` | Superpowers |
| Lỗi PyTorch/CUDA | agent `pytorch-build-resolver` | ECC |
| Review code | agent `code-reviewer` (một vòng mỗi tính năng); reviewer theo ngôn ngữ chỉ khi profile yêu cầu | ECC |
| Review pipeline ML/RAG | agent `mle-reviewer`, `rag-pipeline-reviewer` | ECC |
| Quét lộ key, bảo mật | agent `security-reviewer` | ECC |
| Test luồng demo end-to-end | web: agent `e2e-runner` (Playwright); mobile: `ml/scripts/demo_check.py` + checklist QA trong `profiles/mobile-ai.md` | ECC / tự viết |
| Trước khi nộp/claim xong | skill `verification-before-completion` | Superpowers |
| Pitch, slide, câu hỏi giám khảo | agent `pitch-coach` | tự viết |

## Luồng chạy (bản đầy đủ; profile có thể rút gọn)
1. brainstorming -> chốt MVP -> writing-plans (ghi PLAN.md)
2. architect -> ARCHITECTURE.md (hợp đồng API giữa UI/backend/model)
3. devops-deployer đưa bản hello-world lên URL thật ngay từ đầu; fullstack-dev và ml-engineer chạy song song (dispatching-parallel-agents)
4. Sau mỗi tính năng: code-reviewer (+ reviewer theo ngôn ngữ), security-reviewer trước khi push
5. AI: app gọi API/LLM có sẵn thì làm endpoint + 10-20 ví dụ chấm; có huấn luyện thì ml-engineer theo `ml-experiment-loop` (baseline -> mỗi lần đổi một thứ -> `results.md`, chọn trên val, mở test cho ứng viên cuối). Deploy rồi chạy `ml/scripts/smoke_test.py <URL> --kind image|json`
6. Từ 50% thời gian: pitch-coach; 2 giờ cuối: e2e-runner + verification-before-completion

## Quy ước
- Cuộc thi có thang điểm thì đọc nó trước (profile thường ghi sẵn) và ưu tiên việc theo điểm; hai việc tranh nhau thì chọn việc bảo vệ tiêu chí nặng điểm nhất.
- Demo chạy được > code đẹp. Luôn có dữ liệu mẫu và phương án dự phòng khi demo; giải chấm demo trên máy thật thì dự phòng bằng máy thứ hai, không bằng video.
- Không commit API key; không đặt key trong app mobile/frontend. Mỗi quyết định chỉ một vai chịu trách nhiệm (bảng trên đã chọn sẵn khi có hai lựa chọn).
- Chỉ báo "xong" khi đã chạy lệnh kiểm chứng và thấy kết quả; dashboard không phải bằng chứng.
- Chỉ gọi agent khi việc đủ lớn hoặc độc lập; việc nhỏ cứ làm thẳng.

## Theo dõi tiến độ (dashboard, tùy chọn)
- Luôn giữ `PLAN.md` ở thư mục gốc dạng checklist `- [ ] việc`; đánh dấu `- [x]` ngay khi xong để dashboard hiện thanh tiến độ.
- Khi giao việc cho agent, ghi `description` ngắn, cụ thể (ví dụ "API /predict trả JSON") để dashboard hiển thị đúng việc đang làm.
- Người dùng xem tiến độ tại http://localhost:8765 (chạy `python3 .claude/monitor/server.py`). Thẻ chỉ "xong" khi có SubagentStop; "chưa rõ" nghĩa là mất tín hiệu, cần tự kiểm tra. Chưa kiểm chứng với hook thật của Codex; Antigravity chưa gắn hook nên dashboard không thấy việc của nó, theo dõi bằng `PLAN.md`.

**Profile đang dùng cho dự án này: `mobile-ai`** (xem `profiles/mobile-ai.md`). Chỉ dùng các vai mà profile liệt kê.
<!-- hackathon-kit:end -->
