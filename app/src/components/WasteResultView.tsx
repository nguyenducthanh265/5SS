import { Ionicons } from "@expo/vector-icons";
import { Pressable, StyleSheet, Text, View } from "react-native";

import {
  getGroupVisual,
  ICON_SIZE,
  MIN_TOUCH_SIZE,
  RADII,
  SPACING,
  type AppTheme,
} from "@/theme/tokens";
import type { DropoffPoint, WasteResult } from "@/types/waste";

interface WasteResultViewProps {
  result: WasteResult;
  latencyMs: number;
  isSpeakingNow: boolean;
  theme: AppTheme;
  onSpeak: (text: string) => void;
  onStopSpeech: () => void;
}

function formatDropoffPoint(point: DropoffPoint): {
  name: string;
  area?: string;
  note?: string;
} {
  if (typeof point === "string") {
    return { name: point };
  }
  const area = point.area ?? point.address ?? point.district;
  const note = point.note ?? point.note_vi;
  return { name: point.name, area, note };
}

export function WasteResultView({
  result,
  latencyMs,
  isSpeakingNow,
  theme,
  onSpeak,
  onStopSpeech,
}: WasteResultViewProps) {
  const mixedBg = result.has_hazardous ? theme.dangerBg : theme.warningBg;
  const mixedBorder = result.has_hazardous ? theme.dangerBorder : theme.warningBorder;
  const mixedText = result.has_hazardous ? theme.dangerText : theme.warningText;
  const onCivicBlue = theme.isDark ? "#0A1128" : "#FFFFFF";

  return (
    <View style={styles.root}>
      {/* Status bar: AI verified */}
      <View style={styles.metaRow}>
        <View
          style={[
            styles.aiBadge,
            { backgroundColor: theme.primarySoft, borderColor: theme.primary },
          ]}>
          <Ionicons name="sparkles" size={14} color={theme.primarySoftText} />
          <Text style={[styles.aiBadgeText, { color: theme.primarySoftText }]}>
            Kết quả AI trực tiếp · {latencyMs} ms
          </Text>
        </View>
        <Text style={[styles.countText, { color: theme.textSecondary }]}>
          {result.items.length} món nhận diện
        </Text>
      </View>

      {/* Mixed-bag alert */}
      {result.mixed_bag && (
        <View
          accessibilityRole="alert"
          accessibilityLiveRegion="assertive"
          style={[
            styles.alertBox,
            { backgroundColor: mixedBg, borderColor: mixedBorder },
          ]}>
          <Ionicons
            name={result.has_hazardous ? "alert-circle" : "warning"}
            size={ICON_SIZE.md}
            color={mixedText}
          />
          <View style={styles.alertContent}>
            <Text style={[styles.alertTitle, { color: mixedText }]}>
              {result.has_hazardous
                ? "CẢNH BÁO: Túi rác có lẫn chất thải nguy hại"
                : "Cảnh báo: Túi rác đang bị trộn lẫn"}
            </Text>
            <Text style={[styles.alertBody, { color: mixedText }]}>
              {result.mixed_bag_reason_vi ||
                "Cần tách riêng từng nhóm rác theo Quyết định 87/2025/QĐ-UBND."}
            </Text>
          </View>
        </View>
      )}

      {/* Voice readout card */}
      {!!result.speech_vi.trim() && (
        <View
          style={[
            styles.speechCard,
            { backgroundColor: theme.civicBlueSoft, borderColor: theme.civicBlue },
          ]}>
          <View style={styles.speechHeader}>
            <View style={styles.speechTitleRow}>
              <Ionicons name="volume-high" size={ICON_SIZE.sm} color={theme.civicBlueText} />
              <Text style={[styles.speechTitle, { color: theme.civicBlueText }]}>
                Hướng dẫn bằng giọng nói
              </Text>
            </View>
            <View style={styles.speechActions}>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={isSpeakingNow ? "Đang đọc hướng dẫn" : "Nghe lại hướng dẫn tiếng Việt"}
                onPress={() => onSpeak(result.speech_vi)}
                style={({ pressed }) => [
                  styles.speechBtn,
                  {
                    backgroundColor: theme.civicBlue,
                    opacity: pressed ? 0.85 : 1,
                  },
                ]}>
                <Ionicons
                  name={isSpeakingNow ? "radio" : "play"}
                  size={16}
                  color={onCivicBlue}
                />
                <Text style={[styles.speechBtnText, { color: onCivicBlue }]}>
                  {isSpeakingNow ? "Đang đọc..." : "Nghe lại"}
                </Text>
              </Pressable>
              {isSpeakingNow && (
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="Dừng đọc giọng nói"
                  onPress={onStopSpeech}
                  style={({ pressed }) => [
                    styles.speechStopBtn,
                    {
                      backgroundColor: theme.surface,
                      borderColor: theme.civicBlue,
                      opacity: pressed ? 0.85 : 1,
                    },
                  ]}>
                  <Ionicons name="stop" size={16} color={theme.civicBlueText} />
                  <Text style={[styles.speechStopText, { color: theme.civicBlueText }]}>
                    Dừng
                  </Text>
                </Pressable>
              )}
            </View>
          </View>
          <Text style={[styles.speechBody, { color: theme.civicBlueText }]}>
            {result.speech_vi}
          </Text>
        </View>
      )}

      {/* Empty item state */}
      {result.items.length === 0 && (
        <View
          style={[
            styles.emptyCard,
            { backgroundColor: theme.surfaceGlass, borderColor: theme.border },
          ]}>
          <Ionicons name="scan-outline" size={ICON_SIZE.lg} color={theme.textSecondary} />
          <Text style={[styles.emptyTitle, { color: theme.textPrimary }]}>
            Chưa thấy rõ món rác trong khung hình
          </Text>
          <Text style={[styles.emptySubtitle, { color: theme.textSecondary }]}>
            Hãy đưa camera lại gần hơn, đủ ánh sáng và chụp lại.
          </Text>
        </View>
      )}

      {/* Per-item classification cards */}
      {result.items.map((item, idx) => {
        const groupVis = getGroupVisual(item.group_id, theme.isDark);
        return (
          <View
            key={`${item.item_key}-${idx}`}
            style={[
              styles.itemCard,
              { backgroundColor: theme.surfaceGlass, borderColor: theme.border },
            ]}>
            <View
              style={[
                styles.groupPill,
                { backgroundColor: groupVis.bg, borderColor: groupVis.border },
              ]}>
              <Ionicons name={groupVis.icon} size={16} color={groupVis.text} />
              <Text style={[styles.groupPillText, { color: groupVis.text }]}>
                {item.group_name_vi}
              </Text>
            </View>

            <View style={styles.itemHeader}>
              <Text style={[styles.itemName, { color: theme.textPrimary }]}>
                {item.name_vi}
              </Text>
              {item.dirty_oily && (
                <View
                  style={[
                    styles.oilyTag,
                    { backgroundColor: theme.warningBg, borderColor: theme.warningBorder },
                  ]}>
                  <Ionicons name="water" size={13} color={theme.warningText} />
                  <Text style={[styles.oilyTagText, { color: theme.warningText }]}>
                    Dính dầu / bẩn
                  </Text>
                </View>
              )}
            </View>

            <Text style={[styles.materialText, { color: theme.textSecondary }]}>
              {item.material
                ? `Chất liệu: ${item.material} · ${groupVis.binHint}`
                : groupVis.binHint}
            </Text>

            {/* Action chips: Rinse + Resale */}
            <View style={styles.chipRow}>
              <View
                style={[
                  styles.actionChip,
                  {
                    backgroundColor: item.rinse_required
                      ? theme.civicBlueSoft
                      : theme.surfaceMuted,
                    borderColor: item.rinse_required ? theme.civicBlue : theme.border,
                  },
                ]}>
                <Ionicons
                  name={item.rinse_required ? "water-outline" : "checkmark-circle-outline"}
                  size={15}
                  color={item.rinse_required ? theme.civicBlueText : theme.textSecondary}
                />
                <Text
                  style={[
                    styles.actionChipText,
                    {
                      color: item.rinse_required ? theme.civicBlueText : theme.textSecondary,
                    },
                  ]}>
                  {item.rinse_required ? "Cần tráng sạch & ép dẹp" : "Không cần tráng rửa"}
                </Text>
              </View>

              <View
                style={[
                  styles.actionChip,
                  {
                    backgroundColor: item.sell_for_recycling
                      ? theme.primarySoft
                      : theme.surfaceMuted,
                    borderColor: item.sell_for_recycling ? theme.primary : theme.border,
                  },
                ]}>
                <Ionicons
                  name={item.sell_for_recycling ? "cash-outline" : "close-circle-outline"}
                  size={15}
                  color={item.sell_for_recycling ? theme.primarySoftText : theme.textSecondary}
                />
                <Text
                  style={[
                    styles.actionChipText,
                    {
                      color: item.sell_for_recycling
                        ? theme.primarySoftText
                        : theme.textSecondary,
                    },
                  ]}>
                  {item.sell_for_recycling ? "Bán ve chai được" : "Không bán ve chai"}
                </Text>
              </View>
            </View>

            {!!item.note_vi && (
              <View
                style={[
                  styles.noteBox,
                  { backgroundColor: theme.surfaceMuted },
                ]}>
                <Ionicons name="information-circle" size={16} color={theme.textSecondary} />
                <Text style={[styles.noteText, { color: theme.textPrimary }]}>
                  {item.note_vi}
                </Text>
              </View>
            )}
          </View>
        );
      })}

      {/* Dropoff points for batteries / hazardous items */}
      {result.dropoff_summary.length > 0 && (
        <View
          style={[
            styles.dropoffCard,
            { backgroundColor: theme.dangerBg, borderColor: theme.dangerBorder },
          ]}>
          <View style={styles.dropoffHeader}>
            <Ionicons name="location" size={ICON_SIZE.sm} color={theme.dangerText} />
            <Text style={[styles.dropoffTitle, { color: theme.dangerText }]}>
              Điểm thu hồi pin / rác nguy hại tại Hà Nội
            </Text>
          </View>
          {result.dropoff_summary.map((pt, idx) => {
            const info = formatDropoffPoint(pt);
            return (
              <View
                key={`${info.name}-${idx}`}
                style={[
                  styles.dropoffItem,
                  { backgroundColor: theme.surface, borderColor: theme.dangerBorder },
                ]}>
                <Text style={[styles.dropoffName, { color: theme.textPrimary }]}>
                  {info.name}
                </Text>
                {!!info.area && (
                  <Text style={[styles.dropoffMeta, { color: theme.textSecondary }]}>
                    Khu vực: {info.area}
                  </Text>
                )}
                {!!info.note && (
                  <Text style={[styles.dropoffMeta, { color: theme.textSecondary }]}>
                    {info.note}
                  </Text>
                )}
              </View>
            );
          })}
        </View>
      )}

      {/* Hanoi collection time window */}
      {!!result.collection_window_vi && (
        <View
          style={[
            styles.windowFooter,
            { backgroundColor: theme.surfaceGlass, borderColor: theme.border },
          ]}>
          <Ionicons name="time-outline" size={18} color={theme.textSecondary} />
          <View style={styles.windowTextWrap}>
            <Text style={[styles.windowTitle, { color: theme.textPrimary }]}>
              Khung giờ tập kết nội đô Hà Nội
            </Text>
            <Text style={[styles.windowDesc, { color: theme.textSecondary }]}>
              {result.collection_window_vi}
            </Text>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { gap: SPACING.md },
  metaRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: SPACING.sm,
    flexWrap: "wrap",
  },
  aiBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: RADII.pill,
    borderWidth: 1,
  },
  aiBadgeText: { fontSize: 12, fontWeight: "700" },
  countText: { fontSize: 13, fontWeight: "600" },
  alertBox: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: SPACING.md,
    padding: SPACING.lg,
    borderRadius: RADII.lg,
    borderWidth: 1.5,
  },
  alertContent: { flex: 1, gap: 4 },
  alertTitle: { fontSize: 15, fontWeight: "800" },
  alertBody: { fontSize: 14, lineHeight: 20 },
  speechCard: {
    borderRadius: RADII.lg,
    borderWidth: 1,
    padding: SPACING.lg,
    gap: SPACING.sm,
  },
  speechHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: SPACING.sm,
    flexWrap: "wrap",
  },
  speechTitleRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  speechTitle: { fontSize: 14, fontWeight: "700" },
  speechActions: { flexDirection: "row", alignItems: "center", gap: SPACING.sm },
  speechBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    minHeight: MIN_TOUCH_SIZE,
    paddingHorizontal: 14,
    borderRadius: RADII.pill,
  },
  speechBtnText: { color: "#FFFFFF", fontSize: 13, fontWeight: "700" },
  speechStopBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    minHeight: MIN_TOUCH_SIZE,
    paddingHorizontal: 12,
    borderRadius: RADII.pill,
    borderWidth: 1,
  },
  speechStopText: { fontSize: 13, fontWeight: "700" },
  speechBody: { fontSize: 14, lineHeight: 21 },
  emptyCard: {
    borderRadius: RADII.lg,
    borderWidth: 1,
    padding: SPACING.xl,
    alignItems: "center",
    gap: SPACING.sm,
  },
  emptyTitle: { fontSize: 15, fontWeight: "700", textAlign: "center" },
  emptySubtitle: { fontSize: 13, textAlign: "center", lineHeight: 19 },
  itemCard: {
    borderRadius: RADII.lg,
    borderWidth: 1,
    padding: SPACING.lg,
    gap: SPACING.sm,
  },
  groupPill: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: RADII.pill,
    borderWidth: 1,
  },
  groupPillText: { fontSize: 12, fontWeight: "700", flexShrink: 1 },
  itemHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: SPACING.sm,
    flexWrap: "wrap",
  },
  itemName: { fontSize: 18, fontWeight: "800", flexShrink: 1 },
  oilyTag: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: RADII.sm,
    borderWidth: 1,
  },
  oilyTagText: { fontSize: 12, fontWeight: "700" },
  materialText: { fontSize: 13, lineHeight: 19 },
  chipRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: SPACING.sm,
    marginTop: 2,
  },
  actionChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: RADII.sm,
    borderWidth: 1,
  },
  actionChipText: { fontSize: 13, fontWeight: "600" },
  noteBox: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
    padding: SPACING.md,
    borderRadius: RADII.md,
    marginTop: 2,
  },
  noteText: { flex: 1, fontSize: 13, lineHeight: 19 },
  dropoffCard: {
    borderRadius: RADII.lg,
    borderWidth: 1,
    padding: SPACING.lg,
    gap: SPACING.sm,
  },
  dropoffHeader: { flexDirection: "row", alignItems: "center", gap: 6 },
  dropoffTitle: { fontSize: 14, fontWeight: "800", flex: 1 },
  dropoffItem: {
    borderRadius: RADII.md,
    borderWidth: 1,
    padding: SPACING.md,
    gap: 3,
  },
  dropoffName: { fontSize: 14, fontWeight: "700" },
  dropoffMeta: { fontSize: 13, lineHeight: 18 },
  windowFooter: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: SPACING.md,
    borderRadius: RADII.lg,
    borderWidth: 1,
    padding: SPACING.lg,
  },
  windowTextWrap: { flex: 1, gap: 2 },
  windowTitle: { fontSize: 13, fontWeight: "700" },
  windowDesc: { fontSize: 13, lineHeight: 19 },
});

