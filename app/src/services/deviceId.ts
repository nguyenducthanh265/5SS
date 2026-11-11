import AsyncStorage from "@react-native-async-storage/async-storage";

const DEVICE_ID_STORAGE_KEY = "hanoi_waste_device_id_v1";

let cachedDeviceId: string | null = null;
let pendingPromise: Promise<string> | null = null;

function generateUuidV4(): string {
  const globalCrypto = globalThis.crypto as
    | { randomUUID?: () => string; getRandomValues?: (arr: Uint8Array) => Uint8Array }
    | undefined;

  if (globalCrypto?.randomUUID) {
    return globalCrypto.randomUUID();
  }

  const bytes = new Uint8Array(16);
  if (globalCrypto?.getRandomValues) {
    globalCrypto.getRandomValues(bytes);
  } else {
    for (let i = 0; i < 16; i += 1) {
      bytes[i] = Math.floor(Math.random() * 256);
    }
  }

  // RFC 4122 version 4 & variant 1 bits
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;

  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/**
 * Lấy hoặc khởi tạo UUID ngẫu nhiên lưu trong AsyncStorage để gửi qua header `X-Device-Id`.
 * Tránh race condition khi gọi song song; an toàn khi AsyncStorage gặp lỗi.
 */
export async function getDeviceId(): Promise<string> {
  if (cachedDeviceId) {
    return cachedDeviceId;
  }
  if (pendingPromise) {
    return pendingPromise;
  }

  pendingPromise = (async () => {
    try {
      const existing = await AsyncStorage.getItem(DEVICE_ID_STORAGE_KEY);
      if (existing && existing.trim().length > 0) {
        cachedDeviceId = existing.trim();
        return cachedDeviceId;
      }

      const fresh = generateUuidV4();
      await AsyncStorage.setItem(DEVICE_ID_STORAGE_KEY, fresh);
      cachedDeviceId = fresh;
      return fresh;
    } catch {
      const ephemeral = generateUuidV4();
      cachedDeviceId = ephemeral;
      return ephemeral;
    } finally {
      pendingPromise = null;
    }
  })();

  return pendingPromise;
}
