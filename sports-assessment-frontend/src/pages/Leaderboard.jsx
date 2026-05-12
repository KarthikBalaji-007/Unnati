import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import api from '../services/api';

const MEDAL_ICONS = ['🥇', '🥈', '🥉'];

export default function Leaderboard() {
    const [entries, setEntries] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        api.get('/api/leaderboard?limit=20')
            .then(r => { setEntries(r.data); setLoading(false); })
            .catch(() => setLoading(false));
    }, []);

    const top3 = entries.slice(0, 3);
    const rest = entries.slice(3);

    return (
        <div className="page page-with-bottom-nav">
            <div className="container flex-col gap-6">
                <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
                    <h2>🏆 Leaderboard</h2>
                    <p>Top athletes ranked by total points</p>
                </motion.div>

                {loading ? (
                    <p>Loading...</p>
                ) : entries.length === 0 ? (
                    <div className="card" style={{ padding: 40, textAlign: 'center' }}>
                        <p style={{ fontSize: '2rem' }}>🏅</p>
                        <p>No athletes registered yet. Be the first!</p>
                    </div>
                ) : (
                    <>
                        {/* Podium – Top 3 */}
                        <motion.div className="podium" initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
                            {[1, 0, 2].map(idx => {
                                const e = top3[idx];
                                if (!e) return null;
                                return (
                                    <div key={e.athlete_id} className={`podium-item podium-${idx + 1}`}>
                                        <div className="podium-rank">{MEDAL_ICONS[idx]}</div>
                                        <div className="podium-name">{e.name}</div>
                                        <div className="podium-points">{e.total_points} pts</div>
                                        <span className="badge badge-info" style={{ marginTop: 4, fontSize: '0.65rem' }}>
                                            {e.rank_level}
                                        </span>
                                    </div>
                                );
                            })}
                        </motion.div>

                        {/* Rest of leaderboard */}
                        {rest.length > 0 && (
                            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                                <div className="table-wrapper">
                                    <table>
                                        <thead>
                                            <tr>
                                                <th>#</th>
                                                <th>Athlete</th>
                                                <th>Points</th>
                                                <th>Rank</th>
                                                <th>Tests</th>
                                                <th>Badges</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {rest.map((e, i) => (
                                                <tr key={e.athlete_id}>
                                                    <td style={{ fontWeight: 700 }}>{i + 4}</td>
                                                    <td>{e.name}</td>
                                                    <td className="text-green" style={{ fontWeight: 700 }}>{e.total_points}</td>
                                                    <td><span className="badge badge-info">{e.rank_level}</span></td>
                                                    <td>{e.tests_completed}</td>
                                                    <td>{e.badges_count}</td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </motion.div>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
