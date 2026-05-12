import { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import api from '../services/api';
import VideoUploader from '../components/VideoUploader';
import WebcamCapture from '../components/WebcamCapture';
import ProcessingLoader from '../components/ProcessingLoader';
import ResultCard from '../components/ResultCard';

const TESTS = [
    { id: 'T3', name: 'Sit & Reach', icon: '🧘', desc: 'Measure flexibility by reaching forward' },
    { id: 'T4', name: 'Vertical Jump', icon: '🦘', desc: 'Jump as high as you can from standing' },
    { id: 'T5', name: 'Broad Jump', icon: '🏃', desc: 'Jump forward as far as possible' },
    { id: 'T8', name: 'Shuttle Run', icon: '⚡', desc: 'Sprint 4×10m touching the line each time' },
    { id: 'T9', name: 'Sit-Ups', icon: '💪', desc: 'Perform as many sit-ups as you can' },
];

const STEPS = ['select', 'input', 'countdown', 'capture', 'processing', 'result'];

export default function TestRunner() {
    const [searchParams] = useSearchParams();
    const [step, setStep] = useState('select');
    const [testType, setTestType] = useState(searchParams.get('type') || '');
    const [inputMode, setInputMode] = useState('upload'); // upload | webcam
    const [file, setFile] = useState(null);
    const [athleteId, setAthleteId] = useState('');
    const [athletes, setAthletes] = useState([]);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    const [processing, setProcessing] = useState(false);
    const [countdown, setCountdown] = useState(null);
    const countdownTimer = useRef(null);

    // Load athletes
    useEffect(() => {
        api.get('/api/athletes').then(r => {
            setAthletes(r.data);
            if (r.data.length > 0) setAthleteId(r.data[0].athlete_id);
        }).catch(() => { });
    }, []);

    // Pre-select test from URL
    useEffect(() => {
        const t = searchParams.get('type');
        if (t && TESTS.find(x => x.id === t)) { setTestType(t); setStep('input'); }
    }, [searchParams]);

    // ── Countdown sequence ──
    const startCountdown = () => {
        setStep('countdown');
        let count = 3;
        setCountdown(count);
        countdownTimer.current = setInterval(() => {
            count--;
            if (count > 0) {
                setCountdown(count);
            } else if (count === 0) {
                setCountdown('GO');
            } else {
                clearInterval(countdownTimer.current);
                setStep('capture');
                setCountdown(null);
            }
        }, 1000);
    };

    // ── Handle file selected (upload mode) ──
    const handleFileSelect = (f) => { setFile(f); };

    // ── Handle webcam recording complete ──
    const handleRecordingComplete = (blob) => {
        const f = new File([blob], 'webcam-recording.webm', { type: 'video/webm' });
        setFile(f);
        analyze(f);
    };

    // ── Analyze ──
    const analyze = async (videoFile = file) => {
        if (!videoFile) return;
        setStep('processing');
        setProcessing(true);
        setError(null);

        try {
            // Upload
            const formData = new FormData();
            formData.append('file', videoFile);
            const uploadRes = await api.post('/api/upload', formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            const fileId = uploadRes.data.file_id;

            // Process
            const processRes = await api.post('/api/process', {
                file_id: fileId,
                test_type: testType,
                athlete_id: athleteId || null,
            });

            setResult(processRes.data.result);
            setStep('result');
        } catch (err) {
            setError(err.response?.data?.detail || err.message || 'Analysis failed');
            setStep('result');
        } finally {
            setProcessing(false);
        }
    };

    // ── Reset ──
    const resetAll = () => {
        setStep('select');
        setTestType('');
        setFile(null);
        setResult(null);
        setError(null);
        setProcessing(false);
    };

    const testInfo = TESTS.find(t => t.id === testType);

    return (
        <div className="page page-with-bottom-nav">
            <div className="container" style={{ maxWidth: 720 }}>
                <AnimatePresence mode="wait">

                    {/* ─── Step: Test Selection ─── */}
                    {step === 'select' && (
                        <motion.div key="select" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                            <h2 style={{ marginBottom: 20 }}>Select a Test</h2>
                            <div className="flex-col gap-3">
                                {TESTS.map(t => (
                                    <div
                                        key={t.id}
                                        className="card flex items-center gap-4"
                                        style={{ padding: 16, cursor: 'pointer' }}
                                        onClick={() => { setTestType(t.id); setStep('input'); }}
                                    >
                                        <span style={{ fontSize: '2rem' }}>{t.icon}</span>
                                        <div style={{ flex: 1 }}>
                                            <h4>{t.name}</h4>
                                            <p style={{ fontSize: '0.8rem', margin: 0 }}>{t.desc}</p>
                                        </div>
                                        <span className="badge badge-info">{t.id}</span>
                                    </div>
                                ))}
                            </div>
                        </motion.div>
                    )}

                    {/* ─── Step: Input Mode + File/Webcam ─── */}
                    {step === 'input' && (
                        <motion.div key="input" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-col gap-6">
                            <div>
                                <button className="btn btn-secondary btn-sm" onClick={() => { setStep('select'); setTestType(''); }} style={{ marginBottom: 12 }}>← Back</button>
                                <h2>{testInfo?.icon} {testInfo?.name}</h2>
                                <p>{testInfo?.desc}</p>
                            </div>

                            {/* Athlete selector */}
                            {athletes.length > 0 && (
                                <div>
                                    <label className="section-label">Select Athlete</label>
                                    <select className="input" value={athleteId} onChange={e => setAthleteId(e.target.value)}>
                                        {athletes.map(a => <option key={a.athlete_id} value={a.athlete_id}>{a.name}</option>)}
                                    </select>
                                </div>
                            )}

                            {/* Mode tabs */}
                            <div className="tab-bar">
                                <button className={`tab ${inputMode === 'upload' ? 'active' : ''}`} onClick={() => setInputMode('upload')}>📁 Upload Video</button>
                                <button className={`tab ${inputMode === 'webcam' ? 'active' : ''}`} onClick={() => setInputMode('webcam')}>📷 Live Webcam</button>
                            </div>

                            {inputMode === 'upload' ? (
                                <div className="flex-col gap-4">
                                    <VideoUploader onFileSelected={handleFileSelect} />
                                    {file && (
                                        <button className="btn btn-primary btn-lg" style={{ width: '100%', justifyContent: 'center' }} onClick={() => analyze()}>
                                            🚀 Analyze Video
                                        </button>
                                    )}
                                </div>
                            ) : (
                                <div className="flex-col gap-4">
                                    <div className="alert alert-info">💡 Position yourself so your full body is visible. Press Start when ready.</div>
                                    <button className="btn btn-primary btn-lg" style={{ width: '100%', justifyContent: 'center' }} onClick={startCountdown}>
                                        🎯 Start Live Test
                                    </button>
                                </div>
                            )}
                        </motion.div>
                    )}

                    {/* ─── Step: Countdown ─── */}
                    {step === 'countdown' && (
                        <motion.div key="countdown" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                            <div className="countdown-overlay">
                                {countdown === 'GO' ? (
                                    <div className="countdown-go" key="go">GO!</div>
                                ) : (
                                    <div className="countdown-number" key={countdown}>{countdown}</div>
                                )}
                            </div>
                        </motion.div>
                    )}

                    {/* ─── Step: Live Capture ─── */}
                    {step === 'capture' && (
                        <motion.div key="capture" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                            <h3 style={{ marginBottom: 12 }}>{testInfo?.icon} {testInfo?.name} — Recording</h3>
                            <WebcamCapture testType={testType} onRecordingComplete={handleRecordingComplete} maxDuration={60} />
                        </motion.div>
                    )}

                    {/* ─── Step: Processing ─── */}
                    {step === 'processing' && (
                        <motion.div key="processing" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                            <ProcessingLoader testType={testType} />
                        </motion.div>
                    )}

                    {/* ─── Step: Result ─── */}
                    {step === 'result' && (
                        <motion.div key="result" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-col gap-6">
                            {error ? (
                                <div className="alert alert-danger">
                                    <h3>❌ Analysis Failed</h3>
                                    <p style={{ marginTop: 8 }}>{error}</p>
                                </div>
                            ) : result ? (
                                <>
                                    <div className="celebration">
                                        <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', damping: 8 }}>
                                            <div style={{ fontSize: '4rem' }}>🎉</div>
                                            <h2 className="celebration-title">Test Completed!</h2>
                                        </motion.div>
                                    </div>
                                    <ResultCard result={result} testType={testType} />
                                </>
                            ) : null}

                            <button className="btn btn-secondary btn-lg" style={{ width: '100%', justifyContent: 'center' }} onClick={resetAll}>
                                ← Take Another Test
                            </button>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}
