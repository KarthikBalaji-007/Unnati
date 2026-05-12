import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import api, { getMyAthlete, linkAthlete } from '../services/api';
import { queueMutation } from '../services/offlineQueue';

const RANK_ICONS = { Bronze: '🥉', Silver: '🥈', Gold: '🥇', Platinum: '💎' };

export default function Profile() {
    const [athlete, setAthlete] = useState(null);
    const [history, setHistory] = useState([]);
    const [showRegister, setShowRegister] = useState(false);
    const [form, setForm] = useState({ name: '', age: '', gender: 'male', location: '', organization: '' });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [availableAthletes, setAvailableAthletes] = useState([]);
    const [selectedAthleteId, setSelectedAthleteId] = useState('');

    useEffect(() => {
        Promise.all([
            getMyAthlete().catch(() => null),
            api.get('/api/athletes').catch(() => ({ data: [] })),
        ]).then(([mine, all]) => {
            if (mine?.data) {
                setAthlete(mine.data);
                loadHistory(mine.data.athlete_id);
            } else if (all.data.length > 0) {
                setAvailableAthletes(all.data);
                setSelectedAthleteId(all.data[0].athlete_id);
                setShowRegister(true);
            } else {
                setShowRegister(true);
            }
            setLoading(false);
        }).catch(() => setLoading(false));
    }, []);

    const loadHistory = (id) => {
        api.get(`/api/athletes/${id}/history`).then(r => setHistory(r.data)).catch(() => { });
    };

    const register = async () => {
        setError('');
        const name = form.name.trim();
        const age = parseInt(form.age, 10);
        if (!name || name.length < 2) {
            setError('Name must be at least 2 characters.');
            return;
        }
        if (!Number.isFinite(age) || age < 5 || age > 80) {
            setError('Age must be between 5 and 80.');
            return;
        }
        try {
            const res = await api.post('/api/athletes', {
                name,
                age,
                gender: form.gender,
                location: form.location.trim() || null,
                organization: form.organization.trim() || null,
            });
            setAthlete(res.data);
            setShowRegister(false);
        } catch (err) {
            if (!navigator.onLine) {
                queueMutation({
                    method: 'post',
                    url: '/api/athletes',
                    data: {
                        name,
                        age,
                        gender: form.gender,
                        location: form.location.trim() || null,
                        organization: form.organization.trim() || null,
                    },
                });
                setError('Offline: profile queued and will sync when online.');
                return;
            }
            setError(err.message || 'Registration failed');
        }
    };

    const linkSelectedAthlete = async () => {
        if (!selectedAthleteId) return;
        try {
            const res = await linkAthlete(selectedAthleteId);
            setAthlete(res.data);
            setShowRegister(false);
            loadHistory(res.data.athlete_id);
        } catch (err) {
            setError(err.message || 'Failed to link athlete profile.');
        }
    };

    if (loading) return <div className="page page-with-bottom-nav container" style={{ paddingTop: 60 }}><p>Loading...</p></div>;

    if (showRegister) {
        return (
            <div className="page page-with-bottom-nav">
                <div className="container" style={{ maxWidth: 480 }}>
                    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                        <h2 style={{ marginBottom: 24 }}>Create Your Profile</h2>
                        <div className="card flex-col gap-4" style={{ padding: 24 }}>
                            {availableAthletes.length > 0 && (
                                <>
                                    <label className="section-label">Link Existing Athlete</label>
                                    <div className="flex gap-2">
                                        <select className="input" value={selectedAthleteId} onChange={e => setSelectedAthleteId(e.target.value)}>
                                            {availableAthletes.map(a => (
                                                <option key={a.athlete_id} value={a.athlete_id}>{a.name} ({a.age}, {a.gender})</option>
                                            ))}
                                        </select>
                                        <button className="btn btn-secondary" onClick={linkSelectedAthlete} type="button">
                                            Link
                                        </button>
                                    </div>
                                    <div className="divider" />
                                </>
                            )}
                            <input className="input" placeholder="Full Name *" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
                            <input className="input" type="number" placeholder="Age *" value={form.age} onChange={e => setForm({ ...form, age: e.target.value })} />
                            <select className="input" value={form.gender} onChange={e => setForm({ ...form, gender: e.target.value })}>
                                <option value="male">Male</option>
                                <option value="female">Female</option>
                                <option value="other">Other</option>
                            </select>
                            <input className="input" placeholder="Location (optional)" value={form.location} onChange={e => setForm({ ...form, location: e.target.value })} />
                            <input className="input" placeholder="Organization (optional)" value={form.organization} onChange={e => setForm({ ...form, organization: e.target.value })} />
                            {error && <div className={`alert ${error.startsWith('Offline') ? 'alert-warning' : 'alert-danger'}`}>{error}</div>}
                            <button className="btn btn-primary btn-lg" style={{ width: '100%', justifyContent: 'center' }} onClick={register} disabled={!form.name || !form.age}>
                                Create Profile
                            </button>
                        </div>
                    </motion.div>
                </div>
            </div>
        );
    }

    return (
        <div className="page page-with-bottom-nav">
            <div className="container flex-col gap-6">
                {/* Profile header */}
                <motion.div className="card" style={{ padding: 24, textAlign: 'center' }} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                    <div style={{ fontSize: '3rem', marginBottom: 8 }}>
                        {RANK_ICONS[athlete?.rank_level] || '🥉'}
                    </div>
                    <h2>{athlete?.name}</h2>
                    <p style={{ margin: '4px 0' }}>{athlete?.gender} · {athlete?.age} yrs · {athlete?.location || 'Unknown'}</p>
                    {athlete?.organization && <span className="badge badge-info">{athlete.organization}</span>}
                </motion.div>

                {/* Stats */}
                <div className="grid-4">
                    {[
                        { value: athlete?.total_points || 0, label: 'Points', color: 'var(--accent-primary)' },
                        { value: athlete?.rank_level || 'Bronze', label: 'Rank', color: 'var(--accent-green)' },
                        { value: (athlete?.badges || []).length, label: 'Badges', color: 'var(--accent-orange)' },
                        { value: athlete?.tests_completed || 0, label: 'Tests', color: 'var(--accent-secondary)' },
                    ].map((s, i) => (
                        <motion.div key={s.label} className="card stat-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + i * 0.08 }}>
                            <div className="stat-value" style={{ color: s.color }}>{s.value}</div>
                            <div className="stat-label">{s.label}</div>
                        </motion.div>
                    ))}
                </div>

                {/* Badges */}
                {(athlete?.badges || []).length > 0 && (
                    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                        <h3 style={{ marginBottom: 12 }}>Badges Earned</h3>
                        <div className="flex gap-3" style={{ flexWrap: 'wrap' }}>
                            {(athlete.badge_details || []).map(b => (
                                <div key={b.id} className="card" style={{ padding: '12px 16px', textAlign: 'center' }}>
                                    <div style={{ fontSize: '1.8rem' }}>{b.icon}</div>
                                    <div style={{ fontSize: '0.8rem', fontWeight: 600, marginTop: 4 }}>{b.name}</div>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                )}

                {/* Test History */}
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
                    <h3 style={{ marginBottom: 12 }}>Test History</h3>
                    {history.length === 0 ? (
                        <p>No tests taken yet. Go to Tests to get started!</p>
                    ) : (
                        <div className="table-wrapper">
                            <table>
                                <thead>
                                    <tr>
                                        <th>Test</th>
                                        <th>Result</th>
                                        <th>Grade</th>
                                        <th>Points</th>
                                        <th>Date</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {history.map(h => (
                                        <tr key={h.session_id}>
                                            <td>{h.test_type}</td>
                                            <td>{h.primary_metric != null ? h.primary_metric.toFixed(1) : '—'}</td>
                                            <td>{h.grade ? <span className={`grade-badge grade-${h.grade}`} style={{ width: 32, height: 32, fontSize: '0.9rem' }}>{h.grade}</span> : '—'}</td>
                                            <td className="text-green">+{h.points_awarded}</td>
                                            <td style={{ color: 'var(--text-muted)' }}>{h.start_time ? new Date(h.start_time).toLocaleDateString() : '—'}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </motion.div>
            </div>
        </div>
    );
}
