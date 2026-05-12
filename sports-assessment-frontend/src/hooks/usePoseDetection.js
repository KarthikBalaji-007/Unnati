/**
 * usePoseDetection.js
 * Custom React hook for real-time TF.js MoveNet pose detection on webcam frames.
 * Supports a keypoint callback for the live analysis engine.
 */

import { useRef, useState, useCallback, useEffect } from 'react';

// Lazy-load TF.js to avoid blocking initial render
let poseDetectionModule = null;
let tfModule = null;
let detectorInstance = null;  // singleton detector

async function loadModules() {
  if (!tfModule) {
    tfModule = await import('@tensorflow/tfjs');
    await tfModule.setBackend('webgl').catch(() => tfModule.setBackend('cpu'));
    await tfModule.ready();
  }
  if (!poseDetectionModule) {
    poseDetectionModule = await import('@tensorflow-models/pose-detection');
  }
  if (!detectorInstance) {
    detectorInstance = await poseDetectionModule.createDetector(
      poseDetectionModule.SupportedModels.MoveNet,
      { modelType: poseDetectionModule.movenet.modelType.SINGLEPOSE_LIGHTNING, enableSmoothing: true }
    );
  }
  return detectorInstance;
}

export default function usePoseDetection(videoRef, canvasRef) {
  const animFrameRef = useRef(null);
  const callbackRef = useRef(null);
  const [isModelLoaded, setIsModelLoaded] = useState(false);

  // Load detector on mount
  useEffect(() => {
    loadModules()
      .then(() => setIsModelLoaded(true))
      .catch(() => {});
  }, []);

  const startDetection = useCallback((onKeypoints) => {
    callbackRef.current = onKeypoints || null;
    const videoEl = videoRef?.current;
    const canvasEl = canvasRef?.current;
    if (!detectorInstance || !videoEl) return;

    const detect = async () => {
      if (!videoEl || videoEl.readyState < 2) {
        animFrameRef.current = requestAnimationFrame(detect);
        return;
      }
      try {
        const poses = await detectorInstance.estimatePoses(videoEl);
        if (poses.length > 0) {
          const pts = poses[0].keypoints;
          if (canvasEl) _drawSkeleton(canvasEl, pts, videoEl.videoWidth, videoEl.videoHeight);
          if (callbackRef.current) callbackRef.current(pts);
        }
      } catch (_) {}
      animFrameRef.current = requestAnimationFrame(detect);
    };

    animFrameRef.current = requestAnimationFrame(detect);
  }, [videoRef, canvasRef]);

  const stopDetection = useCallback(() => {
    if (animFrameRef.current) {
      cancelAnimationFrame(animFrameRef.current);
      animFrameRef.current = null;
    }
    callbackRef.current = null;
  }, []);

  useEffect(() => () => stopDetection(), [stopDetection]);

  return { isModelLoaded, startDetection, stopDetection };
}

// ─── Skeleton Drawing ─────────────────────────────────────────────────────────
const CONNECTIONS = [
  [0,1],[0,2],[1,3],[2,4],
  [5,6],
  [5,7],[7,9],
  [6,8],[8,10],
  [5,11],[6,12],
  [11,12],
  [11,13],[13,15],
  [12,14],[14,16],
];

function _drawSkeleton(canvas, keypoints, videoW, videoH) {
  const ctx = canvas.getContext('2d');
  const scaleX = canvas.width  / (videoW || 640);
  const scaleY = canvas.height / (videoH || 480);

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // Connections — thicker lines with glow
  ctx.lineWidth = 3;
  ctx.shadowBlur = 6;
  CONNECTIONS.forEach(([a, b]) => {
    const ptA = keypoints[a], ptB = keypoints[b];
    if (!ptA || !ptB) return;
    if ((ptA.score ?? 1) < 0.3 || (ptB.score ?? 1) < 0.3) return;

    const alpha = Math.min(ptA.score ?? 1, ptB.score ?? 1);
    ctx.strokeStyle = `rgba(99,102,241,${alpha})`;
    ctx.shadowColor = 'rgba(99,102,241,0.4)';
    ctx.beginPath();
    ctx.moveTo(ptA.x * scaleX, ptA.y * scaleY);
    ctx.lineTo(ptB.x * scaleX, ptB.y * scaleY);
    ctx.stroke();
  });

  // Keypoints
  ctx.shadowBlur = 0;
  keypoints.forEach(pt => {
    if (!pt || (pt.score ?? 1) < 0.3) return;
    ctx.fillStyle = `rgba(6,182,212,${pt.score ?? 1})`;
    ctx.beginPath();
    ctx.arc(pt.x * scaleX, pt.y * scaleY, 5, 0, Math.PI * 2);
    ctx.fill();
  });
}
