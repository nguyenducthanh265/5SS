import { Ionicons } from "@expo/vector-icons";
import { Pressable, StyleSheet, Text, View } from "react-native";

import type { ClassifyWasteResponse } from "@/services/wasteApi";
import { ICON_SIZE, MIN_TOUCH_SIZE, RADII, SPACING, type AppTheme } from "@/theme/tokens";

interface StatusBannerProps {
  response: Exclude<ClassifyWasteResponse, { status: "ai" }>;
  theme: AppTheme;
  onRetry?: () => void;
}

export function StatusBanner({ response, theme, onRetry }: StatusBannerProps) {
  if (response.status === "fallback") {
    const onWarningSolid = theme.isDark ? "#451A03" : "#FFFFFF";
    return (
      <View
        accessibilityRole="alert"
        accessibilityLiveRegion="polite"
        style={[
          styles.card,
          { backgroundColor: theme.warningBg, borderColor: theme.warningBorder },
        ]}>
        <View style={styles.headerRow}>
          <View
            style={[
              styles.badge,
              { backgroundColor: theme.warningText },
            ]}>
            <Ionicons name="cloud-offline" size={14} color={onWarningSolid} />
            <Text style={[styles.badgeText, { color: onWarningSolid }]}>
              {response.badge.toUpperCase()}
            </Text>
          </View>
          <Text style={[styles.latency, { color: theme.warningText }]}>
            {response.latencyMs} ms
          </Text>
        </View>

        <Text style={[styles.title, { color: theme.warningText }]}>
          Chưa nhận được phân loại AI trực tiếp
        </Text>
        <Text style={[styles.body, { color: theme.warningText }]}>
          Hệ thống đang hiển thị phản hồi dự phòng ({response.reason}). Không tính là kết quả AI thật.
        </Text>
        {!!response.rawOutput && (
          <View style={[styles.sampleBox, { backgroundColor: theme.surface }]}>
            <Text style={[styles.sampleText, { color: theme.textSecondary }]}>
              {response.rawOutput}
            </Text>
          </View>
        )}
        {onRetry && (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel="Thử phân loại lại bằng AI"
            onPress={onRetry}
            style={({ pressed }) => [
              styles.retryBtn,
              { backgroundColor: theme.warningText, opacity: pressed ? 0.85 : 1 },
            ]}>
            <Ionicons name="refresh" size={16} color={onWarningSolid} />
            <Text style={[styles.retryBtnText, { color: onWarningSolid }]}>Thử lại</Text>
          </Pressable>
        )}
      </View>
    );
  }

  const isBusy = response.status === "busy";
  const title =
    response.status === "parse_error"
      ? "Dữ liệu trả về chưa đúng định dạng"
      : isBusy
        ? "Máy chủ AI đang bận"
        : response.status === "timeout"
          ? "Quá thời gian chờ AI"
          : response.status === "config_error"
            ? "Thiếu cấu hình máy chủ"
            : "Lỗi kết nối máy chủ";

  const detail =
    response.status === "parse_error"
      ? `Không đọc được schema kết quả (${response.reason}).`
      : response.message;

  const iconName = isBusy
    ? "hourglass-outline"
    : response.status === "network"
      ? "wifi-outline"
      : "alert-circle";

  return (
    <View
      accessibilityRole="alert"
      accessibilityLiveRegion="assertive"
      style={[
        styles.card,
        { backgroundColor: theme.dangerBg, borderColor: theme.dangerBorder },
      ]}>
      <View style={styles.headerRow}>
        <View style={styles.iconTitle}>
          <Ionicons name={iconName} size={ICON_SIZE.md} color={theme.dangerText} />
          <Text style={[styles.title, { color: theme.dangerText }]}>{title}</Text>
        </View>
      </View>
      <Text style={[styles.body, { color: theme.dangerText }]}>{detail}</Text>
      {onRetry && response.status !== "config_error" && (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Thử lại yêu cầu phân loại"
          onPress={onRetry}
          style={({ pressed }) => [
            styles.retryBtn,
            { backgroundColor: theme.dangerSolid, opacity: pressed ? 0.85 : 1 },
          ]}>
          <Ionicons name="refresh" size={16} color={theme.onDangerSolid} />
          <Text style={[styles.retryBtnText, { color: theme.onDangerSolid }]}>
            Thử lại
          </Text>
        </Pressable>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: RADII.lg,
    borderWidth: 1.5,
    padding: SPACING.lg,
    gap: SPACING.sm,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: SPACING.sm,
  },
  iconTitle: { flexDirection: "row", alignItems: "center", gap: SPACING.sm, flex: 1 },
  badge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: RADII.pill,
  },
  badgeText: { color: "#FFFFFF", fontSize: 12, fontWeight: "800" },
  latency: { fontSize: 12, fontWeight: "700" },
  title: { fontSize: 15, fontWeight: "800", flexShrink: 1 },
  body: { fontSize: 14, lineHeight: 20 },
  sampleBox: {
    borderRadius: RADII.md,
    padding: SPACING.md,
  },
  sampleText: { fontSize: 13, lineHeight: 19 },
  retryBtn: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    minHeight: MIN_TOUCH_SIZE,
    paddingHorizontal: 16,
    borderRadius: RADII.pill,
    marginTop: 4,
  },
  retryBtnText: { color: "#FFFFFF", fontSize: 14, fontWeight: "700" },
});

