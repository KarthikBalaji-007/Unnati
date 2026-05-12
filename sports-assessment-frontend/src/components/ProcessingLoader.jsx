/**
 * ProcessingLoader.jsx
 * Animated loading state shown while the backend processes the video.
 */

import { motion } from 'framer-motion';

const STEPS = [
    { icon: '📤', label: 'Uploading video to server' },
    { icon: '🤖', label: 'Running MediaPipe pose estimation' },
    { icon: '📐', label: 'Computing test-specific metrics' },
    { icon: '🛡️', label: 'Running cheat detection' },
    { icon: '💾', label: 'Saving results to database' },
];

export default function ProcessingLoader({ step = 0, progress = 0, error = null }) {
    return (
        <motion.div
            className="card"
            style={{ padding: '40px', textAlign: 'center' }}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4 }}
        >
            {error ? (
                <>
                    <div style={{ fontSize: '3rem', marginBottom: '16px' }}>❌</div>
                    <h3 style={{ color: 'var(--accent-red)', marginBottom: '12px' }}>Analysis Failed</h3>
                    <div className="alert alert-danger">{error}</div>
                </>
            ) : (
                <>
                    {/* Animated spinner */}
                    <div style={{ position: 'relative', width: '80px', height: '80px', margin: '0 auto 24px' }}>
                        <motion.div
                            style={{
                                position: 'absolute', inset: 0,
                                border: '3px solid rgba(99,102,241,0.15)',
                                borderTop: '3px solid var(--accent-primary)',
                                borderRadius: '50%',
                            }}
                            animate={{ rotate: 360 }}
                            transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
                        />
                        <div style={{
                            position: 'absolute', inset: '16px',
                            background: 'var(--bg-card)',
                            borderRadius: '50%',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontSize: '1.4rem',
                        }}>
                            {STEPS[Math.min(step, STEPS.length - 1)].icon}
                        </div>
                    </div>

                    <h3 style={{ marginBottom: '8px' }}>Analyzing Video...</h3>
                    <p style={{ fontSize: '0.9rem', marginBottom: '24px' }}>
                        {STEPS[Math.min(step, STEPS.length - 1)].label}
                    </p>

                    {/* Progress bar */}
                    {progress > 0 && (
                        <div style={{ marginBottom: '24px' }}>
                            <div className="progress-track">
                                <motion.div
                                    className="progress-fill"
                                    initial={{ width: 0 }}
                                    animate={{ width: `${progress}%` }}
                                    transition={{ duration: 0.4 }}
                                />
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '6px' }}>
                                {progress}% uploaded
                            </div>
                        </div>
                    )}

                    {/* Steps list */}
                    <div style={{ textAlign: 'left', maxWidth: '320px', margin: '0 auto' }}>
                        {STEPS.map((s, i) => (
                            <div key={i} className="flex gap-3 items-center" style={{ padding: '6px 0' }}>
                                <motion.div
                                    style={{
                                        width: '8px', height: '8px', borderRadius: '50%',
                                        background: i <= step ? 'var(--accent-primary)' : 'rgba(255,255,255,0.1)',
                                        flexShrink: 0,
                                    }}
                                    animate={i === step ? { scale: [1, 1.4, 1], opacity: [1, 0.6, 1] } : {}}
                                    transition={{ duration: 1, repeat: Infinity }}
                                />
                                <span style={{
                                    fontSize: '0.82rem',
                                    color: i < step ? 'var(--accent-green)' : i === step ? 'var(--text-primary)' : 'var(--text-muted)',
                                }}>
                                    {i < step ? '✓ ' : ''}{s.label}
                                </span>
                            </div>
                        ))}
                    </div>
                </>
            )}
        </motion.div>
    );
}
