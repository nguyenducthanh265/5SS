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
  binHint: string;
  icon: IoniconName;
  bg: string;
  border: string;
  text: string;
  accent: string;
}

export function getGroupVisual(groupId: WasteGroupId, isDark: boolean): GroupVisualStyle {
  switch (groupId) {
    case "group_1_recyclable":
      return isDark
        ? {
            label: "Nhóm 1 · Tái chế",
            binHint: "Thùng xanh lá / Bán phế liệu",
            icon: "leaf",
            bg: "#052E16",
            border: "#34D399",
            text: "#A7F3D0",
            accent: "#34D399",
          }
        : {
            label: "Nhóm 1 · Tái chế",
            binHint: "Thùng xanh lá / Bán phế liệu",
            icon: "leaf",
            bg: "#D1FAE5",
            border: "#34D399",
            text: "#064E3B",
            accent: "#0F766E",
          };

    case "group_2_food":
      return isDark
        ? {
            label: "Nhóm 2 · Thực phẩm",
            binHint: "Thùng rác hữu cơ / thực phẩm",
            icon: "restaurant",
            bg: "#451A03",
            border: "#FBBF24",
            text: "#FDE68A",
            accent: "#FBBF24",
          }
        : {
            label: "Nhóm 2 · Thực phẩm",
            binHint: "Thùng rác hữu cơ / thực phẩm",
            icon: "restaurant",
            bg: "#FEF3C7",
            border: "#F59E0B",
            text: "#78350F",
            accent: "#B45309",
          };

    case "group_3_hazardous":
      return isDark
        ? {
            label: "Nhóm 3 · Rác nguy hại",
            binHint: "Tách riêng, mang tới điểm thu hồi",
            icon: "warning",
            bg: "#450A0A",
            border: "#F87171",
            text: "#FECACA",
            accent: "#F87171",
          }
        : {
            label: "Nhóm 3 · Rác nguy hại",
            binHint: "Tách riêng, mang tới điểm thu hồi",
            icon: "warning",
            bg: "#FEE2E2",
            border: "#F87171",
            text: "#7F1D1D",
            accent: "#B91C1C",
          };

    case "group_3_bulky":
      return isDark
        ? {
            label: "Nhóm 3 · Rác cồng kềnh",
            binHint: "Đặt tại điểm thu gom theo lịch phường",
            icon: "cube",
            bg: "#2E1065",
            border: "#A78BFA",
            text: "#DDD6FE",
            accent: "#A78BFA",
          }
        : {
            label: "Nhóm 3 · Rác cồng kềnh",
            binHint: "Đặt tại điểm thu gom theo lịch phường",
            icon: "cube",
            bg: "#EDE9FE",
            border: "#A78BFA",
            text: "#4C1D95",
            accent: "#5B21B6",
          };

    case "group_3_other":
    default:
      return isDark
        ? {
            label: "Nhóm 3 · Rác thải còn lại",
            binHint: "Thùng rác sinh hoạt còn lại",
            icon: "trash",
            bg: "#1E293B",
            border: "#64748B",
            text: "#E2E8F0",
            accent: "#94A3B8",
          }
        : {
            label: "Nhóm 3 · Rác thải còn lại",
            binHint: "Thùng rác sinh hoạt còn lại",
            icon: "trash",
            bg: "#EEF2FF",
            border: "#94A3B8",
            text: "#1E293B",
            accent: "#334155",
          };
  }
}
