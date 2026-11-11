import { useSyncExternalStore } from "react";
import { useColorScheme } from "react-native";

const subscribeNoop = () => () => {};
const getClientSnapshot = () => true;
const getServerSnapshot = () => false;

/**
 * Trả về `true` nếu thiết bị đang ở chế độ tối sau khi client đã hydrate,
 * tránh React hydration mismatch giữa Expo Web SSR (luôn light) và dark mode trình duyệt.
 */
export function useHydratedDark(): boolean {
  const systemScheme = useColorScheme();
  const isHydrated = useSyncExternalStore(
    subscribeNoop,
    getClientSnapshot,
    getServerSnapshot,
  );
  return isHydrated && systemScheme === "dark";
}

