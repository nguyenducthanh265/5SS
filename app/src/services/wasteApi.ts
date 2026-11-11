import { ImageManipulator, SaveFormat } from "expo-image-manipulator";

import { askAIImage } from "../../aiClient";
import { parseWasteResult, type WasteResult } from "../types/waste";
import { getDeviceId } from "./deviceId";

export const DEFAULT_WASTE_PROMPT =
  "Nhận diện các món rác thải trong ảnh để phân loại theo Quyết định 87/2025/QĐ-UBND Hà Nội. Trả về đúng JSON theo schema chuẩn.";

export const MAX_IMAGE_DIMENSION = 1024;
export const JPEG_COMPRESS_QUALITY = 0.8;

export type ClassifyWasteResponse =
  | {
      status: "ai";
      result: WasteResult;
      rawOutput: string;
      latencyMs: number;
    }
  | {
      status: "fallback";
      rawOutput: string;
      parsedResult: WasteResult | null;
      reason: string;
      badge: "mẫu/offline";
      latencyMs: number;
    }
  | {
      status: "parse_error";
      rawOutput: string;
      reason: string;
      latencyMs: number;
    }
  | {
      status: "busy" | "timeout" | "network" | "http" | "config_error";
      message: string;
      httpStatus?: number;
    };

/**
 * Đọc URL backend từ `EXPO_PUBLIC_API_URL`. Không bao giờ chứa API key.
 */
export function getApiBaseUrl(): string {
  return (process.env.EXPO_PUBLIC_API_URL ?? "").trim();
}

function safeRelease(resource: { release?: () => void } | null | undefined): void {
  try {
    if (resource && typeof resource.release === "function") {
      resource.release();
    }
  } catch {
    // Ignore cleanup errors on already-released SharedObject/ImageRef
  }
}

/**
 * Thu nhỏ ảnh về cạnh tối đa `maxDim` (mặc định 1024px) và xuất base64 JPEG
 * để nằm gọn dưới giới hạn `MAX_CHARS` của backend.
 */
export async function resizeImageToBase64(
  uri: string,
  maxDim: number = MAX_IMAGE_DIMENSION,
): Promise<string> {
  const cleanUri = uri.trim();
  if (!cleanUri) {
    throw new Error("Thiếu đường dẫn ảnh để xử lý.");
  }

  const boundedDim = Math.max(1, Math.round(maxDim));
  type ManipulateCtx = ReturnType<typeof ImageManipulator.manipulate>;
  type ManipulatedRef = Awaited<ReturnType<ManipulateCtx["renderAsync"]>>;
  let firstCtx: ManipulateCtx | null = null;
  let secondCtx: ManipulateCtx | null = null;
  let loaded: ManipulatedRef | null = null;
  let targetRef: ManipulatedRef | null = null;

  try {
    firstCtx = ImageManipulator.manipulate(cleanUri, {
      maxWidth: boundedDim,
      maxHeight: boundedDim,
    });
    loaded = await firstCtx.renderAsync();

    targetRef = loaded;
    if (loaded.width > boundedDim || loaded.height > boundedDim) {
      const resizeSize =
        loaded.width >= loaded.height ? { width: boundedDim } : { height: boundedDim };
      secondCtx = ImageManipulator.manipulate(loaded).resize(resizeSize);
      targetRef = await secondCtx.renderAsync();
    }

    const saved = await targetRef.saveAsync({
      format: SaveFormat.JPEG,
      compress: JPEG_COMPRESS_QUALITY,
      base64: true,
    });

    if (
      saved.uri &&
      saved.uri.startsWith("blob:") &&
      typeof URL !== "undefined" &&
      typeof URL.revokeObjectURL === "function"
    ) {
      URL.revokeObjectURL(saved.uri);
    }

    const rawBase64 = saved.base64?.replace(/^data:[^;]+;base64,/i, "").trim();
    if (!rawBase64) {
      throw new Error("Không trích xuất được base64 JPEG từ ảnh.");
    }
    return rawBase64;
  } finally {
    if (targetRef && targetRef !== loaded) {
      safeRelease(targetRef);
    }
    safeRelease(loaded);
    safeRelease(secondCtx);
    safeRelease(firstCtx);
  }
}

/**
 * Gửi base64 JPEG tới backend `/predict` qua `askAIImage` kèm `deviceId`,
 * sau đó kiểm tra trạng thái `ai / fallback / busy / timeout / network / http` và parse JSON an toàn.
 */
export async function classifyWasteImage(
  imageBase64: string,
  opts: { baseUrl?: string; prompt?: string; timeoutMs?: number } = {},
): Promise<ClassifyWasteResponse> {
  const baseUrl = (opts.baseUrl ?? getApiBaseUrl()).trim();
  if (!baseUrl) {
    return {
      status: "config_error",
      message: "Chưa cấu hình EXPO_PUBLIC_API_URL trỏ tới backend.",
    };
  }

  const deviceId = await getDeviceId();
  const prompt = opts.prompt ?? DEFAULT_WASTE_PROMPT;
  const aiRes = await askAIImage(baseUrl, imageBase64, prompt, {
    deviceId,
    timeoutMs: opts.timeoutMs,
    json: true,
  });

  if (aiRes.kind === "ai") {
    const parsed = parseWasteResult(aiRes.output);
    if (!parsed.ok) {
      return {
        status: "parse_error",
        rawOutput: aiRes.output,
        reason: parsed.reason,
        latencyMs: aiRes.latencyMs,
      };
    }
    return {
      status: "ai",
      result: parsed.data,
      rawOutput: aiRes.output,
      latencyMs: aiRes.latencyMs,
    };
  }

  if (aiRes.kind === "fallback") {
    const parsed = parseWasteResult(aiRes.output);
    return {
      status: "fallback",
      rawOutput: aiRes.output,
      parsedResult: parsed.ok ? parsed.data : null,
      reason: aiRes.reason,
      badge: "mẫu/offline",
      latencyMs: aiRes.latencyMs,
    };
  }

  if (aiRes.kind === "http") {
    return {
      status: "http",
      message: aiRes.message,
      httpStatus: aiRes.status,
    };
  }

  return {
    status: aiRes.kind,
    message: aiRes.message,
  };
}

/**
 * Tiện ích đầu-cuối từ URI ảnh (camera/asset) -> resize ~1024px -> gọi backend -> parse schema.
 */
export async function classifyWasteUri(
  uri: string,
  opts: { baseUrl?: string; prompt?: string; timeoutMs?: number } = {},
): Promise<ClassifyWasteResponse> {
  const baseUrl = (opts.baseUrl ?? getApiBaseUrl()).trim();
  if (!baseUrl) {
    return {
      status: "config_error",
      message: "Chưa cấu hình EXPO_PUBLIC_API_URL trỏ tới backend.",
    };
  }
  const base64 = await resizeImageToBase64(uri);
  return classifyWasteImage(base64, { ...opts, baseUrl });
}
