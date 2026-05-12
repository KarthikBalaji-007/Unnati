import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import api from '../services/api';
import ResultCard from '../components/ResultCard';
import { queueMutation } from '../services/offlineQueue';

const TEST_NAMES = { T3: 'Sit & Reach', T4: 'Vertical Jump', T5: 'Broad Jump', T8: 'Shuttle Run', T9: 'Sit-Ups' };

export default function History() {
    const [sessions, setSessions] = useState([]);
    const [selected, setSelected] = useState(null);
    const [detail, setDetail] = useState(null);
    const [loading, setLoading] = useState(true);
    const [message, setMessage] = useState('');

    useEffect(() => {
        api.get('/api/sessions?limit=50')
            .then(r => { setSessions(r.data); setLoading(false); })
            .catch(() => setLoading(false));
    }, []);

    const viewDetail = async (sessionId) => {
        if (selected === sessionId) { setSelected(null); setDetail(null); return; }
        try {
            const r = await api.get(`/api/results/${sessionId}`);
            setDetail(r.data);
            setSelected(sessionId);
        } catch { setSelected(null); setDetail(null); }
    };

    const deleteSession = async (sessionId) => {
        if (!confirm('Delete this session?')) return;
        try {
            await api.delete(`/api/sessions/${sessionId}`);
            setSessions(s => s.filter(x => x.session_id !== sessionId));
            if (selected === sessionId) { setSelected(null); setDetail(null); }
        } catch (err) {
            if (!navigator.onLine) {
                queueMutation({ method: 'delete', url: `/api/sessions/${sessionId}` });
                setSessions(s => s.filter(x => x.session_id !== sessionId));
                if (selected === sessionId) { setSelected(null); setDetail(null); }
                setMessage('Offline: delete queued and will sync when online.');
                return;
            }
            setMessage(err.message || 'Failed to delete session.');
        }
    };

    const exportCsv = () => {
        const header = ['session_id', 'athlete_name', 'test_type', 'primary_metric', 'grade', 'points_awarded', 'status', 'date'];
        const rows = sessions.map((s) => [
            s.session_id,
            s.athlete_name || 'Anonymous',
            s.test_type,
            s.primary_metric ?? '',
            s.grade || '',
            s.points_awarded ?? 0,
            s.status,
            s.start_time ? new Date(s.start_time).toISOString() : '',
        ]);
        const csv = [header, ...rows].map((r) =>
            r.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(',')
        ).join('\n');
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `unnati-history-${new Date().toISOString().slice(0, 10)}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const printReport = () => {
        const htmlRows = sessions.map((s) => `
            <tr>
                <td>${s.athlete_name || 'Anonymous'}</td>
                <td>${s.test_type}</td>
                <td>${s.primary_metric ?? '—'}</td>
                <td>${s.grade || '—'}</td>
                <td>${s.points_awarded ?? 0}</td>
                <td>${s.start_time ? new Date(s.start_time).toLocaleString() : '—'}</td>
            </tr>
        `).join('');
        const w = window.open('', '_blank');
        if (!w) return;
        w.document.write(`
            <html><head><title>Unnati History Report</title></head>
            <body>
                <h2>Unnati - Test History Report</h2>
                <table border="1" cellspacing="0" cellpadding="6">
                    <thead><tr><th>Athlete</th><th>Test</th><th>Metric</th><th>Grade</th><th>Points</th><th>Date</th></tr></thead>
                    <tbody>${htmlRows}</tbody>
                </table>
            </body></html>
        `);
        w.document.close();
        w.focus();
        w.print();
    };

    if (loading) return <div className="page page-with-bottom-nav container"><p>Loading...</p></div>;

    return (
        <div className="page page-with-bottom-nav">
            <div className="container flex-col gap-6">
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                    <h2>📊 Test History</h2>
                    <p>{sessions.length} sessions recorded</p>
                </motion.div>
                {message && <div className={`alert ${message.startsWith('Offline') ? 'alert-warning' : 'alert-danger'}`}>{message}</div>}
                <div className="flex gap-3">
                    <button className="btn btn-secondary btn-sm" onClick={exportCsv} type="button">Export CSV</button>
                    <button className="btn btn-secondary btn-sm" onClick={printReport} type="button">Print / Save as PDF</button>
                </div>

                {sessions.length === 0 ? (
                    <div className="card" style={{ padding: 40, textAlign: 'center' }}>
                        <p style={{ fontSize: '2rem' }}>📋</p>
                        <p>No test sessions yet. Go to Tests to get started!</p>
                    </div>
                ) : (
                    <div className="flex-col gap-3">
                        {sessions.map((s, i) => (
                            <motion.div
                                key={s.session_id}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: i * 0.05 }}
                            >
                                <div className="card" style={{ padding: 16 }}>
                                    <div className="flex items-center gap-4" style={{ cursor: 'pointer' }} onClick={() => viewDetail(s.session_id)}>
                                        {s.grade ? (
                                            <div className={`grade-badge grade-${s.grade}`} style={{ width: 42, height: 42, fontSize: '1.1rem' }}>{s.grade}</div>
                                        ) : (
                                            <div className="grade-badge" style={{ width: 42, height: 42, fontSize: '1.1rem', background: 'var(--bg-card)', border: '1px solid var(--glass-border)' }}>—</div>
                                        )}
                                        <div style={{ flex: 1 }}>
                                            <h4>{TEST_NAMES[s.test_type] || s.test_type}</h4>
                                            <p style={{ fontSize: '0.8rem', margin: 0 }}>
                                                {s.athlete_name || 'Anonymous'} · {s.primary_metric != null ? s.primary_metric.toFixed(1) : '—'}
                                                {s.points_awarded > 0 && <span className="text-green"> · +{s.points_awarded}pts</span>}
                                            </p>
                                        </div>
                                        <div style={{ textAlign: 'right' }}>
                                            <span className={`badge ${s.valid ? 'badge-success' : 'badge-danger'}`}>
                                                {s.valid ? 'Valid' : 'Invalid'}
                                            </span>
                                            <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', margin: '4px 0 0' }}>
                                                {new Date(s.start_time).toLocaleDateString()}
                                            </p>
                                        </div>
                                    </div>

                                    {/* Expanded detail */}
                                    {selected === s.session_id && detail && (
                                        <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} style={{ marginTop: 16, overflow: 'hidden' }}>
                                            <div className="divider" />
                                            <ResultCard result={detail} testType={s.test_type} />
                                            <button className="btn btn-danger btn-sm" style={{ marginTop: 12 }} onClick={() => deleteSession(s.session_id)}>
                                                🗑 Delete Session
                                            </button>
                                        </motion.div>
                                    )}
                                </div>
                            </motion.div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
