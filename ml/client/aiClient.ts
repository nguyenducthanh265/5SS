/**
 * Client gọi backend AI (serve/app_llm.py) cho app Expo/React Native. Không chứa API key: key chỉ ở backend.
 * Đây là mẫu có sẵn từ hackathon-kit: nếu dùng trong cuộc thi, hãy công bố là phần làm trước theo thể lệ.
 *
 *   import { askAI } from "./aiClient";
 *   const r = await askAI(process.env.EXPO_PUBLIC_API_URL!, text);
 *   if (r.kind === "ai") show(r.output);
 *   else if (r.kind === "fallback") showWithBadge(r.output, "mẫu/offline");   // KHÔNG trình bày như kết quả AI
 *   else showError(r.message);                                                // busy | network | timeout | http
 *
 * EXPO_PUBLIC_API_URL chỉ chứa URL backend (công khai được); không bao giờ đặt key vào biến EXPO_PUBLIC_*.
 *
 * Ảnh (backend dùng examples/openai_system_template.py, server đặt MAX_CHARS đủ lớn):
 *   const r = await askAIImage(url, base64Jpeg, "Đọc thành phần, trả JSON {...}", { deviceId });
 * deviceId: id ngẫu nhiên lưu trên máy (ví dụ AsyncStorage), gửi qua header X-Device-Id để GET /stats đếm người dùng thật.
 */
export type AIResult =
  | { kind: "ai"; output: string; latencyMs: number }
  | { kind: "fallback"; output: string; reason: string; latencyMs: number }
  | { kind: "busy"; message: string }
  | { kind: "timeout"; message: string }
  | { kind: "network"; message: string }
  | { kind: "http"; status: number; message: string };

export type AskOptions = { timeoutMs?: number; path?: string; deviceId?: string };

export async function askAI(baseUrl: string, input: string, opts: AskOptions = {}): Promise<AIResult> {
  const timeoutMs = opts.timeoutMs ?? 25000; // lớn hơn TIMEOUT_S của server một chút để nhận được fallback có nhãn
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  const t0 = Date.now();
  try {
    const res = await fetch(baseUrl.replace(/\/+$/, "") + (opts.path ?? "/predict"), {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(opts.deviceId ? { "X-Device-Id": opts.deviceId } : {}) },
      body: JSON.stringify({ input }),
      signal: ctrl.signal,
    });
    if (res.status === 503) return { kind: "busy", message: "Máy chủ AI đang bận, thử lại sau vài giây." };
    if (!res.ok) return { kind: "http", status: res.status, message: `Lỗi máy chủ (${res.status}).` };
    const data: unknown = await res.json();
    const d = (typeof data === "object" && data !== null ? data : {}) as Record<string, unknown>;
    const output = typeof d.output === "string" ? d.output : "";
    const latencyMs = Date.now() - t0;
    if (d.source === "ai" && output.trim() && !d.error) return { kind: "ai", output, latencyMs };
    // Mọi thứ không chắc chắn là AI thành công đều là fallback: không bao giờ hiển thị như kết quả AI
    return { kind: "fallback", output: output || "Không có câu trả lời.", reason: String(d.error ?? d.source ?? "unknown"), latencyMs };
  } catch (e) {
    if ((e as { name?: string })?.name === "AbortError") return { kind: "timeout", message: "Quá thời gian chờ AI." };
    return { kind: "network", message: "Không kết nối được máy chủ. Kiểm tra mạng." };
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Gửi một ảnh (base64 JPEG hoặc data URL) kèm yêu cầu. Thu nhỏ ảnh còn ~1024 px trước khi gọi (expo-image-manipulator)
 * để request nhỏ và nhanh. json=true (mặc định): model trả một object JSON trong `output`; app tự JSON.parse và kiểm schema.
 */
export async function askAIImage(
  baseUrl: string,
  imageBase64: string,
  prompt: string,
  opts: AskOptions & { json?: boolean } = {},
): Promise<AIResult> {
  const image = imageBase64.startsWith("data:") ? imageBase64 : `data:image/jpeg;base64,${imageBase64}`;
  const { json = true, ...rest } = opts;
  return askAI(baseUrl, JSON.stringify({ prompt, image, json }), rest);
}
