/**
 * Kiểu dữ liệu & parser an toàn cho kết quả phân loại rác Hà Nội (QĐ 87/2025/QĐ-UBND).
 * Khớp hợp đồng JSON từ `serve/app_llm.py` mô tả trong `ARCHITECTURE.md`.
 */

export type WasteGroupId =
  | "group_1_recyclable"
  | "group_2_food"
  | "group_3_other"
  | "group_3_bulky"
  | "group_3_hazardous"
  | (string & {});

export type DropoffPoint =
  | string
  | {
      name: string;
      area?: string;
      address?: string;
      district?: string;
      note?: string;
      note_vi?: string;
    };

export interface WasteItem {
  name_vi: string;
  item_key: string;
  material: string;
  dirty_oily: boolean;
  group_id: WasteGroupId;
  group_name_vi: string;
  group_short_label?: string;
  is_hazardous?: boolean;
  rinse_required: boolean;
  sell_for_recycling: boolean;
  dropoff_points: DropoffPoint[];
  note_vi: string;
}

export interface WasteResult {
  items: WasteItem[];
  mixed_bag: boolean;
  mixed_bag_reason_vi: string;
  has_hazardous: boolean;
  dropoff_summary: DropoffPoint[];
  collection_window_vi: string;
  speech_vi: string;
}

export type ParseWasteOutcome =
  | { ok: true; data: WasteResult }
  | { ok: false; reason: string };

function isRecord(val: unknown): val is Record<string, unknown> {
  return typeof val === "object" && val !== null && !Array.isArray(val);
}

function asNonEmptyString(val: unknown): string | null {
  return typeof val === "string" && val.trim().length > 0 ? val : null;
}

function asString(val: unknown, fallback = ""): string {
  return typeof val === "string" ? val : fallback;
}

function asBoolean(val: unknown, fallback = false): boolean {
  return typeof val === "boolean" ? val : fallback;
}

function normalizeDropoffList(val: unknown): DropoffPoint[] {
  if (!Array.isArray(val)) return [];
  const out: DropoffPoint[] = [];
  for (const entry of val) {
    if (typeof entry === "string" && entry.trim()) {
      out.push(entry);
    } else if (isRecord(entry) && typeof entry.name === "string" && entry.name.trim()) {
      out.push({
        name: entry.name,
        area: typeof entry.area === "string" ? entry.area : undefined,
        address: typeof entry.address === "string" ? entry.address : undefined,
        district: typeof entry.district === "string" ? entry.district : undefined,
        note: typeof entry.note === "string" ? entry.note : undefined,
        note_vi: typeof entry.note_vi === "string" ? entry.note_vi : undefined,
      });
    }
  }
  return out;
}

function parseItem(raw: unknown, index: number): { ok: true; item: WasteItem } | { ok: false; reason: string } {
  if (!isRecord(raw)) {
    return { ok: false, reason: `items[${index}] không phải object` };
  }
  const name_vi = asNonEmptyString(raw.name_vi);
  const group_id = asNonEmptyString(raw.group_id);
  const group_name_vi = asNonEmptyString(raw.group_name_vi);
  if (!name_vi || !group_id || !group_name_vi) {
    return { ok: false, reason: `items[${index}] thiếu name_vi, group_id hoặc group_name_vi` };
  }

  return {
    ok: true,
    item: {
      name_vi,
      item_key: asString(raw.item_key, "unknown"),
      material: asString(raw.material, ""),
      dirty_oily: asBoolean(raw.dirty_oily, false),
      group_id,
      group_name_vi,
      group_short_label: asString(raw.group_short_label, "") || undefined,
      is_hazardous: typeof raw.is_hazardous === "boolean" ? raw.is_hazardous : undefined,
      rinse_required: asBoolean(raw.rinse_required, false),
      sell_for_recycling: asBoolean(raw.sell_for_recycling, false),
      dropoff_points: normalizeDropoffList(raw.dropoff_points),
      note_vi: asString(raw.note_vi, ""),
    },
  };
}

function extractBalancedJsonObject(text: string): string | null {
  const start = text.indexOf("{");
  if (start === -1) return null;

  let depth = 0;
  let inString = false;
  let escaped = false;

  for (let i = start; i < text.length; i += 1) {
    const ch = text[i];
    if (inString) {
      if (escaped) {
        escaped = false;
      } else if (ch === "\\") {
        escaped = true;
      } else if (ch === '"') {
        inString = false;
      }
      continue;
    }

    if (ch === '"') {
      inString = true;
    } else if (ch === "{") {
      depth += 1;
    } else if (ch === "}") {
      depth -= 1;
      if (depth === 0) {
        return text.slice(start, i + 1);
      }
    }
  }
  return null;
}

function parseJsonCandidate(rawText: string): { ok: true; value: unknown } | { ok: false; message: string } {
  const trimmed = rawText.trim();
  if (!trimmed) {
    return { ok: false, message: "Chuỗi JSON rỗng" };
  }

  const candidates: string[] = [trimmed];
  const fenceRegex = /```(?:json)?\s*([\s\S]*?)\s*```/gi;
  for (const match of trimmed.matchAll(fenceRegex)) {
    const inner = match[1]?.trim();
    if (inner) candidates.push(inner);
  }
  const balanced = extractBalancedJsonObject(trimmed);
  if (balanced) {
    candidates.push(balanced);
  }

  let firstError = "JSON không hợp lệ";
  for (let i = 0; i < candidates.length; i += 1) {
    try {
      return { ok: true, value: JSON.parse(candidates[i]) };
    } catch (err) {
      if (i === 0 && err instanceof Error) {
        firstError = err.message;
      }
    }
  }

  return { ok: false, message: `Lỗi JSON.parse: ${firstError}` };
}

/**
 * Parse an toàn chuỗi JSON hoặc object trả về từ backend `/predict`.
 * Hỗ trợ chuỗi có markdown ```json fence hoặc văn bản bao quanh JSON.
 * Không ném exception; trả về `{ ok: true, data }` hoặc `{ ok: false, reason }`.
 */
export function parseWasteResult(raw: unknown): ParseWasteOutcome {
  let parsed: unknown = raw;
  if (typeof raw === "string") {
    const jsonOutcome = parseJsonCandidate(raw);
    if (!jsonOutcome.ok) {
      return { ok: false, reason: jsonOutcome.message };
    }
    parsed = jsonOutcome.value;
  }

  if (!isRecord(parsed)) {
    return { ok: false, reason: "Kết quả không phải JSON object" };
  }

  if (!Array.isArray(parsed.items)) {
    return { ok: false, reason: "Thiếu mảng items" };
  }

  const items: WasteItem[] = [];
  for (let i = 0; i < parsed.items.length; i += 1) {
    const itemRes = parseItem(parsed.items[i], i);
    if (!itemRes.ok) return itemRes;
    items.push(itemRes.item);
  }

  if (typeof parsed.speech_vi !== "string") {
    return { ok: false, reason: "Thiếu trường speech_vi" };
  }

  return {
    ok: true,
    data: {
      items,
      mixed_bag: asBoolean(parsed.mixed_bag, false),
      mixed_bag_reason_vi: asString(parsed.mixed_bag_reason_vi, ""),
      has_hazardous: asBoolean(parsed.has_hazardous, false),
      dropoff_summary: normalizeDropoffList(parsed.dropoff_summary),
      collection_window_vi: asString(parsed.collection_window_vi, ""),
      speech_vi: parsed.speech_vi,
    },
  };
}
