import { motion } from 'framer-motion';

const TEST_NAMES = { T3: 'Sit & Reach', T4: 'Vertical Jump', T5: 'Broad Jump', T8: 'Shuttle Run', T9: 'Sit-Ups' };
const UNITS = { T3: 'cm', T4: 'cm', T5: 'cm', T8: 'sec', T9: 'reps' };

export default function ResultCard({ result, testType }) {
    if (!result) return null;

    const { primary_metric, secondary_metrics, valid, confidence_score, cheat_flags, cheat_score, grade, form_score, points_awarded, benchmark_threshold } = result;

    const gradeLabel = grade || 'F';
    const testName = TEST_NAMES[testType] || testType;
    const benchmarkPct = (primary_metric && benchmark_threshold)
        ? Math.min(100, Math.round((primary_metric / benchmark_threshold) * 100))
        : 0;
    const isLowerBetter = testType === 'T8' || testName?.toLowerCase().includes('shuttle');
    const displayPercent = isLowerBetter ? 100 - benchmarkPct : benchmarkPct;

    return (
        <motion.div className="card" style={{ padding: 24, overflow: 'hidden' }} initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}>

            {/* ── Header: Grade + Primary metric ── */}
                <div className="flex items-center gap-6" style={{ marginBottom: 20 }}>
                <div className={`grade-badge grade-badge-lg grade-${gradeLabel}`}>
                    {gradeLabel}
                </div>
                <div style={{ flex: 1 }}>
                    <div className="section-label">{testName}</div>
                    <div className="metric-value">
                        {primary_metric != null ? primary_metric.toFixed(1) : '—'}
                    </div>
                    <div className="metric-unit">{UNITS[testType] || ''}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                    <span className={`badge ${valid ? 'badge-success' : 'badge-danger'}`}>
                        {valid ? '✓ Valid' : '✗ Invalid'}
                    </span>
                    {points_awarded > 0 && (
                        <div className="text-green" style={{ fontSize: '1.2rem', fontWeight: 900, marginTop: 4 }}>
                            +{points_awarded} pts
                        </div>
                    )}
                </div>
            </div>

            {/* ── Benchmark comparison bar ── */}
            {benchmark_threshold && (
                <div style={{ marginBottom: 20 }}>
                    <div className="flex justify-between" style={{ fontSize: '0.75rem', marginBottom: 4 }}>
                        <span className="text-muted">vs Grade A benchmark ({benchmark_threshold}) {isLowerBetter && '(lower is better)'}</span>
                        <span style={{ fontWeight: 700 }}>{displayPercent}%</span>
                    </div>
                    <div className="progress-track" style={{ height: 8 }}>
                        <div className="progress-fill" style={{
                            width: `${displayPercent}%`,
                            background: displayPercent >= 100 ? 'var(--grad-green)' : displayPercent >= 60 ? 'var(--grad-secondary)' : 'var(--grad-primary)',
                        }} />
                    </div>
                </div>
            )}

            {/* ── Metrics row: Confidence + Form + Cheat ── */}
            <div className="grid-3" style={{ marginBottom: 20 }}>
                <div className="card stat-card" style={{ padding: 12 }}>
                    <div className="stat-value text-cyan" style={{ fontSize: '1.4rem' }}>
                        {confidence_score != null ? `${(confidence_score * 100).toFixed(0)}%` : '—'}
                    </div>
                    <div className="stat-label">Confidence</div>
                </div>
                <div className="card stat-card" style={{ padding: 12 }}>
                    <div className="stat-value text-green" style={{ fontSize: '1.4rem' }}>
                        {form_score != null ? `${form_score.toFixed(0)}%` : '—'}
                    </div>
                    <div className="stat-label">Form Score</div>
                </div>
                <div className="card stat-card" style={{ padding: 12 }}>
                    <div className={`stat-value ${cheat_score > 0.3 ? 'text-red' : 'text-green'}`} style={{ fontSize: '1.4rem' }}>
                        {cheat_score != null ? cheat_score.toFixed(2) : '0.00'}
                    </div>
                    <div className="stat-label">Cheat Score</div>
                </div>
            </div>

            {/* ── Secondary metrics ── */}
            {secondary_metrics && Object.keys(secondary_metrics).length > 0 && (
                <div style={{ marginBottom: 16 }}>
                    <div className="section-label">Detail Metrics</div>
                    <div className="flex gap-3" style={{ flexWrap: 'wrap' }}>
                        {Object.entries(secondary_metrics)
                            .filter(([k, v]) => typeof v !== 'object')
                            .map(([k, v]) => (
                                <div key={k} className="card" style={{ padding: '8px 14px', fontSize: '0.85rem' }}>
                                    <span className="text-muted">{k.replace(/_/g, ' ')}: </span>
                                    <span style={{ fontWeight: 700 }}>{typeof v === 'number' ? v.toFixed(2) : String(v)}</span>
                                </div>
                            ))}
                    </div>
                </div>
            )}

            {/* ── Cheat flags ── */}
            {cheat_flags && cheat_flags.length > 0 && (
                <div className="alert alert-warning" style={{ marginTop: 8 }}>
                    ⚠️ {cheat_flags.join(' · ')}
                </div>
            )}
        </motion.div>
    );
}
