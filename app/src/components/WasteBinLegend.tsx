import { Ionicons } from "@expo/vector-icons";
import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import {
  getGroupVisual,
  RADII,
  SPACING,
  type AppTheme,
  type GroupVisualStyle,
} from "@/theme/tokens";
import type { WasteGroupId } from "@/types/waste";

const PRIMARY_BIN_ORDER: readonly WasteGroupId[] = [
  "group_1_recyclable",
  "group_2_food",
  "group_3_other",
  "group_3_hazardous",
];

interface WasteBinGraphicProps {
  visual: GroupVisualStyle;
  isHazardous?: boolean;
  size?: "sm" | "md";
}

/**
 * Biểu tượng thùng rác có nắp & màu chuẩn theo sơ đồ 4 thùng (Xanh lá / Vàng / Đỏ / Đen).
 */
export function WasteBinGraphic({
  visual,
  isHazardous = false,
  size = "md",
}: WasteBinGraphicProps) {
  const isSmall = size === "sm";
  const bodyW = isSmall ? 34 : 50;
  const bodyH = isSmall ? 38 : 54;
  const lidW = isSmall ? 40 : 58;

  return (
    <View style={styles.binGraphicWrap}>
      <View
        style={[
          styles.binHandle,
          {
            width: isSmall ? 12 : 16,
            height: isSmall ? 3 : 4,
            backgroundColor: visual.binLidBg,
          },
        ]}
      />
      <View
        style={[
          styles.binLid,
          {
            width: lidW,
            height: isSmall ? 6 : 8,
            backgroundColor: visual.binLidBg,
          },
        ]}
      />
      <View
        style={[
          styles.binBody,
          {
            width: bodyW,
            height: bodyH,
            backgroundColor: visual.binBg,
            borderColor: isHazardous ? "#FACC15" : "rgba(255,255,255,0.28)",
          },
        ]}>
        <Ionicons
          name={visual.binInnerIcon}
          size={isSmall ? 17 : 24}
          color={visual.binInk}
        />
        {!isSmall && isHazardous && (
          <Text style={styles.hazardBinLabel}>NGUY HẠI</Text>
        )}
      </View>
    </View>
  );
}

interface WasteBinLegendProps {
  theme: AppTheme;
  activeGroupIds?: readonly WasteGroupId[];
  onQuickScanGroup?: (groupId: WasteGroupId, visual: GroupVisualStyle) => void;
}

/**
 * Bảng 4 nhãn thùng phân loại trực quan ("nhìn là biết bỏ thùng nào"):
 * Xanh lá (Tái chế) -> Vàng (Hữu cơ) -> Đỏ (Vô cơ) -> Đen (Nguy hại) + đích xử lý.
 */
