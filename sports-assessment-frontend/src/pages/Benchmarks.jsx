import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import api from '../services/api';

const TEST_NAMES = { T3: 'Sit & Reach', T4: 'Vertical Jump', T5: 'Broad Jump', T8: 'Shuttle Run', T9: 'Sit-Ups' };

export default function Benchmarks() {
    const [benchmarks, setBenchmarks] = useState({});
    const [genderTab, setGenderTab] = useState('male');

    useEffect(() => {
        api.get('/api/benchmarks').then(r => setBenchmarks(r.data)).catch(() => { });
    }, []);

    const GRADE_COLORS = { A: '#10b981', B: '#06b6d4', C: '#6366f1', D: '#f59e0b', F: '#ef4444' };

    return (
        <div className="page page-with-bottom-nav">
            <div className="container flex-col gap-6">
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                    <h2>📋 SAI Standards & Benchmarks</h2>
                    <p>Performance benchmarks from SAI Annexure A for grading</p>
                </motion.div>

                {/* Gender tabs */}
                <div className="tab-bar" style={{ maxWidth: 300 }}>
                    {['male', 'female'].map(g => (
                        <button key={g} className={`tab ${genderTab === g ? 'active' : ''}`} onClick={() => setGenderTab(g)}>
                            {g === 'male' ? '👨 Men' : '👩 Women'}
                        </button>
                    ))}
                </div>

                {/* Benchmark cards */}
                <div className="flex-col gap-4">
                    {Object.entries(benchmarks).map(([testId, b], i) => (
                        <motion.div
                            key={testId}
                            className="card"
                            style={{ padding: 20 }}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: 0.1 + i * 0.08 }}
                        >
                            <div className="flex items-center justify-between" style={{ marginBottom: 16 }}>
                                <div>
                                    <h3>{TEST_NAMES[testId] || testId}</h3>
                                    <p style={{ fontSize: '0.8rem', margin: 0 }}>
                                        Unit: {b.unit} · {b.higher_is_better ? 'Higher is better ↑' : 'Lower is better ↓'}
                                    </p>
                                </div>
                                <span className="badge badge-info">{testId}</span>
                            </div>

                            <div className="flex gap-3" style={{ flexWrap: 'wrap' }}>
                                {['A', 'B', 'C', 'D'].map(grade => (
                                    <div key={grade} style={{
                                        background: `${GRADE_COLORS[grade]}12`,
                                        border: `1px solid ${GRADE_COLORS[grade]}40`,
                                        borderRadius: 'var(--radius-md)',
                                        padding: '10px 16px',
                                        textAlign: 'center',
                                        flex: 1,
                                        minWidth: 80,
                                    }}>
                                        <div style={{ fontSize: '1.3rem', fontWeight: 900, color: GRADE_COLORS[grade] }}>
                                            {grade}
                                        </div>
                                        <div style={{ fontSize: '0.85rem', fontWeight: 600, marginTop: 2 }}>
                                            {b.higher_is_better ? '≥' : '≤'} {b[genderTab]?.[grade]}
                                        </div>
                                        <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                                            {b.unit}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </motion.div>
                    ))}
                </div>
            </div>
        </div>
    );
}
