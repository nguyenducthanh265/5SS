import { Ionicons } from "@expo/vector-icons";
import { Modal, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import {
  getGroupVisual,
  ICON_SIZE,
  MIN_TOUCH_SIZE,
  RADII,
  SPACING,
  type AppTheme,
} from "@/theme/tokens";

interface GuideModalProps {
  visible: boolean;
  theme: AppTheme;
  onClose: () => void;
}

const GUIDE_GROUPS = [
  {
    id: "group_1_recyclable" as const,
    title: "Nhóm 1: Rác có khả năng tái sử dụng, tái chế",
    detail: "Giấy, bìa carton khô, chai nhựa sạch, lon kim loại, thủy tinh, vỏ hộp sữa đã tráng sạch & ép dẹp.",
  },
  {
    id: "group_2_food" as const,
    title: "Nhóm 2: Chất thải thực phẩm",
    detail: "Thức ăn thừa, rau củ quả hỏng, vỏ trái cây, bã cà phê, phần thải bỏ từ thịt cá (chắt ráo nước).",
  },
  {
    id: "group_3_other" as const,
    title: "Nhóm 3: Chất thải sinh hoạt khác",
    detail: "Túi nilon dính dầu mỡ, hộp xốp bẩn, vỉ thuốc ghép nhôm-nhựa, giấy vệ sinh, tã bỉm.",
  },
  {
    id: "group_3_hazardous" as const,
    title: "Nhóm 3 (Nguy hại): Tách riêng tuyệt đối",
    detail: "Pin thải, bóng đèn huỳnh quang, nhiệt kế thủy ngân, vỏ hóa chất -> mang tới điểm thu hồi pin/nguy hại.",
  },
];

const TRICKY_CASES = [
  {
    item: "Vỏ hộp sữa giấy",
    rule: "Đổ cạn, tráng sơ, ép dẹp -> Nhóm 1 (Tái chế / bán phế liệu).",
  },
  {
    item: "Túi nilon / hộp xốp dính dầu mỡ",
    rule: "Khó làm sạch -> Nhóm 3 (Rác thải còn lại), không bỏ tái chế.",
  },
  {
    item: "Pin tiểu, pin cúc áo",
    rule: "Chất thải nguy hại -> Dán băng keo hai đầu, đưa tới điểm thu hồi pin.",
  },
  {
    item: "Vỉ thuốc rỗng (nhôm-nhựa)",
    rule: "Vật liệu ghép khó tách -> Nhóm 3 (Rác thải còn lại).",
  },
];

export function GuideModal({ visible, theme, onClose }: GuideModalProps) {
  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}>
      <View style={[styles.overlay, { backgroundColor: theme.scrim }]}>
        <View
          accessibilityViewIsModal
          style={[
            styles.sheet,
            { backgroundColor: theme.surface, borderColor: theme.border },
          ]}>
          <View style={[styles.header, { borderBottomColor: theme.border }]}>
            <View style={styles.headerTitleWrap}>
              <Ionicons name="book-outline" size={ICON_SIZE.md} color={theme.primary} />
              <View style={styles.headerTexts}>
                <Text style={[styles.title, { color: theme.textPrimary }]}>
                  Quyết định 87/2025/QĐ-UBND
                </Text>
                <Text style={[styles.subtitle, { color: theme.textSecondary }]}>
                  Áp dụng tại Hà Nội từ 08/01/2026
                </Text>
              </View>
            </View>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Đóng hướng dẫn quy định Hà Nội"
              hitSlop={8}
              onPress={onClose}
              style={({ pressed }) => [
                styles.closeBtn,
                { backgroundColor: theme.surfaceMuted, opacity: pressed ? 0.8 : 1 },
              ]}>
              <Ionicons name="close" size={ICON_SIZE.md} color={theme.textPrimary} />
            </Pressable>
          </View>

          <ScrollView contentContainerStyle={styles.body}>
            <Text style={[styles.sectionTitle, { color: theme.textPrimary }]}>
              3 nhóm phân loại chính tại nguồn
            </Text>
            {GUIDE_GROUPS.map((g) => {
              const vis = getGroupVisual(g.id, theme.isDark);
              return (
                <View
                  key={g.id}
                  style={[
                    styles.groupCard,
                    { backgroundColor: vis.bg, borderColor: vis.border },
                  ]}>
                  <View style={styles.groupRow}>
                    <Ionicons name={vis.icon} size={18} color={vis.text} />
                    <Text style={[styles.groupTitle, { color: vis.text }]}>
                      {g.title}
                    </Text>
                  </View>
                  <Text style={[styles.groupDetail, { color: vis.text }]}>
                    {g.detail}
                  </Text>
                </View>
              );
            })}

            <Text style={[styles.sectionTitle, { color: theme.textPrimary }]}>
              Các món dễ nhầm khi đứng ở thùng rác
            </Text>
            {TRICKY_CASES.map((tc) => (
              <View
                key={tc.item}
                style={[
                  styles.trickyCard,
                  { backgroundColor: theme.surfaceMuted, borderColor: theme.border },
                ]}>
                <Text style={[styles.trickyItem, { color: theme.textPrimary }]}>
                  {tc.item}
                </Text>
                <Text style={[styles.trickyRule, { color: theme.textSecondary }]}>
                  {tc.rule}
                </Text>
              </View>
            ))}

            <View
              style={[
                styles.noticeBox,
                { backgroundColor: theme.civicBlueSoft, borderColor: theme.civicBlue },
              ]}>
              <Ionicons name="time" size={18} color={theme.civicBlueText} />
              <Text style={[styles.noticeText, { color: theme.civicBlueText }]}>
                Giờ tập kết rác nội đô: 18:00 - 22:00. Đơn vị thu gom có quyền từ chối thu gom nếu không phân loại đúng.
              </Text>
            </View>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: "flex-end",
    paddingTop: 48,
  },
  sheet: {
    maxHeight: "90%",
    borderTopLeftRadius: RADII.xl,
    borderTopRightRadius: RADII.xl,
    borderTopWidth: 1,
    overflow: "hidden",
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: SPACING.lg,
    paddingVertical: SPACING.md,
    borderBottomWidth: 1,
    gap: SPACING.sm,
  },
  headerTitleWrap: { flexDirection: "row", alignItems: "center", gap: SPACING.sm, flex: 1 },
  headerTexts: { flex: 1 },
  title: { fontSize: 16, fontWeight: "800" },
  subtitle: { fontSize: 12 },
  closeBtn: {
    width: MIN_TOUCH_SIZE,
    height: MIN_TOUCH_SIZE,
    borderRadius: RADII.pill,
    alignItems: "center",
    justifyContent: "center",
  },
  body: {
    padding: SPACING.lg,
    gap: SPACING.md,
    paddingBottom: SPACING.xxl,
  },
  sectionTitle: { fontSize: 15, fontWeight: "800", marginTop: 4 },
  groupCard: {
    borderRadius: RADII.md,
    borderWidth: 1,
    padding: SPACING.md,
    gap: 4,
  },
  groupRow: { flexDirection: "row", alignItems: "center", gap: 6 },
  groupTitle: { fontSize: 14, fontWeight: "800", flex: 1 },
  groupDetail: { fontSize: 13, lineHeight: 19 },
  trickyCard: {
    borderRadius: RADII.md,
    borderWidth: 1,
    padding: SPACING.md,
    gap: 2,
  },
  trickyItem: { fontSize: 14, fontWeight: "700" },
  trickyRule: { fontSize: 13, lineHeight: 19 },
  noticeBox: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: SPACING.sm,
    borderRadius: RADII.md,
    borderWidth: 1,
    padding: SPACING.md,
  },
  noticeText: { flex: 1, fontSize: 13, lineHeight: 19, fontWeight: "600" },
});

