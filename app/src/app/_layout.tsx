import { DarkTheme, DefaultTheme, Stack, ThemeProvider } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect } from "react";

import { useHydratedDark } from "@/hooks/useHydratedDark";

SplashScreen.preventAutoHideAsync().catch(() => {});

export default function RootLayout() {
  const isDark = useHydratedDark();

  useEffect(() => {
    SplashScreen.hideAsync().catch(() => {});
  }, []);

  return (
    <ThemeProvider value={isDark ? DarkTheme : DefaultTheme}>
      <Stack>
        <Stack.Screen
          name="index"
          options={{
            headerShown: false,
            title: "Điều Hòa Dòng Rác · QĐ 87/2025",
          }}
        />
        <Stack.Screen
          name="selftest"
          options={{ title: "Selftest AI" }}
        />
      </Stack>
    </ThemeProvider>
  );
}
