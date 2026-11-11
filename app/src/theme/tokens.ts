import type { Ionicons } from "@expo/vector-icons";
import { Platform } from "react-native";

import type { WasteGroupId } from "@/types/waste";

export type IoniconName = React.ComponentProps<typeof Ionicons>["name"];

export const SPACING = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const RADII = {
  sm: 10,
  md: 14,
  lg: 18,
  xl: 24,
  pill: 999,
} as const;

/** Native touch target minimum: 44pt iOS / 48dp Android. */
export const MIN_TOUCH_SIZE = Platform.select({ ios: 44, android: 48, default: 44 });

export const ICON_SIZE = {
  sm: 18,
  md: 22,
  lg: 26,
} as const;

export interface AppTheme {
  isDark: boolean;
  bg: string;
  bgGradient: readonly [string, string, string];
  ctaGradient: readonly [string, string];
  surface: string;
  surfaceGlass: string;
  surfaceMuted: string;
  textPrimary: string;
  textSecondary: string;
  border: string;
  primary: string;
  onPrimary: string;
  primarySoft: string;
  primarySoftText: string;
  civicBlue: string;
  civicBlueSoft: string;
  civicBlueText: string;
  haloOuter: string;
  haloMid: string;
  haloCore: string;
  waveTop: string;
  waveBottom: string;
  warningBg: string;
  warningBorder: string;
  warningText: string;
  dangerBg: string;
  dangerBorder: string;
  dangerText: string;
  dangerSolid: string;
  onDangerSolid: string;
  scrim: string;
}

/**
 * Mangrove Flow ("Điều Hòa Dòng Chảy") Palette:
 * Sky-periwinkle + flowing jade-teal currents + deep indigo ink + warm solar halo.
 */
export const LIGHT_THEME: AppTheme = {
  isDark: false,
  bg: "#E9F0FF",
  bgGradient: ["#E5EBFF", "#DBF4ED", "#E4EEFF"],
  ctaGradient: ["#0F766E", "#15803D"],
  surface: "#FFFFFF",
  surfaceGlass: "rgba(255, 255, 255, 0.88)",
  surfaceMuted: "rgba(235, 243, 255, 0.92)",
  textPrimary: "#14224A",
  textSecondary: "#3B4D7A",
  border: "#C7D7FE",
  primary: "#0F766E",
  onPrimary: "#FFFFFF",
  primarySoft: "#D1FAE5",
  primarySoftText: "#064E3B",
  civicBlue: "#1D4ED8",
  civicBlueSoft: "#E0EAFF",
  civicBlueText: "#1E3A8A",
  haloOuter: "rgba(167, 243, 208, 0.45)",
  haloMid: "rgba(254, 243, 199, 0.65)",
  haloCore: "#FEF9C3",
  waveTop: "rgba(52, 211, 153, 0.22)",
  waveBottom: "rgba(99, 102, 241, 0.16)",
  warningBg: "#FEF3C7",
  warningBorder: "#F59E0B",
  warningText: "#78350F",
  dangerBg: "#FEE2E2",
  dangerBorder: "#EF4444",
  dangerText: "#7F1D1D",
  dangerSolid: "#B91C1C",
  onDangerSolid: "#FFFFFF",
  scrim: "rgba(15, 23, 58, 0.62)",
};

export const DARK_THEME: AppTheme = {
  isDark: true,
  bg: "#0A1128",
  bgGradient: ["#0B1330", "#102847", "#0B2B38"],
  ctaGradient: ["#0D9488", "#16A34A"],
  surface: "#111D3B",
  surfaceGlass: "rgba(17, 29, 59, 0.88)",
  surfaceMuted: "rgba(28, 45, 84, 0.88)",
  textPrimary: "#F1F5FF",
  textSecondary: "#CBD5F5",
  border: "#2A4073",
  primary: "#14B8A6",
  onPrimary: "#042F2E",
  primarySoft: "#064E3B",
  primarySoftText: "#A7F3D0",
  civicBlue: "#60A5FA",
  civicBlueSoft: "#172554",
  civicBlueText: "#DBEAFE",
  haloOuter: "rgba(45, 212, 191, 0.18)",
  haloMid: "rgba(253, 230, 138, 0.22)",
  haloCore: "#FDE68A",
  waveTop: "rgba(45, 212, 191, 0.14)",
  waveBottom: "rgba(99, 102, 241, 0.18)",
  warningBg: "#451A03",
  warningBorder: "#D97706",
  warningText: "#FDE68A",
  dangerBg: "#450A0A",
  dangerBorder: "#EF4444",
  dangerText: "#FECACA",
  dangerSolid: "#DC2626",
  onDangerSolid: "#FFFFFF",
  scrim: "rgba(2, 6, 23, 0.8)",
};

export interface GroupVisualStyle {
  label: string;
  binName: string;
  binColorName: string;
  binHint: string;
  examples: string;
  destination: string;
  shortDestination: string;
  legalTag: string;
  icon: IoniconName;
  binInnerIcon: IoniconName;
  binBg: string;
  binLidBg: string;
  binInk: string;
  bg: string;
  border: string;
  text: string;
  accent: string;
}

