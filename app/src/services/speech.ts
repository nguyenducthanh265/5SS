import * as Speech from "expo-speech";
import { Platform } from "react-native";

export type SpeakOptions = {
  rate?: number;
  pitch?: number;
  volume?: number;
  onStart?: () => void;
  onDone?: () => void;
  onStopped?: () => void;
  onError?: (error: Error) => void;
};

function isSpeechRuntimeAvailable(): boolean {
  if (Platform.OS === "web") {
    return typeof window !== "undefined" && "speechSynthesis" in window;
  }
  return true;
}

/**
 * Dừng phát giọng nói hiện tại (nếu có). Không ném lỗi trên thiết bị không hỗ trợ TTS.
 */
export async function stopSpeaking(): Promise<void> {
  if (!isSpeechRuntimeAvailable()) return;
  try {
    await Speech.stop();
  } catch {
    // Thiết bị không hỗ trợ TTS hoặc đang không phát: bỏ qua an toàn
  }
}

/**
 * Kiểm tra trạng thái đang phát giọng nói.
 */
export async function isSpeaking(): Promise<boolean> {
  if (!isSpeechRuntimeAvailable()) return false;
  try {
    return await Speech.isSpeakingAsync();
  } catch {
    return false;
  }
}

/**
 * Kiểm tra xem thiết bị có sẵn giọng đọc hay không (không bắt buộc có đúng vi-VN mới chạy).
 */
export async function hasSpeechSupport(): Promise<boolean> {
  if (!isSpeechRuntimeAvailable()) return false;
  try {
    const voices = await Speech.getAvailableVoicesAsync();
    return Array.isArray(voices);
  } catch {
    return false;
  }
}

/**
 * Phát câu tiếng Việt (`vi-VN`) qua `expo-speech`.
 * Tự dừng câu đang đọc trước đó để tránh chồng âm; an toàn nếu thiết bị không hỗ trợ TTS.
 */
export async function speakVietnamese(text: string, opts: SpeakOptions = {}): Promise<boolean> {
  const clean = text.trim();
  if (!clean || !isSpeechRuntimeAvailable()) {
    return false;
  }

  const maxLen =
    typeof Speech.maxSpeechInputLength === "number" && Speech.maxSpeechInputLength > 0
      ? Speech.maxSpeechInputLength
      : 3800;
  const boundedText = clean.length > maxLen ? clean.slice(0, maxLen) : clean;

  try {
    await stopSpeaking();
    Speech.speak(boundedText, {
      language: "vi-VN",
      pitch: opts.pitch ?? 1.0,
      rate: opts.rate ?? 0.98,
      volume: opts.volume ?? 1.0,
      onStart: opts.onStart,
      onDone: opts.onDone,
      onStopped: opts.onStopped,
      onError: (err) => {
        opts.onError?.(err);
      },
    });
    return true;
  } catch (err) {
    const error = err instanceof Error ? err : new Error("Thiết bị không hỗ trợ đọc giọng nói.");
    opts.onError?.(error);
    return false;
  }
}
