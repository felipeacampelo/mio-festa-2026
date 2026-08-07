import { useEffect, useRef, useState } from "react";
import jsQR from "jsqr";

export function useQrScanner(onDecode: (data: string) => void | Promise<void>) {
  const [scanning, setScanning] = useState(false);
  const [cameraError, setCameraError] = useState("");

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const intervalRef = useRef<number | null>(null);
  const onDecodeRef = useRef(onDecode);
  onDecodeRef.current = onDecode;
  const processingRef = useRef(false);

  const stopCamera = () => {
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setScanning(false);
  };

  const startCamera = async () => {
    setCameraError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      if (!canvasRef.current) canvasRef.current = document.createElement("canvas");
      setScanning(true);

      intervalRef.current = window.setInterval(async () => {
        if (processingRef.current) return;
        if (!videoRef.current || !canvasRef.current) return;
        const width = videoRef.current.videoWidth;
        const height = videoRef.current.videoHeight;
        if (!width || !height) return;
        const context = canvasRef.current.getContext("2d", { willReadFrequently: true });
        if (!context) return;
        canvasRef.current.width = width;
        canvasRef.current.height = height;
        context.drawImage(videoRef.current, 0, 0, width, height);
        const imageData = context.getImageData(0, 0, width, height);
        const qrCode = jsQR(imageData.data, imageData.width, imageData.height);
        if (!qrCode?.data) return;
        // Trava novas leituras ate essa terminar de processar - sem isso, se
        // onDecode demorar (chamada de rede), o mesmo QR ainda visivel na
        // camera dispara de novo no proximo tick antes da primeira terminar.
        processingRef.current = true;
        try {
          await onDecodeRef.current(qrCode.data);
        } finally {
          processingRef.current = false;
        }
      }, 1000);
    } catch {
      setCameraError("Não foi possível acessar a câmera.");
    }
  };

  useEffect(() => {
    return () => stopCamera();
  }, []);

  return { videoRef, scanning, cameraError, startCamera, stopCamera };
}
