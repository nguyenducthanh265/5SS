# Profile: web + LLM/RAG
Dùng khi: web app hoặc chatbot có truy xuất tài liệu, hackathon 1–3 ngày.
- Đội: agent chính, `fullstack-dev`, `ml-engineer`, `rag-pipeline-reviewer` (khi đã có pipeline), `code-reviewer`, `pitch-coach`; `e2e-runner` cho luồng demo web.
- Đánh giá: `ml/` module `llm_eval`; đặt `fingerprint_files` trỏ tới prompt và corpus để đổi tài liệu là cache tự làm mới; mỗi lần đổi một thứ (chunk size, top_k, prompt, model).
- Backend: `ml/serve/app_llm.py`; smoke test `--kind json`.
