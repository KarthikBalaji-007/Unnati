import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { getCoachOverview, getCoachRecentSessions } from '../services/api';

export default function CoachDashboard() {
    const [overview, setOverview] = useState(null);
    const [recent, setRecent] = useState([]);
    const [error, setError] = useState('');

    useEffect(() => {
        Promise.all([getCoachOverview(), getCoachRecentSessions(20)])
            .then(([overviewRes, recentRes]) => {
                setOverview(overviewRes.data);
                setRecent(recentRes.data);
            })
            .catch((err) => setError(err.message || 'Failed to load coach dashboard.'));
    }, []);

    return (
        <div className="page page-with-bottom-nav">
            <div className="container flex-col gap-6">
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                    <h2>🧭 Coach Dashboard</h2>
                    <p>Read-only analytics for athlete assessments.</p>
                </motion.div>

                {error && <div className="alert alert-danger">{error}</div>}

                {overview && (
                    <div className="grid-4">
                        <div className="card stat-card"><div className="stat-value">{overview.total_athletes}</div><div className="stat-label">Athletes</div></div>
                        <div className="card stat-card"><div className="stat-value">{overview.total_sessions}</div><div className="stat-label">Sessions</div></div>
                        <div className="card stat-card"><div className="stat-value text-green">{overview.valid_rate_pct}%</div><div className="stat-label">Valid Rate</div></div>
                        <div className="card stat-card"><div className="stat-value text-cyan">{overview.avg_confidence_pct}%</div><div className="stat-label">Avg Confidence</div></div>
                    </div>
                )}

                <div className="card" style={{ padding: 16 }}>
                    <h3 style={{ marginBottom: 12 }}>Recent Sessions</h3>
                    {recent.length === 0 ? (
                        <p>No sessions yet.</p>
                    ) : (
                        <div className="table-wrapper">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Athlete</th>
                                        <th>Test</th>
                                        <th>Status</th>
                                        <th>Grade</th>
                                        <th>Date</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {recent.map((r) => (
                                        <tr key={r.session_id}>
                                            <td>{r.athlete_name || 'Anonymous'}</td>
                                            <td>{r.test_type}</td>
                                            <td>{r.status}</td>
                                            <td>{r.grade || '—'}</td>
                                            <td>{new Date(r.start_time).toLocaleString()}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
