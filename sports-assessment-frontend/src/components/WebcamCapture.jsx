import { useRef, useState, useEffect, useCallback } from 'react';
import usePoseDetection from '../hooks/usePoseDetection';
import useLiveAnalysis from '../hooks/useLiveAnalysis';

export default function WebcamCapture({ testType, onRecordingComplete, maxDuration = 60 }) {
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const mediaRecorderRef = useRef(null);
    const chunksRef = useRef([]);
    const timerRef = useRef(null);

    const [stream, setStream] = useState(null);
    const [recording, setRecording] = useState(false);
    const [elapsed, setElapsed] = useState(0);
    const [error, setError] = useState(null);
    const [facingMode, setFacingMode] = useState('environment');

    // Hooks
    const { isModelLoaded, startDetection, stopDetection } = usePoseDetection(videoRef, canvasRef);
    const { reps, accuracy, speed, coaching, processKeypoints, reset: resetAnalysis } = useLiveAnalysis(testType);

    // Start camera
    const startCamera = useCallback(async () => {
        try {
            const s = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: facingMode, width: { ideal: 640 }, height: { ideal: 480 } },
                audio: false,
            });
            setStream(s);
            if (videoRef.current) {
                videoRef.current.srcObject = s;
                videoRef.current.play();
            }
        } catch (e) {
            setError('Camera access denied. Please allow camera permissions.');
        }
    }, [facingMode]);

    useEffect(() => {
        stream?.getTracks().forEach(t => t.stop());
        startCamera();
        return () => { stream?.getTracks().forEach(t => t.stop()); };
    }, [facingMode]);

    // Pose detection callback — feed keypoints to live analysis
    useEffect(() => {
        if (stream && isModelLoaded && recording) {
            startDetection((keypoints) => {
                processKeypoints(keypoints);
            });
        }
        return () => stopDetection();
    }, [stream, isModelLoaded, recording]);

    // Start recording
    const startRecording = () => {
        if (!stream) return;
        resetAnalysis();
        chunksRef.current = [];
        const mr = new MediaRecorder(stream, { mimeType: 'video/webm' });
        mr.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data); };
        mr.onstop = () => {
            const blob = new Blob(chunksRef.current, { type: 'video/webm' });
            onRecordingComplete(blob);
        };
        mr.start();
        mediaRecorderRef.current = mr;
        setRecording(true);
        setElapsed(0);

        timerRef.current = setInterval(() => {
            setElapsed(prev => {
                if (prev + 1 >= maxDuration) { stopRecording(); return prev; }
                return prev + 1;
            });
        }, 1000);
    };

    const stopRecording = () => {
        if (mediaRecorderRef.current?.state === 'recording') {
            mediaRecorderRef.current.stop();
        }
        clearInterval(timerRef.current);
        setRecording(false);
        stopDetection();
    };

    const formatTime = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

    if (error) return <div className="alert alert-danger">{error}</div>;

    return (
        <div className="video-container" style={{ position: 'relative' }}>
            <video ref={videoRef} playsInline muted style={{ width: '100%', borderRadius: 'var(--radius-lg)' }} />
            <canvas ref={canvasRef} className="pose-canvas" />
            <button
                type="button"
                onClick={() => setFacingMode(f => f === 'user' ? 'environment' : 'user')}
                disabled={recording}
                style={{ position: 'absolute', top: 12, right: 12, zIndex: 3, padding: '8px 12px' }}
            >
                {facingMode === 'user' ? ' Rear' : ' Front'}
            </button>

            {/* ── Coaching HUD (visible during recording) ── */}
            {recording && (
                <>
                    <div className="coaching-hud">
                        <div className="hud-metric">
                            <div className="hud-metric-value text-cyan">{accuracy}%</div>
                            <div className="hud-metric-label">Accuracy</div>
                        </div>
                        <div className="hud-metric">
                            <div className="hud-metric-value" style={{ color: 'var(--accent-orange)' }}>{formatTime(elapsed)}</div>
                            <div className="hud-metric-label">Time</div>
                        </div>
                        <div className="hud-metric">
                            <div className="hud-metric-value text-green">{speed}s</div>
                            <div className="hud-metric-label">Speed/Rep</div>
                        </div>
                    </div>

                    {/* Rep counter */}
                    <div className="rep-counter">{reps}</div>

                    {/* Coaching bar */}
                    <div className={`coaching-bar coaching-${coaching.level}`} key={coaching.msg}>
                        {coaching.msg}
                    </div>
                </>
            )}

            {/* ── Controls ── */}
            <div style={{ padding: 16, display: 'flex', gap: 12, justifyContent: 'center' }}>
                {!recording ? (
                    <button className="btn btn-primary btn-lg" onClick={startRecording} disabled={!stream}>
                        🔴 Start Recording
                    </button>
                ) : (
                    <button className="btn btn-danger btn-lg" onClick={stopRecording}>
                        ⏹ Stop ({formatTime(maxDuration - elapsed)} left)
                    </button>
                )}
            </div>

            {/* Model loading indicator */}
            {!isModelLoaded && (
                <div className="alert alert-info" style={{ margin: '0 16px 16px' }}>
                    ⏳ Loading AI pose detection model...
                </div>
            )}
        </div>
    );
}
