import { Asset } from "expo-asset";
import { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";

import { classifyWasteUri, type ClassifyWasteResponse } from "@/services/wasteApi";

const SAMPLE_WASTE_ASSET = require("../../assets/sample-waste.jpg");

type SelftestStatus = "running" | "pass" | "fail";

/**
 * Route deep link `<scheme>://selftest` (`hanoiwaste://selftest`).
 * Chạy luồng thật `wasteApi` trên ảnh mẫu đóng gói sẵn trong `assets/sample-waste.jpg`.
 * Chỉ in `HACKCHECK SELFTEST PASS` khi `kind === "ai"` và `parseWasteResult` hợp lệ.
 */
export default function SelftestScreen() {
  const [status, setStatus] = useState<SelftestStatus>("running");
  const [detail, setDetail] = useState<string>("Đang chuẩn bị ảnh mẫu và gọi backend AI...");
  const [response, setResponse] = useState<ClassifyWasteResponse | null>(null);
  const startedRef = useRef(false);

  const runSelftest = useCallback(async () => {
    setStatus("running");
    setDetail("Đang nạp ảnh mẫu và gọi classifyWasteUri...");
    setResponse(null);

    try {
      const asset = Asset.fromModule(SAMPLE_WASTE_ASSET);
      await asset.downloadAsync();
      const uri = asset.localUri ?? asset.uri;
      if (!uri) {
        const reason = "không lấy được URI của ảnh mẫu";
        console.log(`HACKCHECK SELFTEST FAIL ${reason}`);
        setStatus("fail");
        setDetail(reason);
        return;
      }

      const res = await classifyWasteUri(uri);
      setResponse(res);

      if (res.status === "ai") {
        console.log("HACKCHECK SELFTEST PASS");
        setStatus("pass");
        const itemSummary =
          res.result.items.length > 0
            ? `${res.result.items.length} món: ${res.result.items.map((i) => i.name_vi).join(", ")}`
            : "0 món";
        setDetail(`AI OK (${res.latencyMs}ms) — ${itemSummary}`);
        return;
      }

      const reason =
        res.status === "fallback"
          ? `fallback (${res.reason})`
          : res.status === "parse_error"
            ? `parse_error (${res.reason})`
            : `${res.status}: ${res.message}`;

      console.log(`HACKCHECK SELFTEST FAIL ${reason}`);
      setStatus("fail");
      setDetail(reason);
    } catch (err) {
      const reason = err instanceof Error ? err.message : "lỗi không xác định";
      console.log(`HACKCHECK SELFTEST FAIL ${reason}`);
      setStatus("fail");
      setDetail(reason);
    }
  }, []);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;
    void runSelftest();
  }, [runSelftest]);

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Hanoi Waste — Selftest</Text>
      <View style={styles.card}>
        {status === "running" && <ActivityIndicator size="small" />}
        <Text
          style={[
            styles.statusText,
            status === "pass"
              ? styles.pass
              : status === "fail"
                ? styles.fail
                : styles.running,
          ]}>
          {status === "running"
            ? "ĐANG CHẠY..."
            : status === "pass"
              ? "HACKCHECK SELFTEST PASS"
              : "HACKCHECK SELFTEST FAIL"}
        </Text>
        <Text style={styles.detail}>{detail}</Text>
        {response?.status === "ai" && (
          <Text style={styles.speech}>speech_vi: {response.result.speech_vi}</Text>
        )}
      </View>

      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Chạy lại kiểm tra tự động Selftest"
        style={({ pressed }) => [
          styles.button,
          { opacity: status === "running" ? 0.6 : pressed ? 0.85 : 1 },
        ]}
        onPress={() => {
          void runSelftest();
        }}
        disabled={status === "running"}>
        <Text style={styles.buttonText}>Chạy lại Selftest</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, padding: 20, gap: 16, backgroundColor: "#F8FAFC" },
  title: { fontSize: 20, fontWeight: "700", color: "#0F172A" },
  card: {
    backgroundColor: "#FFFFFF",
    borderRadius: 12,
    padding: 16,
    gap: 10,
    borderWidth: 1,
    borderColor: "#E2E8F0",
  },
  statusText: { fontSize: 16, fontWeight: "700" },
  running: { color: "#0369A1" },
  pass: { color: "#15803D" },
  fail: { color: "#B91C1C" },
  detail: { fontSize: 14, color: "#334155" },
  speech: { fontSize: 13, color: "#475569", fontStyle: "italic" },
  button: {
    alignSelf: "flex-start",
    justifyContent: "center",
    minHeight: 44,
    backgroundColor: "#0F172A",
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 10,
  },
  buttonText: { color: "#FFFFFF", fontWeight: "600" },
});
