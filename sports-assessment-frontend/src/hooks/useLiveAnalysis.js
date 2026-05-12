/**
 * useLiveAnalysis.js
 * Real-time rep counting + form feedback engine using TF.js keypoints.
 * Runs entirely in the browser for live coaching overlay.
 */
import { useState, useRef, useCallback } from 'react';

/* ── Keypoint indices (MoveNet COCO) ── */
const KP = {
  NOSE: 0, L_SHOULDER: 5, R_SHOULDER: 6, L_ELBOW: 7, R_ELBOW: 8,
  L_WRIST: 9, R_WRIST: 10, L_HIP: 11, R_HIP: 12,
  L_KNEE: 13, R_KNEE: 14, L_ANKLE: 15, R_ANKLE: 16,
};

function angle(a, b, c) {
  const ab = [a.x - b.x, a.y - b.y];
  const cb = [c.x - b.x, c.y - b.y];
  const dot = ab[0] * cb[0] + ab[1] * cb[1];
  const magA = Math.sqrt(ab[0] ** 2 + ab[1] ** 2);
  const magC = Math.sqrt(cb[0] ** 2 + cb[1] ** 2);
  const cos = Math.max(-1, Math.min(1, dot / (magA * magC + 1e-8)));
  return Math.acos(cos) * (180 / Math.PI);
}

/* ── Test-specific rep counting logic ── */
const TEST_CONFIGS = {
  T9: { // Sit-Ups
    getState: (kps) => {
      const hip = kps[KP.L_HIP], knee = kps[KP.L_KNEE], shoulder = kps[KP.L_SHOULDER];
      if (!hip || !knee || !shoulder) return null;
      const torsoAngle = angle(shoulder, hip, knee);
      return torsoAngle > 60 ? 'UP' : 'DOWN';
    },
    upState: 'UP', downState: 'DOWN',
    feedback: (kps) => {
      const hip = kps[KP.L_HIP], knee = kps[KP.L_KNEE];
      if (hip && knee && Math.abs(hip.y - knee.y) > 0.3) return { msg: 'Keep knees bent', level: 'yellow' };
      return { msg: 'Great form!', level: 'green' };
    },
  },
  T3: { // Sit & Reach (hold detection)
    getState: (kps) => {
      const wrist = kps[KP.L_WRIST], ankle = kps[KP.L_ANKLE];
      if (!wrist || !ankle) return null;
      return wrist.y > ankle.y - 0.05 ? 'REACHING' : 'IDLE';
    },
    upState: 'REACHING', downState: 'IDLE',
    feedback: () => ({ msg: 'Reach forward steadily', level: 'green' }),
  },
  T4: { // Vertical Jump
    getState: (kps) => {
      const ankle = kps[KP.L_ANKLE], hip = kps[KP.L_HIP];
      if (!ankle || !hip) return null;
      return ankle.y < hip.y - 0.15 ? 'AIR' : 'GROUND';
    },
    upState: 'AIR', downState: 'GROUND',
    feedback: (kps) => {
      const knee = kps[KP.L_KNEE], hip = kps[KP.L_HIP], ankle = kps[KP.L_ANKLE];
      if (knee && hip && ankle) {
        const kneeAngle = angle(hip, knee, ankle);
        if (kneeAngle > 160) return { msg: 'Bend knees more before jumping', level: 'yellow' };
      }
      return { msg: 'Good jump!', level: 'green' };
    },
  },
  T5: { // Broad Jump (same as T4 but horizontal)
    getState: (kps) => {
      const ankle = kps[KP.L_ANKLE], hip = kps[KP.L_HIP];
      if (!ankle || !hip) return null;
      return ankle.y < hip.y - 0.1 ? 'AIR' : 'GROUND';
    },
    upState: 'AIR', downState: 'GROUND',
    feedback: () => ({ msg: 'Jump forward as far as you can', level: 'green' }),
  },
  T8: { // Shuttle Run (direction change detection)
    getState: (kps) => {
      const hip = kps[KP.L_HIP];
      if (!hip) return null;
      return hip.x > 0.5 ? 'RIGHT' : 'LEFT';
    },
    upState: 'RIGHT', downState: 'LEFT',
    feedback: () => ({ msg: 'Sprint! Touch and turn quickly', level: 'green' }),
  },
};

export default function useLiveAnalysis(testType) {
  const [reps, setReps] = useState(0);
  const [accuracy, setAccuracy] = useState(100);
  const [speed, setSpeed] = useState(0);
  const [coaching, setCoaching] = useState({ msg: 'Get ready...', level: 'green' });

  const stateRef = useRef('IDLE');
  const repTimesRef = useRef([]);
  const goodFormCountRef = useRef(0);
  const totalFramesRef = useRef(0);

  const processKeypoints = useCallback((keypoints) => {
    if (!keypoints || keypoints.length < 17) return;

    const config = TEST_CONFIGS[testType];
    if (!config) return;

    totalFramesRef.current++;

    const kps = keypoints.map(kp => ({ x: kp.x, y: kp.y, score: kp.score }));
    const newState = config.getState(kps);
    if (!newState) return;

    const prev = stateRef.current;

    // Rep detection: transition from downState → upState
    if (prev === config.downState && newState === config.upState) {
      const now = Date.now();
      repTimesRef.current.push(now);
      setReps(r => r + 1);

      // Compute speed (sec per rep)
      const times = repTimesRef.current;
      if (times.length >= 2) {
        const dt = (times[times.length - 1] - times[times.length - 2]) / 1000;
        setSpeed(parseFloat(dt.toFixed(1)));
      }
    }

    stateRef.current = newState;

    // Form feedback
    const fb = config.feedback(kps);
    if (fb.level === 'green') goodFormCountRef.current++;
    setCoaching(fb);

    // Accuracy
    const acc = Math.round((goodFormCountRef.current / totalFramesRef.current) * 100);
    setAccuracy(acc);
  }, [testType]);

  const reset = useCallback(() => {
    setReps(0);
    setAccuracy(100);
    setSpeed(0);
    setCoaching({ msg: 'Get ready...', level: 'green' });
    stateRef.current = 'IDLE';
    repTimesRef.current = [];
    goodFormCountRef.current = 0;
    totalFramesRef.current = 0;
  }, []);

  return { reps, accuracy, speed, coaching, processKeypoints, reset };
}