export function WasteBinLegend({
  theme,
  activeGroupIds = [],
  onQuickScanGroup,
}: WasteBinLegendProps) {
  const [selectedId, setSelectedId] = useState<WasteGroupId | null>(null);
  const effectiveSelected = selectedId
    ? { id: selectedId, visual: getGroupVisual(selectedId, theme.isDark) }
    : null;

  return (
    <View
      style={[
        styles.wrapper,
        { backgroundColor: theme.surfaceGlass, borderColor: theme.border },
      ]}>
      <View style={styles.headerRow}>
        <View style={styles.headerTextWrap}>
          <Text style={[styles.heading, { color: theme.textPrimary }]}>
            Nhìn nhanh 4 thùng phân loại rác
          </Text>
          <Text style={[styles.subheading, { color: theme.textSecondary }]}>
            Chạm vào từng thùng để xem ví dụ &amp; bấm soi ngay
          </Text>
        </View>
      </View>

      <View style={styles.grid}>
        {PRIMARY_BIN_ORDER.map((groupId) => {
          const vis = getGroupVisual(groupId, theme.isDark);
          const isSelected = selectedId === groupId;
          const isMatched = activeGroupIds.includes(groupId);
          const isHazardous = groupId === "group_3_hazardous";

          return (
            <Pressable
              key={groupId}
              accessibilityRole="button"
              accessibilityLabel={`${vis.binColorName}: ${vis.binName}. Ví dụ: ${vis.examples}. Đưa tới: ${vis.shortDestination}`}
              accessibilityState={{ selected: isSelected }}
              onPress={() => setSelectedId((prev) => (prev === groupId ? null : groupId))}
              style={({ pressed }) => [
                styles.binCard,
                {
                  backgroundColor: isSelected || isMatched ? vis.bg : theme.surface,
                  borderColor:
                    isSelected || isMatched ? vis.binBg : theme.border,
                  borderWidth: isSelected || isMatched ? 2 : 1,
                  opacity: pressed ? 0.88 : 1,
                },
              ]}>
              {isMatched && (
                <View style={[styles.matchedPill, { backgroundColor: vis.binBg }]}>
                  <Text style={[styles.matchedText, { color: vis.binInk }]}>
                    Đồ vừa soi
                  </Text>
                </View>
              )}

              <Text
                style={[styles.examplesHint, { color: theme.textSecondary }]}
                numberOfLines={2}>
                {vis.examples}
              </Text>

              <WasteBinGraphic visual={vis} isHazardous={isHazardous} size="md" />

              <View style={styles.labelBlock}>
                <View
                  style={[
                    styles.colorTag,
                    { backgroundColor: vis.binBg },
                  ]}>
                  <Text style={[styles.colorTagText, { color: vis.binInk }]}>
                    {vis.binColorName}
                  </Text>
                </View>
                <Text
                  style={[
                    styles.binTitle,
                    { color: isSelected || isMatched ? vis.text : theme.textPrimary },
                  ]}>
                  {vis.binName}
                </Text>
              </View>

              <View style={[styles.destRow, { borderTopColor: theme.border }]}>
                <Ionicons name="arrow-down" size={12} color={vis.accent} />
                <Text
                  style={[
                    styles.destText,
                    { color: isSelected || isMatched ? vis.text : theme.textSecondary },
                  ]}
                  numberOfLines={1}>
                  {vis.shortDestination}
                </Text>
              </View>
            </Pressable>
          );
        })}
      </View>

      {effectiveSelected && (
        <View
          style={[
            styles.detailDrawer,
            {
              backgroundColor: effectiveSelected.visual.bg,
              borderColor: effectiveSelected.visual.border,
            },
          ]}>
          <View style={styles.detailHeader}>
            <View style={styles.detailTitleRow}>
              <Ionicons
                name={effectiveSelected.visual.icon}
                size={18}
                color={effectiveSelected.visual.text}
              />
              <Text style={[styles.detailTitle, { color: effectiveSelected.visual.text }]}>
                {effectiveSelected.visual.label}
              </Text>
            </View>
            <Text style={[styles.detailLegal, { color: effectiveSelected.visual.text }]}>
              {effectiveSelected.visual.legalTag}
            </Text>
          </View>

          <Text style={[styles.detailLine, { color: effectiveSelected.visual.text }]}>
            • Ví dụ thường gặp: {effectiveSelected.visual.examples}
          </Text>
          <Text style={[styles.detailLine, { color: effectiveSelected.visual.text }]}>
            • Hướng xử lý: {effectiveSelected.visual.destination}
          </Text>
          <Text style={[styles.detailLine, { color: effectiveSelected.visual.text }]}>
            • Cách bỏ đúng: {effectiveSelected.visual.binHint}
          </Text>

          {onQuickScanGroup && (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={`Soi rác nhóm ${effectiveSelected.visual.binName}`}
              onPress={() => onQuickScanGroup(effectiveSelected.id, effectiveSelected.visual)}
              style={({ pressed }) => [
                styles.quickScanBtn,
                {
                  backgroundColor: effectiveSelected.visual.binBg,
                  opacity: pressed ? 0.88 : 1,
                },
              ]}>
              <Ionicons
                name="camera"
                size={16}
                color={effectiveSelected.visual.binInk}
              />
              <Text
                style={[
                  styles.quickScanText,
                  { color: effectiveSelected.visual.binInk },
                ]}>
                Kiểm tra đồ {effectiveSelected.visual.binName.toLowerCase()} ngay
              </Text>
            </Pressable>
          )}
        </View>
      )}

      <View
        style={[
          styles.sloganBar,
          { backgroundColor: theme.civicBlueSoft, borderColor: theme.civicBlue },
        ]}>
        <Ionicons name="sparkles-outline" size={14} color={theme.civicBlueText} />
        <Text style={[styles.sloganText, { color: theme.civicBlueText }]}>
          Rác không được phân loại chỉ là rác · Rác được phân loại là tài nguyên
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    borderRadius: RADII.lg,
    borderWidth: 1,
    padding: SPACING.md,
    gap: SPACING.md,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  headerTextWrap: { gap: 2, flex: 1 },
  heading: { fontSize: 15, fontWeight: "800" },
  subheading: { fontSize: 12 },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: SPACING.sm,
  },
  binCard: {
    flexGrow: 1,
    flexBasis: "47%",
    minWidth: 140,
    borderRadius: RADII.md,
    padding: SPACING.sm + 2,
    alignItems: "center",
    gap: 8,
    position: "relative",
  },
  matchedPill: {
    position: "absolute",
    top: 6,
    right: 6,
    paddingHorizontal: 7,
    paddingVertical: 2,
    borderRadius: RADII.pill,
  },
  matchedText: { fontSize: 10, fontWeight: "800" },
  examplesHint: {
    fontSize: 11,
    lineHeight: 15,
    textAlign: "center",
    minHeight: 30,
    fontWeight: "600",
  },
  binGraphicWrap: {
    alignItems: "center",
    justifyContent: "center",
  },
  binHandle: {
    borderTopLeftRadius: 3,
    borderTopRightRadius: 3,
    marginBottom: 1,
  },
  binLid: {
    borderRadius: 4,
    marginBottom: 2,
  },
  binBody: {
    borderBottomLeftRadius: 10,
    borderBottomRightRadius: 10,
    borderTopLeftRadius: 3,
    borderTopRightRadius: 3,
    borderWidth: 1.5,
    alignItems: "center",
    justifyContent: "center",
    gap: 2,
  },
  hazardBinLabel: {
    color: "#FFFFFF",
    fontSize: 7,
    fontWeight: "900",
    letterSpacing: 0.4,
  },
  labelBlock: {
    alignItems: "center",
    gap: 4,
  },
  colorTag: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: RADII.pill,
  },
  colorTagText: {
    fontSize: 11,
    fontWeight: "800",
  },
  binTitle: {
    fontSize: 14,
    fontWeight: "900",
    textAlign: "center",
  },
  destRow: {
    width: "100%",
    borderTopWidth: 1,
    paddingTop: 6,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 4,
  },
  destText: {
    fontSize: 11,
    fontWeight: "700",
    flexShrink: 1,
  },
  detailDrawer: {
    borderRadius: RADII.md,
    borderWidth: 1,
    padding: SPACING.md,
    gap: 6,
  },
  detailHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    flexWrap: "wrap",
    gap: 6,
    marginBottom: 2,
  },
  detailTitleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  detailTitle: { fontSize: 14, fontWeight: "800" },
  detailLegal: { fontSize: 11, fontWeight: "700", opacity: 0.85 },
  detailLine: { fontSize: 12.5, lineHeight: 18 },
  quickScanBtn: {
    marginTop: 6,
    borderRadius: RADII.md,
    paddingVertical: 10,
    paddingHorizontal: SPACING.md,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
  },
  quickScanText: { fontSize: 13, fontWeight: "800" },
  sloganBar: {
    borderRadius: RADII.sm,
    borderWidth: 1,
    paddingVertical: 7,
    paddingHorizontal: SPACING.sm + 2,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
  },
  sloganText: {
    fontSize: 11.5,
    fontWeight: "700",
    textAlign: "center",
    flexShrink: 1,
  },
});

