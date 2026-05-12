import { useEffect, useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { logoutUser } from '../services/api';
import { clearAuthSession, getAuthUser } from '../services/auth';

const NAV_ITEMS = [
    { path: '/', icon: '🏠', label: 'Home' },
    { path: '/test', icon: '🎯', label: 'Tests' },
    { path: '/leaderboard', icon: '🏆', label: 'Ranks' },
    { path: '/history', icon: '📊', label: 'History' },
    { path: '/profile', icon: '👤', label: 'Profile' },
];

export default function Navbar() {
    const location = useLocation();
    const navigate = useNavigate();
    const [authUser, setAuthUser] = useState(() => getAuthUser());

    useEffect(() => {
        const syncAuth = () => setAuthUser(getAuthUser());
        window.addEventListener('auth-changed', syncAuth);
        window.addEventListener('storage', syncAuth);
        return () => {
            window.removeEventListener('auth-changed', syncAuth);
            window.removeEventListener('storage', syncAuth);
        };
    }, []);

    const onLogout = async () => {
        try {
            await logoutUser();
        } catch (err) {
            console.warn('Logout request failed, clearing local session.', err);
        } finally {
            clearAuthSession();
            navigate('/auth', { replace: true });
        }
    };

    return (
        <>
            {/* Top bar — logo only */}
            <nav className="navbar">
                <NavLink to="/" className="navbar-logo">
                    <span>⚡</span>
                    <span>Unnati</span>
                </NavLink>
                <div className="navbar-links">
                    {authUser?.full_name && (
                        <span className="badge badge-info" style={{ marginRight: 6 }}>
                            {authUser.full_name}
                        </span>
                    )}
                    <NavLink to="/benchmarks" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        📋 Standards
                    </NavLink>
                    <NavLink to="/sessions" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        🔐 Sessions
                    </NavLink>
                    <NavLink to="/coach" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                        🧭 Coach
                    </NavLink>
                    <button className="btn btn-secondary btn-sm" onClick={onLogout} type="button">
                        Logout
                    </button>
                </div>
            </nav>

            {/* Bottom tab bar */}
            <div className="bottom-nav">
                {NAV_ITEMS.map(item => (
                    <NavLink
                        key={item.path}
                        to={item.path}
                        className={`bottom-nav-item ${location.pathname === item.path ? 'active' : ''}`}
                    >
                        <span className="bottom-nav-icon">{item.icon}</span>
                        <span className="bottom-nav-label">{item.label}</span>
                    </NavLink>
                ))}
            </div>
        </>
    );
}
