import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import api from '../services/api';

const RANK_ICONS = { Bronze: '🥉', Silver: '🥈', Gold: '🥇', Platinum: '💎' };

const TESTS = [
    { id: 'T3', name: 'Sit & Reach', icon: '🧘', desc: 'Flexibility test', color: '#10b981' },
    { id: 'T4', name: 'Vertical Jump', icon: '🦘', desc: 'Explosive power', color: '#6366f1' },
    { id: 'T5', name: 'Broad Jump', icon: '🏃', desc: 'Lower body power', color: '#06b6d4' },
    { id: 'T8', name: 'Shuttle Run', icon: '⚡', desc: 'Agility & speed', color: '#f59e0b' },
    { id: 'T9', name: 'Sit-Ups', icon: '💪', desc: 'Core strength', color: '#ef4444' },
];

const QUICK_ACTIONS = [
    { path: '/test', icon: '🎯', label: 'Take Test' },
    { path: '/leaderboard', icon: '🏆', label: 'Leaderboard' },
    { path: '/benchmarks', icon: '📋', label: 'Benchmarks' },
    { path: '/history', icon: '📊', label: 'History' },
    { path: '/sessions', icon: '🔐', label: 'Sessions' },
    { path: '/coach', icon: '🧭', label: 'Coach View' },
];

export default function Dashboard() {
    const [athlete, setAthlete] = useState(null);
    const [recentSessions, setRecentSessions] = useState([]);
    const [showReminder, setShowReminder] = useState(false);

    useEffect(() => {
        api.get('/api/athletes').then(r => {
            if (r.data.length > 0) setAthlete(r.data[0]);
        }).catch(() => { });
        api.get('/api/sessions?limit=5').then(r => {
            setRecentSessions(r.data);
            const snoozeUntil = localStorage.getItem('unnati_reminder_snooze_until');
            const snoozed = snoozeUntil ? new Date(snoozeUntil) > new Date() : false;
            const lastSession = r.data[0]?.start_time ? new Date(r.data[0].start_time) : null;
            const inactiveDays = lastSession ? (Date.now() - lastSession.getTime()) / (1000 * 60 * 60 * 24) : 999;
            setShowReminder(!snoozed && inactiveDays >= 3);
        }).catch(() => { });
    }, []);

    const snoozeReminder = () => {
        const until = new Date(Date.now() + 24 * 60 * 60 * 1000);
        localStorage.setItem('unnati_reminder_snooze_until', until.toISOString());
        setShowReminder(false);
    };

    return (
        <div className="page page-with-bottom-nav">
            <div className="container flex-col gap-8">

                {/* Hero greeting */}
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                    <p className="text-muted" style={{ fontSize: '0.85rem' }}>Welcome back 👋</p>
                    <h1 style={{ marginTop: 4 }}>
                        {athlete ? athlete.name : 'Athlete'}
                    </h1>
                </motion.div>

                {showReminder && (
                    <motion.div className="alert alert-warning flex items-center justify-between" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                        <span>⏰ It has been a while since your last test. Take a quick assessment today.</span>
                        <button className="btn btn-secondary btn-sm" onClick={snoozeReminder} type="button">Remind Tomorrow</button>
                    </motion.div>
                )}

                {/* Rank Card */}
                <motion.div className="rank-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
                    <div className="flex items-center gap-4">
                        <div>
                            <div className="rank-icon">{RANK_ICONS[athlete?.rank_level] || '🥉'}</div>
                            <div className={`rank-label rank-${athlete?.rank_level || 'Bronze'}`}>
                                {athlete?.rank_level || 'Bronze'}
                            </div>
                        </div>
                        <div style={{ flex: 1 }}>
                            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                {athlete?.total_points || 0} total points
                            </p>
                            <div className="rank-progress" style={{ marginTop: 8 }}>
                                <div className="progress-track">
                                    <div className="progress-fill" style={{ width: `${Math.min(100, ((athlete?.total_points || 0) % 100))}%` }} />
                                </div>
                            </div>
                            <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4 }}>
                                {athlete?.tests_completed || 0} tests completed
                            </p>
                        </div>
                    </div>
                </motion.div>

                {/* Quick Actions */}
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
                    <h3 style={{ marginBottom: 12 }}>Quick Actions</h3>
                    <div className="grid-4">
                        {QUICK_ACTIONS.map(a => (
                            <Link key={a.path} to={a.path} className="card quick-action">
                                <span className="quick-action-icon">{a.icon}</span>
                                <span className="quick-action-label">{a.label}</span>
                            </Link>
                        ))}
                    </div>
                </motion.div>

                {/* Available Tests */}
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                    <h3 style={{ marginBottom: 12 }}>Available Tests</h3>
                    <div className="flex-col gap-3">
                        {TESTS.map((t, i) => (
                            <motion.div
                                key={t.id}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: 0.3 + i * 0.08 }}
                            >
                                <Link to={`/test?type=${t.id}`} style={{ textDecoration: 'none' }}>
                                    <div className="card flex items-center gap-4" style={{ padding: 16 }}>
                                        <div style={{
                                            fontSize: '1.8rem',
                                            width: 48, height: 48,
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            borderRadius: 12,
                                            background: `${t.color}15`,
                                        }}>
                                            {t.icon}
                                        </div>
                                        <div style={{ flex: 1 }}>
                                            <h4 style={{ color: 'var(--text-primary)' }}>{t.name}</h4>
                                            <p style={{ fontSize: '0.8rem', margin: 0 }}>{t.desc}</p>
                                        </div>
                                        <span className="badge badge-info">{t.id}</span>
                                    </div>
                                </Link>
                            </motion.div>
                        ))}
                    </div>
                </motion.div>

                {/* Recent Results */}
                {recentSessions.length > 0 && (
                    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
                        <h3 style={{ marginBottom: 12 }}>Recent Results</h3>
                        <div className="flex-col gap-3">
                            {recentSessions.map(s => (
                                <div key={s.session_id} className="card flex items-center gap-4" style={{ padding: 14 }}>
                                    {s.grade && (
                                        <div className={`grade-badge grade-${s.grade}`}>{s.grade}</div>
                                    )}
                                    <div style={{ flex: 1 }}>
                                        <h4>{TESTS.find(t => t.id === s.test_type)?.name || s.test_type}</h4>
                                        <p style={{ fontSize: '0.8rem', margin: 0 }}>
                                            {s.primary_metric != null ? `${s.primary_metric.toFixed(1)}` : '—'}
                                            {' · '}
                                            {new Date(s.start_time).toLocaleDateString()}
                                        </p>
                                    </div>
                                    <span className={`badge ${s.valid ? 'badge-success' : 'badge-danger'}`}>
                                        {s.valid ? 'Valid' : 'Invalid'}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </motion.div>
                )}
            </div>
        </div>
    );
}
