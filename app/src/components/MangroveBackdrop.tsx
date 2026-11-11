import { LinearGradient } from "expo-linear-gradient";
import { StyleSheet, View } from "react-native";
import Svg, { Circle, Defs, LinearGradient as SvgGradient, Path, Stop } from "react-native-svg";

import type { AppTheme } from "@/theme/tokens";

interface MangroveBackdropProps {
  theme: AppTheme;
}

/**
 * Atmospheric eco-editorial backdrop inspired by "Điều Hòa Dòng Chảy":
 * soft periwinkle-jade gradient, luminous concentric solar halo, and flowing water ribbons.
 */
export function MangroveBackdrop({ theme }: MangroveBackdropProps) {
  return (
    <View pointerEvents="none" style={StyleSheet.absoluteFill}>
      <LinearGradient
        colors={theme.bgGradient}
        start={{ x: 0.15, y: 0 }}
        end={{ x: 0.85, y: 1 }}
        style={StyleSheet.absoluteFill}
      />

      <Svg
        width="100%"
        height="100%"
        viewBox="0 0 400 820"
        preserveAspectRatio="xMidYMid slice"
        style={StyleSheet.absoluteFill}>
        <Defs>
          <SvgGradient id="flowJade" x1="0" y1="0" x2="1" y2="1">
            <Stop offset="0%" stopColor="#34D399" stopOpacity={theme.isDark ? 0.22 : 0.34} />
            <Stop offset="55%" stopColor="#38BDF8" stopOpacity={theme.isDark ? 0.16 : 0.24} />
            <Stop offset="100%" stopColor="#6366F1" stopOpacity={theme.isDark ? 0.24 : 0.2} />
          </SvgGradient>
          <SvgGradient id="flowDeep" x1="0" y1="1" x2="1" y2="0">
            <Stop offset="0%" stopColor="#312E81" stopOpacity={theme.isDark ? 0.45 : 0.16} />
            <Stop offset="100%" stopColor="#0D9488" stopOpacity={theme.isDark ? 0.18 : 0.12} />
          </SvgGradient>
        </Defs>

        {/* Concentric luminous solar halo (top-right) */}
        <Circle
          cx="326"
          cy="118"
          r="116"
          fill={theme.haloOuter}
        />
        <Circle
          cx="326"
          cy="118"
          r="76"
          fill={theme.haloMid}
        />
        <Circle
          cx="326"
          cy="118"
          r="34"
          fill={theme.haloCore}
          fillOpacity={theme.isDark ? 0.38 : 0.88}
        />
        <Circle
          cx="326"
          cy="118"
          r="96"
          stroke="#FFFFFF"
          strokeOpacity={theme.isDark ? 0.14 : 0.48}
          strokeWidth="1.2"
          fill="none"
        />

        {/* Flowing mangrove water ribbons */}
        <Path
          d="M-30 340 C 80 280, 210 410, 430 310 L 430 430 C 230 500, 90 385, -30 445 Z"
          fill="url(#flowJade)"
        />
        <Path
          d="M-30 585 C 110 530, 260 645, 430 560 L 430 840 L -30 840 Z"
          fill="url(#flowDeep)"
        />

        {/* Delicate botanical leaf curves */}
        <Path
          d="M16 420 C 48 390, 88 395, 112 422 C 80 432, 42 432, 16 420 Z"
          fill="#10B981"
          fillOpacity={theme.isDark ? 0.2 : 0.24}
        />
        <Path
          d="M320 475 C 352 448, 385 452, 404 475 C 378 485, 344 484, 320 475 Z"
          fill="#14B8A6"
          fillOpacity={theme.isDark ? 0.2 : 0.22}
        />
      </Svg>
    </View>
  );
}

