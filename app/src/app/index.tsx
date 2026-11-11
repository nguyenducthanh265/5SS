import { Ionicons } from "@expo/vector-icons";
import { Asset } from "expo-asset";
import { CameraView } from "expo-camera";
import { Image } from "expo-image";
import * as ImagePicker from "expo-image-picker";
import { LinearGradient } from "expo-linear-gradient";
import { Link } from "expo-router";
import { useRef, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { GuideModal } from "@/components/GuideModal";
import { MangroveBackdrop } from "@/components/MangroveBackdrop";
import { StatusBanner } from "@/components/StatusBanner";
import { WasteResultView } from "@/components/WasteResultView";
import { useHydratedDark } from "@/hooks/useHydratedDark";
import { useWasteClassifier } from "@/hooks/useWasteClassifier";
import { DEFAULT_WASTE_PROMPT, getApiBaseUrl } from "@/services/wasteApi";
import {
  DARK_THEME,
  ICON_SIZE,
  LIGHT_THEME,
  MIN_TOUCH_SIZE,
  RADII,
  SPACING,
} from "@/theme/tokens";

const SAMPLE_WASTE_ASSET = require("../../assets/sample-waste.jpg");

type ScanMode = "single" | "bag";

const BAG_SCAN_PROMPT =
  "Đây là túi rác mở có thể chứa nhiều vật phẩm trộn lẫn. Hãy liệt kê đầy đủ từng món thấy trong ảnh theo schema JSON chuẩn để kiểm tra túi lẫn theo Quyết định 87/2025/QĐ-UBND Hà Nội.";

export default function HomeScreen() {
  const isDark = useHydratedDark();
  const theme = isDark ? DARK_THEME : LIGHT_THEME;

  const {
    cameraPermission,
    requestCameraPermission,
    isAnalyzing,
    isSpeakingNow,
    response,
    lastPhotoUri,
    analyzePhotoUri,
    speakText,
    stopSpeech,
    reset,
  } = useWasteClassifier();

  const cameraRef = useRef<CameraView | null>(null);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [scanMode, setScanMode] = useState<ScanMode>("single");
  const [autoSpeak, setAutoSpeak] = useState(true);
  const [guideOpen, setGuideOpen] = useState(false);
  const [captureError, setCaptureError] = useState<string | null>(null);

  const apiUrl = getApiBaseUrl();
  const activePrompt = scanMode === "bag" ? BAG_SCAN_PROMPT : DEFAULT_WASTE_PROMPT;

  const runAnalysis = async (uri: string) => {
    setCaptureError(null);
    await analyzePhotoUri(uri, { autoSpeak, prompt: activePrompt });
  };

  const handleOpenCamera = async () => {
    setCaptureError(null);
    try {
      if (!cameraPermission?.granted) {
        const res = await requestCameraPermission();
        if (!res.granted) {
          setCaptureError(
            Platform.OS === "web"
              ? "Trình duyệt chưa cấp quyền Camera. Bạn có thể cấp quyền trên thanh địa chỉ hoặc chọn ảnh từ thư viện."
              : "Chưa được cấp quyền Camera. Bạn vẫn có thể chọn ảnh từ thư viện.",
          );
          return;
        }
      }
      setCameraOpen(true);
    } catch {
      setCaptureError("Không mở được camera trên thiết bị này. Bạn có thể chọn ảnh từ thư viện.");
    }
  };

  const handleCapture = async () => {
    if (!cameraRef.current || isAnalyzing) return;
    try {
      const photo = await cameraRef.current.takePictureAsync({ quality: 0.85 });
      if (photo?.uri) {
        setCameraOpen(false);
        await runAnalysis(photo.uri);
      }
    } catch {
      setCaptureError("Không chụp được ảnh từ camera. Vui lòng thử lại.");
    }
  };

  const handlePickImage = async () => {
    if (isAnalyzing) return;
    setCaptureError(null);
    try {
      const picked = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ["images"],
        quality: 0.85,
      });
      if (!picked.canceled && picked.assets[0]?.uri) {
        setCameraOpen(false);
        await runAnalysis(picked.assets[0].uri);
      }
    } catch {
      setCaptureError("Không mở được thư viện ảnh trên thiết bị.");
    }
  };

  const handleTestSample = async () => {
    if (isAnalyzing) return;
    setCaptureError(null);
    try {
      const asset = Asset.fromModule(SAMPLE_WASTE_ASSET);
      await asset.downloadAsync();
      const uri = asset.localUri ?? asset.uri;
      if (!uri) {
        setCaptureError("Không tải được ảnh mẫu đóng gói sẵn.");
        return;
      }
      setCameraOpen(false);
      await runAnalysis(uri);
    } catch {
      setCaptureError("Không mở được ảnh mẫu đóng gói sẵn.");
    }
  };

  const handleRetryLast = async () => {
    if (!lastPhotoUri || isAnalyzing) return;
    await runAnalysis(lastPhotoUri);
  };

  const handleReset = () => {
    setCaptureError(null);
    reset();
  };

  const permissionPermanentlyDenied =
    Boolean(cameraPermission) &&
    !cameraPermission?.granted &&
    cameraPermission?.canAskAgain === false;

  return (
    <View style={[styles.root, { backgroundColor: theme.bg }]}>
      <MangroveBackdrop theme={theme} />

      <SafeAreaView style={styles.safeArea}>
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}>
          <View style={styles.innerContainer}>
            {/* Editorial top header */}
            <View style={styles.topBar}>
              <View style={styles.brandBlock}>
                <LinearGradient
                  colors={theme.ctaGradient}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 1 }}
                  style={styles.brandIcon}>
                  <Ionicons name="leaf" size={20} color="#FFFFFF" />
                </LinearGradient>
                <View style={styles.brandTexts}>
                  <Text style={[styles.eyebrow, { color: theme.primary }]}>
                    HÀ NỘI · QĐ 87/2025/QĐ-UBND
                  </Text>
                  <Text style={[styles.appTitle, { color: theme.textPrimary }]}>
                    ĐIỀU HÒA DÒNG RÁC
                  </Text>
                </View>
              </View>

              <View style={styles.topActions}>
                <Pressable
                  accessibilityRole="switch"
                  accessibilityLabel="Tự động đọc hướng dẫn tiếng Việt"
                  accessibilityState={{ checked: autoSpeak }}
                  onPress={() => {
                    const next = !autoSpeak;
                    setAutoSpeak(next);
                    if (!next) void stopSpeech();
                  }}
                  style={({ pressed }) => [
                    styles.iconPillBtn,
                    {
                      backgroundColor: autoSpeak ? theme.civicBlueSoft : theme.surfaceGlass,
                      borderColor: autoSpeak ? theme.civicBlue : theme.border,
                      opacity: pressed ? 0.85 : 1,
                    },
                  ]}>
                  <Ionicons
                    name={autoSpeak ? "volume-high" : "volume-mute"}
                    size={ICON_SIZE.sm}
                    color={autoSpeak ? theme.civicBlueText : theme.textSecondary}
                  />
                  <Text
                    style={[
                      styles.iconPillText,
                      { color: autoSpeak ? theme.civicBlueText : theme.textSecondary },
                    ]}>
                    {autoSpeak ? "Giọng đọc" : "Tắt tiếng"}
                  </Text>
                </Pressable>

                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="Xem hướng dẫn nhanh Quyết định 87"
                  onPress={() => setGuideOpen(true)}
                  style={({ pressed }) => [
                    styles.iconPillBtn,
                    {
                      backgroundColor: theme.surfaceGlass,
                      borderColor: theme.border,
                      opacity: pressed ? 0.85 : 1,
                    },
                  ]}>
                  <Ionicons name="book-outline" size={ICON_SIZE.sm} color={theme.textPrimary} />
                  <Text style={[styles.iconPillText, { color: theme.textPrimary }]}>
                    QĐ 87
                  </Text>
                </Pressable>
              </View>
            </View>

            {/* Mode selector: Single item vs Open bag */}
            <View
              accessibilityRole="radiogroup"
              accessibilityLabel="Chọn chế độ soi rác"
              style={[
                styles.modeBar,
                { backgroundColor: theme.surfaceGlass, borderColor: theme.border },
              ]}>
              <Pressable
                accessibilityRole="radio"
                accessibilityState={{ selected: scanMode === "single" }}
                accessibilityLabel="Chế độ soi 1 món rác"
                onPress={() => setScanMode("single")}
                style={({ pressed }) => [
                  styles.modeBtn,
                  scanMode === "single" && {
                    backgroundColor: theme.primarySoft,
                    borderColor: theme.primary,
                  },
                  { opacity: pressed ? 0.85 : 1 },
                ]}>
                <Ionicons
                  name="cube-outline"
                  size={16}
                  color={scanMode === "single" ? theme.primarySoftText : theme.textSecondary}
                />
                <Text
                  style={[
                    styles.modeBtnText,
                    {
                      color:
                        scanMode === "single" ? theme.primarySoftText : theme.textSecondary,
                    },
                  ]}>
                  1 món rác
                </Text>
              </Pressable>

              <Pressable
                accessibilityRole="radio"
                accessibilityState={{ selected: scanMode === "bag" }}
                accessibilityLabel="Chế độ kiểm tra túi rác mở"
                onPress={() => setScanMode("bag")}
                style={({ pressed }) => [
                  styles.modeBtn,
                  scanMode === "bag" && {
                    backgroundColor: theme.primarySoft,
                    borderColor: theme.primary,
                  },
                  { opacity: pressed ? 0.85 : 1 },
                ]}>
                <Ionicons
                  name="bag-handle-outline"
                  size={16}
                  color={scanMode === "bag" ? theme.primarySoftText : theme.textSecondary}
                />
                <Text
                  style={[
                    styles.modeBtnText,
                    {
                      color: scanMode === "bag" ? theme.primarySoftText : theme.textSecondary,
                    },
                  ]}>
                  Túi rác mở
                </Text>
              </Pressable>
            </View>

            {/* Frosted Scanner / Camera / Solar-Halo Hero Card */}
            <View
              style={[
                styles.scannerCard,
                { backgroundColor: theme.surfaceGlass, borderColor: theme.border },
              ]}>
              {cameraOpen && cameraPermission?.granted ? (
                <View style={styles.cameraStage}>
                  <View style={styles.cameraFrame}>
                    <CameraView
                      ref={cameraRef}
                      style={styles.cameraView}
                      facing="back"
                      onMountError={() => {
                        setCameraOpen(false);
                        setCaptureError(
                          "Không khởi động được camera trên thiết bị này. Bạn có thể chọn ảnh từ thư viện.",
                        );
                      }}
                    />
                    <View pointerEvents="none" style={styles.reticleOverlay}>
                      <View style={styles.reticleBox} />
                      <View style={styles.reticleCaptionPill}>
                        <Text style={styles.reticleCaption}>
                          {scanMode === "bag"
                            ? "Đưa miệng túi rác mở vào giữa vòng sáng"
                            : "Đưa món rác vào giữa vòng sáng"}
                        </Text>
                      </View>
                    </View>
                  </View>

                  <View style={styles.cameraControls}>
                    <Pressable
                      accessibilityRole="button"
                      accessibilityLabel="Đóng camera"
                      onPress={() => setCameraOpen(false)}
                      style={({ pressed }) => [
                        styles.secondaryBtn,
                        {
                          backgroundColor: theme.surfaceMuted,
                          borderColor: theme.border,
                          opacity: pressed ? 0.85 : 1,
                        },
                      ]}>
                      <Ionicons name="close" size={ICON_SIZE.sm} color={theme.textPrimary} />
                      <Text style={[styles.secondaryBtnText, { color: theme.textPrimary }]}>
                        Đóng
                      </Text>
                    </Pressable>

                    <Pressable
                      accessibilityRole="button"
                      accessibilityLabel="Chụp ảnh và phân loại ngay"
                      disabled={isAnalyzing}
                      onPress={handleCapture}
                      style={({ pressed }) => [
                        styles.shutterWrap,
                        { opacity: isAnalyzing ? 0.6 : pressed ? 0.88 : 1 },
                      ]}>
                      <LinearGradient
                        colors={theme.ctaGradient}
                        start={{ x: 0, y: 0 }}
                        end={{ x: 1, y: 0 }}
                        style={styles.shutterBtn}>
                        <Ionicons name="camera" size={ICON_SIZE.md} color="#FFFFFF" />
                        <Text style={styles.shutterBtnText}>Chụp &amp; Phân loại</Text>
                      </LinearGradient>
                    </Pressable>
                  </View>
                </View>
              ) : (
                <View style={styles.idleStage}>
                  {lastPhotoUri ? (
                    <View style={styles.previewWrap}>
                      <Image
                        source={{ uri: lastPhotoUri }}
                        style={styles.previewImage}
                        contentFit="cover"
                        accessibilityLabel="Ảnh rác vừa chụp để phân loại"
                      />
                      {response && !isAnalyzing && (
                        <Pressable
                          accessibilityRole="button"
                          accessibilityLabel="Xóa kết quả hiện tại"
                          onPress={handleReset}
                          style={({ pressed }) => [
                            styles.clearPreviewBtn,
                            { opacity: pressed ? 0.85 : 1 },
                          ]}>
                          <Ionicons name="close" size={16} color="#FFFFFF" />
                          <Text style={styles.clearPreviewText}>Xóa</Text>
                        </Pressable>
                      )}
                    </View>
                  ) : (
                    <LinearGradient
                      colors={
                        theme.isDark
                          ? ["rgba(16, 40, 71, 0.9)", "rgba(11, 43, 56, 0.9)"]
                          : ["rgba(224, 234, 255, 0.82)", "rgba(209, 250, 229, 0.78)"]
                      }
                      start={{ x: 0, y: 0 }}
                      end={{ x: 1, y: 1 }}
                      style={[styles.heroPlaceholder, { borderColor: theme.border }]}>
                      {/* Concentric solar halo scanner emblem */}
                      <View style={[styles.haloOuterRing, { backgroundColor: theme.haloOuter }]}>
                        <View style={[styles.haloMidRing, { backgroundColor: theme.haloMid }]}>
                          <View style={[styles.heroIconRing, { backgroundColor: theme.surface }]}>
                            <Ionicons name="scan" size={30} color={theme.primary} />
                          </View>
                        </View>
                      </View>
                      <Text style={[styles.heroTitle, { color: theme.textPrimary }]}>
                        Soi rác tại thùng — trả lời tức thì bằng giọng nói
                      </Text>
                      <Text style={[styles.heroDesc, { color: theme.textSecondary }]}>
                        Nhận diện hộp sữa giấy, pin thải, túi dính dầu mỡ, vỉ thuốc và cảnh báo túi lẫn theo QĐ 87/2025.
                      </Text>
                    </LinearGradient>
                  )}

                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel={lastPhotoUri ? "Chụp món rác khác" : "Mở camera để soi rác"}
                    disabled={isAnalyzing}
                    onPress={handleOpenCamera}
                    style={({ pressed }) => [
                      styles.primaryCtaWrap,
                      { opacity: isAnalyzing ? 0.6 : pressed ? 0.88 : 1 },
                    ]}>
                    <LinearGradient
                      colors={theme.ctaGradient}
                      start={{ x: 0, y: 0 }}
                      end={{ x: 1, y: 0 }}
                      style={styles.primaryCta}>
                      <Ionicons name="camera" size={ICON_SIZE.md} color="#FFFFFF" />
                      <Text style={styles.primaryCtaText}>
                        {lastPhotoUri ? "Chụp món khác" : "Mở Camera soi rác"}
                      </Text>
                    </LinearGradient>
                  </Pressable>

                  <View style={styles.secondaryRow}>
                    <Pressable
                      accessibilityRole="button"
                      accessibilityLabel="Chọn ảnh rác từ thư viện"
                      disabled={isAnalyzing}
                      onPress={handlePickImage}
                      style={({ pressed }) => [
                        styles.secondaryBtn,
                        styles.flexBtn,
                        {
                          backgroundColor: theme.surfaceMuted,
                          borderColor: theme.border,
                          opacity: isAnalyzing ? 0.6 : pressed ? 0.85 : 1,
                        },
                      ]}>
                      <Ionicons name="images-outline" size={ICON_SIZE.sm} color={theme.textPrimary} />
                      <Text style={[styles.secondaryBtnText, { color: theme.textPrimary }]}>
                        Thư viện ảnh
                      </Text>
                    </Pressable>

                    <Pressable
                      accessibilityRole="button"
                      accessibilityLabel="Thử với ảnh mẫu đóng gói sẵn"
                      disabled={isAnalyzing}
                      onPress={handleTestSample}
                      style={({ pressed }) => [
                        styles.secondaryBtn,
                        styles.flexBtn,
                        {
                          backgroundColor: theme.surfaceMuted,
                          borderColor: theme.border,
                          opacity: isAnalyzing ? 0.6 : pressed ? 0.85 : 1,
                        },
                      ]}>
                      <Ionicons name="flask-outline" size={ICON_SIZE.sm} color={theme.textPrimary} />
                      <Text style={[styles.secondaryBtnText, { color: theme.textPrimary }]}>
                        Thử ảnh mẫu
                      </Text>
                    </Pressable>
                  </View>
                </View>
              )}
            </View>

            {/* Permission permanently denied banner */}
            {permissionPermanentlyDenied && (
              <View
                accessibilityRole="alert"
                style={[
                  styles.permissionBox,
                  { backgroundColor: theme.warningBg, borderColor: theme.warningBorder },
                ]}>
                <Ionicons name="lock-closed" size={ICON_SIZE.sm} color={theme.warningText} />
                <View style={styles.permissionContent}>
                  <Text style={[styles.permissionTitle, { color: theme.warningText }]}>
                    Quyền Camera đang bị tắt
                  </Text>
                  <Text style={[styles.permissionBody, { color: theme.warningText }]}>
                    {Platform.OS === "web"
                      ? "Bạn vẫn có thể chọn ảnh từ thư viện hoặc bật quyền Camera trong cài đặt trình duyệt."
                      : "Bạn vẫn có thể chọn ảnh từ thư viện hoặc mở Cài đặt để bật quyền Camera."}
                  </Text>
                  {Platform.OS !== "web" && (
                    <Pressable
                      accessibilityRole="button"
                      accessibilityLabel="Mở cài đặt thiết bị để cấp quyền camera"
                      onPress={() => {
                        void Linking.openSettings().catch(() => {
                          setCaptureError("Không mở được Cài đặt trên thiết bị.");
                        });
                      }}
                      style={({ pressed }) => [
                        styles.settingsBtn,
                        { backgroundColor: theme.warningText, opacity: pressed ? 0.85 : 1 },
                      ]}>
                      <Text
                        style={[
                          styles.settingsBtnText,
                          { color: theme.isDark ? "#451A03" : "#FFFFFF" },
                        ]}>
                        Mở Cài đặt
                      </Text>
                    </Pressable>
                  )}
                </View>
              </View>
            )}

            {/* Local capture error */}
            {captureError && (
              <View
                accessibilityRole="alert"
                style={[
                  styles.permissionBox,
                  { backgroundColor: theme.dangerBg, borderColor: theme.dangerBorder },
                ]}>
                <Ionicons name="alert-circle" size={ICON_SIZE.sm} color={theme.dangerText} />
                <Text style={[styles.permissionBody, { color: theme.dangerText, flex: 1 }]}>
                  {captureError}
                </Text>
              </View>
            )}

            {/* Loading state */}
            {isAnalyzing && (
              <View
                accessibilityLiveRegion="polite"
                style={[
                  styles.loadingCard,
                  { backgroundColor: theme.surfaceGlass, borderColor: theme.border },
                ]}>
                <ActivityIndicator size="small" color={theme.primary} />
                <View style={styles.loadingTexts}>
                  <Text style={[styles.loadingTitle, { color: theme.textPrimary }]}>
                    Đang phân tích dòng rác theo QĐ 87/2025...
                  </Text>
                  <Text style={[styles.loadingSub, { color: theme.textSecondary }]}>
                    Kiểm tra chất liệu, dầu mỡ, khả năng tái chế và túi lẫn
                  </Text>
                </View>
              </View>
            )}

            {/* Result or Error / Fallback states */}
            {response && !isAnalyzing && (
              response.status === "ai" ? (
                <WasteResultView
                  result={response.result}
                  latencyMs={response.latencyMs}
                  isSpeakingNow={isSpeakingNow}
                  theme={theme}
                  onSpeak={(txt) => void speakText(txt)}
                  onStopSpeech={() => void stopSpeech()}
                />
              ) : (
                <StatusBanner
                  response={response}
                  theme={theme}
                  onRetry={lastPhotoUri ? () => void handleRetryLast() : undefined}
                />
              )
            )}

            {/* Subtle footer status & QA link */}
            <View style={styles.footer}>
              <Text style={[styles.footerMeta, { color: theme.textSecondary }]} numberOfLines={1}>
                API: {apiUrl || "Chưa đặt EXPO_PUBLIC_API_URL"}
              </Text>
              <Link href="/selftest" asChild>
                <Pressable
                  accessibilityRole="link"
                  accessibilityLabel="Mở màn hình kiểm tra tự động Selftest"
                  hitSlop={8}
                  style={({ pressed }) => [
                    styles.selftestLink,
                    { opacity: pressed ? 0.7 : 1 },
                  ]}>
                  <Ionicons name="pulse-outline" size={14} color={theme.civicBlue} />
                  <Text style={[styles.selftestText, { color: theme.civicBlue }]}>
                    Selftest
                  </Text>
                </Pressable>
              </Link>
            </View>
          </View>
        </ScrollView>
      </SafeAreaView>

      <GuideModal
        visible={guideOpen}
        theme={theme}
        onClose={() => setGuideOpen(false)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  safeArea: { flex: 1 },
  scrollContent: {
    padding: SPACING.lg,
    paddingBottom: SPACING.xxl,
  },
  innerContainer: {
    width: "100%",
    maxWidth: 640,
    alignSelf: "center",
    gap: SPACING.md,
  },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: SPACING.sm,
    flexWrap: "wrap",
  },
  brandBlock: {
    flexDirection: "row",
    alignItems: "center",
    gap: SPACING.sm,
    flexShrink: 1,
  },
  brandIcon: {
    width: 42,
    height: 42,
    borderRadius: RADII.md,
    alignItems: "center",
    justifyContent: "center",
  },
  brandTexts: { flexShrink: 1 },
  eyebrow: {
    fontSize: 11,
    fontWeight: "800",
    letterSpacing: 0.7,
  },
  appTitle: {
    fontSize: 19,
    fontWeight: "900",
    letterSpacing: 0.3,
  },
  topActions: { flexDirection: "row", alignItems: "center", gap: SPACING.sm },
  iconPillBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    minHeight: MIN_TOUCH_SIZE,
    paddingHorizontal: 12,
    borderRadius: RADII.pill,
    borderWidth: 1,
  },
  iconPillText: { fontSize: 13, fontWeight: "700" },
  modeBar: {
    flexDirection: "row",
    padding: 4,
    borderRadius: RADII.md,
    borderWidth: 1,
    gap: 4,
  },
  modeBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    minHeight: MIN_TOUCH_SIZE,
    paddingHorizontal: 10,
    borderRadius: RADII.sm,
    borderWidth: 1,
    borderColor: "transparent",
  },
  modeBtnText: { fontSize: 13, fontWeight: "700", flexShrink: 1 },
  scannerCard: {
    borderRadius: RADII.xl,
    borderWidth: 1,
    padding: SPACING.lg,
  },
  cameraStage: { gap: SPACING.md },
  cameraFrame: {
    width: "100%",
    height: 320,
    borderRadius: RADII.lg,
    overflow: "hidden",
    backgroundColor: "#000000",
    position: "relative",
  },
  cameraView: { width: "100%", height: "100%" },
  reticleOverlay: {
    position: "absolute",
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    alignItems: "center",
    justifyContent: "center",
    padding: SPACING.lg,
  },
  reticleBox: {
    width: "76%",
    height: "62%",
    borderRadius: RADII.xl,
    borderWidth: 2,
    borderColor: "rgba(167, 243, 208, 0.9)",
    borderStyle: "dashed",
  },
  reticleCaptionPill: {
    position: "absolute",
    bottom: 12,
    backgroundColor: "rgba(20, 34, 74, 0.84)",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: RADII.pill,
  },
  reticleCaption: { color: "#FFFFFF", fontSize: 12, fontWeight: "600" },
  cameraControls: {
    flexDirection: "row",
    alignItems: "center",
    gap: SPACING.sm,
  },
  shutterWrap: { flex: 1 },
  shutterBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    minHeight: 54,
    borderRadius: RADII.lg,
    paddingHorizontal: SPACING.lg,
  },
  shutterBtnText: { color: "#FFFFFF", fontSize: 16, fontWeight: "800" },
  idleStage: { gap: SPACING.md },
  heroPlaceholder: {
    borderRadius: RADII.lg,
    borderWidth: 1,
    paddingVertical: SPACING.xl,
    paddingHorizontal: SPACING.lg,
    alignItems: "center",
    gap: SPACING.sm,
  },
  haloOuterRing: {
    width: 106,
    height: 106,
    borderRadius: RADII.pill,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 4,
  },
  haloMidRing: {
    width: 82,
    height: 82,
    borderRadius: RADII.pill,
    alignItems: "center",
    justifyContent: "center",
  },
  heroIconRing: {
    width: 60,
    height: 60,
    borderRadius: RADII.pill,
    alignItems: "center",
    justifyContent: "center",
  },
  heroTitle: { fontSize: 16, fontWeight: "800", textAlign: "center" },
  heroDesc: { fontSize: 13, lineHeight: 19, textAlign: "center", maxWidth: 420 },
  previewWrap: {
    width: "100%",
    height: 220,
    borderRadius: RADII.lg,
    overflow: "hidden",
    position: "relative",
  },
  previewImage: { width: "100%", height: "100%" },
  clearPreviewBtn: {
    position: "absolute",
    top: 10,
    right: 10,
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    minHeight: 36,
    paddingHorizontal: 10,
    borderRadius: RADII.pill,
    backgroundColor: "rgba(20, 34, 74, 0.84)",
  },
  clearPreviewText: { color: "#FFFFFF", fontSize: 12, fontWeight: "700" },
  primaryCtaWrap: { width: "100%" },
  primaryCta: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    minHeight: 54,
    borderRadius: RADII.lg,
    paddingHorizontal: SPACING.lg,
  },
  primaryCtaText: { color: "#FFFFFF", fontSize: 16, fontWeight: "800" },
  secondaryRow: { flexDirection: "row", gap: SPACING.sm },
  flexBtn: { flex: 1, justifyContent: "center" },
  secondaryBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    minHeight: MIN_TOUCH_SIZE,
    paddingHorizontal: 14,
    borderRadius: RADII.md,
    borderWidth: 1,
  },
  secondaryBtnText: { fontSize: 14, fontWeight: "700" },
  permissionBox: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: SPACING.sm,
    borderRadius: RADII.lg,
    borderWidth: 1,
    padding: SPACING.lg,
  },
  permissionContent: { flex: 1, gap: 6 },
  permissionTitle: { fontSize: 14, fontWeight: "800" },
  permissionBody: { fontSize: 13, lineHeight: 19 },
  settingsBtn: {
    alignSelf: "flex-start",
    minHeight: MIN_TOUCH_SIZE,
    justifyContent: "center",
    paddingHorizontal: 14,
    borderRadius: RADII.pill,
    marginTop: 2,
  },
  settingsBtnText: { color: "#FFFFFF", fontSize: 13, fontWeight: "700" },
  loadingCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: SPACING.md,
    borderRadius: RADII.lg,
    borderWidth: 1,
    padding: SPACING.lg,
  },
  loadingTexts: { flex: 1, gap: 2 },
  loadingTitle: { fontSize: 14, fontWeight: "700" },
  loadingSub: { fontSize: 12, lineHeight: 17 },
  footer: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: SPACING.sm,
    paddingTop: SPACING.sm,
  },
  footerMeta: { fontSize: 12, flex: 1 },
  selftestLink: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    minHeight: MIN_TOUCH_SIZE,
    paddingHorizontal: 8,
  },
  selftestText: { fontSize: 12, fontWeight: "700" },
});