export function getGroupVisual(groupId: WasteGroupId, isDark: boolean): GroupVisualStyle {
  switch (groupId) {
    case "group_1_recyclable":
      return {
        label: "Thùng Xanh Lá · Rác Tái Chế",
        binName: "Rác Tái Chế",
        binColorName: "Thùng Xanh Lá",
        binHint: "Bỏ thùng Xanh lá (hoặc gom bán ve chai)",
        examples: "Giấy, bìa carton, chai nhựa sạch, hộp sữa, lon",
        destination: "Cơ sở tái chế rác · Bán ve chai",
        shortDestination: "Cơ sở tái chế",
        legalTag: "Nhóm 1 · QĐ 87/2025",
        icon: "sync-circle",
        binInnerIcon: "sync",
        binBg: "#16A34A",
        binLidBg: "#15803D",
        binInk: "#FFFFFF",
        bg: isDark ? "#052E16" : "#DCFCE7",
        border: isDark ? "#22C55E" : "#16A34A",
        text: isDark ? "#BBF7D0" : "#14532D",
        accent: isDark ? "#4ADE80" : "#15803D",
      };

    case "group_2_food":
      return {
        label: "Thùng Vàng · Rác Hữu Cơ",
        binName: "Rác Hữu Cơ",
        binColorName: "Thùng Vàng",
        binHint: "Chắt ráo nước rồi bỏ thùng Vàng (thực phẩm)",
        examples: "Thức ăn thừa, rau củ, vỏ trái cây, xương thịt cá",
        destination: "Sản xuất phân hữu cơ · Thức ăn gia súc",
        shortDestination: "Phân hữu cơ / Gia súc",
        legalTag: "Nhóm 2 (Thực phẩm) · QĐ 87/2025",
        icon: "nutrition",
        binInnerIcon: "leaf",
        binBg: "#EAB308",
        binLidBg: "#CA8A04",
        binInk: "#422006",
        bg: isDark ? "#422006" : "#FEF9C3",
        border: isDark ? "#FACC15" : "#D97706",
        text: isDark ? "#FEF08A" : "#713F12",
        accent: isDark ? "#FACC15" : "#A16207",
      };

    case "group_3_hazardous":
      return {
        label: "Thùng Đen · Rác Nguy Hại",
        binName: "Rác Nguy Hại",
        binColorName: "Thùng Đen",
        binHint: "KHÔNG bỏ chung túi rác · Mang tới điểm thu hồi",
        examples: "Pin thải, mực in, sơn, hóa chất, bóng đèn",
        destination: "Cơ sở xử lý riêng (đốt, đồng xử lý...)",
        shortDestination: "Xử lý nguy hại",
        legalTag: "Nhóm 3 (Nguy hại) · QĐ 87/2025",
        icon: "warning",
        binInnerIcon: "warning",
        binBg: "#18181B",
        binLidBg: "#27272A",
        binInk: "#FACC15",
        bg: isDark ? "#18181B" : "#F4F4F5",
        border: isDark ? "#FACC15" : "#27272A",
        text: isDark ? "#FEF08A" : "#18181B",
        accent: isDark ? "#FACC15" : "#B45309",
      };

    case "group_3_bulky":
      return {
        label: "Điểm Tập Kết · Rác Cồng Kềnh",
        binName: "Rác Cồng Kềnh",
        binColorName: "Điểm tập kết",
        binHint: "Đặt tại điểm thu gom theo lịch UBND phường",
        examples: "Bàn ghế hỏng, tủ gỗ, nệm cũ, cành cây lớn",
        destination: "Thu gom xử lý theo lịch UBND phường/xã",
        shortDestination: "Điểm tập kết",
        legalTag: "Nhóm 3 (Cồng kềnh) · QĐ 87/2025",
        icon: "cube",
        binInnerIcon: "cube",
        binBg: "#7C3AED",
        binLidBg: "#6D28D9",
        binInk: "#FFFFFF",
        bg: isDark ? "#2E1065" : "#EDE9FE",
        border: isDark ? "#A78BFA" : "#7C3AED",
        text: isDark ? "#DDD6FE" : "#4C1D95",
        accent: isDark ? "#A78BFA" : "#5B21B6",
      };

    case "group_3_other":
    default:
      return {
        label: "Thùng Đỏ · Rác Vô Cơ",
        binName: "Rác Vô Cơ",
        binColorName: "Thùng Đỏ",
        binHint: "Bỏ thùng Đỏ (rác vô cơ / sinh hoạt còn lại)",
        examples: "Túi nilon bẩn, hộp xốp, găng tay, đồ gốm vỡ, tã",
        destination: "Cơ sở xử lý rác (đốt, chôn lấp...)",
        shortDestination: "Đốt, chôn lấp",
        legalTag: "Nhóm 3 (Còn lại) · QĐ 87/2025",
        icon: "flame",
        binInnerIcon: "trash",
        binBg: "#DC2626",
        binLidBg: "#B91C1C",
        binInk: "#FFFFFF",
        bg: isDark ? "#450A0A" : "#FEE2E2",
        border: isDark ? "#F87171" : "#DC2626",
        text: isDark ? "#FECACA" : "#7F1D1D",
        accent: isDark ? "#F87171" : "#B91C1C",
      };
  }
}
