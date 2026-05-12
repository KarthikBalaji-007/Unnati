import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { getAuthSessions, revokeAllAuthSessions, revokeAuthSession } from '../services/api';

export default function Sessions() {
    const [sessions, setSessions] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    const loadSessions = async () => {
        try {
            setLoading(true);
            const res = await getAuthSessions();
            setSessions(res.data);
            setError('');
        } catch (err) {
            setError(err.message || 'Failed to load sessions.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadSessions();
    }, []);

    const revokeOne = async (sessionId) => {
        try {
            await revokeAuthSession(sessionId);
            setSessions((prev) => prev.filter((s) => s.session_id !== sessionId));
        } catch (err) {
            setError(err.message || 'Failed to revoke session.');
        }
    };

    const revokeOthers = async () => {
        try {
            await revokeAllAuthSessions(true);
            await loadSessions();
        } catch (err) {
            setError(err.message || 'Failed to revoke sessions.');
        }
    };

    return (
        <div className="page page-with-bottom-nav">
            <div className="container flex-col gap-6">
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                    <h2>🔐 Active Sessions</h2>
                    <p>Manage where your account is currently signed in.</p>
                </motion.div>

                {error && <div className="alert alert-danger">{error}</div>}

                <div className="card" style={{ padding: 16 }}>
                    <button className="btn btn-secondary btn-sm" onClick={revokeOthers} type="button">
                        Revoke Other Sessions
                    </button>
                </div>

                {loading ? (
                    <p>Loading sessions...</p>
                ) : (
                    <div className="flex-col gap-3">
                        {sessions.map((s) => (
                            <div key={s.session_id} className="card" style={{ padding: 16 }}>
                                <div className="flex items-center justify-between gap-4">
                                    <div style={{ flex: 1 }}>
                                        <h4 style={{ marginBottom: 4 }}>
                                            {s.current ? 'Current Session' : 'Signed-in Session'}
                                        </h4>
                                        <p style={{ fontSize: '0.8rem', margin: 0 }}>
                                            Created: {new Date(s.created_at).toLocaleString()} · Last used: {new Date(s.last_used_at).toLocaleString()}
                                        </p>
                                        <p style={{ fontSize: '0.75rem', margin: '4px 0 0', color: 'var(--text-muted)' }}>
                                            Expires: {new Date(s.expires_at).toLocaleString()}
                                        </p>
                                    </div>
                                    {!s.current && (
                                        <button className="btn btn-danger btn-sm" onClick={() => revokeOne(s.session_id)} type="button">
                                            Revoke
                                        </button>
                                    )}
                                    {s.current && <span className="badge badge-success">Current</span>}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
}
