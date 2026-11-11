import { useCameraPermissions, type PermissionResponse } from "expo-camera";
import { useCallback, useEffect, useRef, useState } from "react";

import { speakVietnamese, stopSpeaking } from "@/services/speech";
import { classifyWasteUri, type ClassifyWasteResponse } from "@/services/wasteApi";

export interface UseWasteClassifierState {
  cameraPermission: PermissionResponse | null;
  requestCameraPermission: () => Promise<PermissionResponse>;
  isAnalyzing: boolean;
  isSpeakingNow: boolean;
  response: ClassifyWasteResponse | null;
  lastPhotoUri: string | null;
  analyzePhotoUri: (
    uri: string,
    options?: { autoSpeak?: boolean; prompt?: string },
  ) => Promise<ClassifyWasteResponse>;
  speakText: (text: string) => Promise<void>;
  stopSpeech: () => Promise<void>;
  reset: () => void;
}

/**
 * Hook trung tâm kết nối Camera permission + gọi AI phân loại rác (`wasteApi`) + giọng nói (`speech`).
 * UI/UX chỉ cần gọi các action & render theo `response.status`.
 */
export function useWasteClassifier(): UseWasteClassifierState {
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isSpeakingNow, setIsSpeakingNow] = useState(false);
  const [response, setResponse] = useState<ClassifyWasteResponse | null>(null);
  const [lastPhotoUri, setLastPhotoUri] = useState<string | null>(null);
  const inFlightRef = useRef(false);
  const speechSessionRef = useRef(0);

  const stopSpeech = useCallback(async () => {
    speechSessionRef.current += 1;
    await stopSpeaking();
    setIsSpeakingNow(false);
  }, []);

  const speakText = useCallback(async (text: string) => {
    if (!text.trim()) return;
    const sessionId = ++speechSessionRef.current;
    setIsSpeakingNow(true);
    const clearIfCurrent = () => {
      if (speechSessionRef.current === sessionId) {
        setIsSpeakingNow(false);
      }
    };
    const started = await speakVietnamese(text, {
      onDone: clearIfCurrent,
      onStopped: clearIfCurrent,
      onError: clearIfCurrent,
    });
    if (!started) {
      clearIfCurrent();
    }
  }, []);

  useEffect(() => {
    return () => {
      speechSessionRef.current += 1;
      void stopSpeaking();
    };
  }, []);

  const analyzePhotoUri = useCallback(
    async (
      uri: string,
      options: { autoSpeak?: boolean; prompt?: string } = {},
    ): Promise<ClassifyWasteResponse> => {
      if (inFlightRef.current) {
        return {
          status: "busy",
          message: "Đang xử lý ảnh trước đó, vui lòng chờ giây lát.",
        };
      }

      inFlightRef.current = true;
      setIsAnalyzing(true);
      setLastPhotoUri(uri);
      await stopSpeech();

      try {
        const res = await classifyWasteUri(uri, { prompt: options.prompt });
        setResponse(res);

        if (options.autoSpeak !== false && res.status === "ai" && res.result.speech_vi.trim()) {
          await speakText(res.result.speech_vi);
        }
        return res;
      } catch (err) {
        const message = err instanceof Error ? err.message : "Không xử lý được ảnh đã chụp.";
        const failRes: ClassifyWasteResponse = { status: "network", message };
        setResponse(failRes);
        return failRes;
      } finally {
        inFlightRef.current = false;
        setIsAnalyzing(false);
      }
    },
    [speakText, stopSpeech],
  );

  const reset = useCallback(() => {
    void stopSpeech();
    setResponse(null);
    setLastPhotoUri(null);
  }, [stopSpeech]);

  return {
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
  };
}
