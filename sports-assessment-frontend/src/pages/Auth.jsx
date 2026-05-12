import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useLocation, useNavigate } from 'react-router-dom';
import { confirmPasswordReset, loginUser, registerUser, requestPasswordReset } from '../services/api';
import { getAuthToken, setAuthSession } from '../services/auth';

export default function Auth() {
    const navigate = useNavigate();
    const location = useLocation();
    const fromPath = location.state?.from?.pathname || '/';

    const [mode, setMode] = useState('login');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const [loginForm, setLoginForm] = useState({ identifier: '', password: '' });
    const [registerForm, setRegisterForm] = useState({
        full_name: '',
        email: '',
        mobile: '',
        password: '',
        confirmPassword: '',
    });
    const [resetRequest, setResetRequest] = useState({ identifier: '', resetCode: '' });
    const [resetConfirm, setResetConfirm] = useState({ identifier: '', code: '', newPassword: '', confirmPassword: '' });

    useEffect(() => {
        if (getAuthToken()) {
            navigate('/', { replace: true });
        }
    }, [navigate]);

    const onLogin = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        if (!loginForm.identifier.trim() || !loginForm.password) {
            setError('Please enter your email/mobile and password.');
            return;
        }

        try {
            setLoading(true);
            const res = await loginUser({
                identifier: loginForm.identifier.trim(),
                password: loginForm.password,
            });
            setAuthSession(res.data.token, res.data.user);
            navigate(fromPath, { replace: true });
        } catch (err) {
            setError(err.message || 'Login failed.');
        } finally {
            setLoading(false);
        }
    };

    const onRegister = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        if (!registerForm.full_name.trim()) {
            setError('Full name is required.');
            return;
        }
        if (registerForm.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(registerForm.email.trim())) {
            setError('Enter a valid email address.');
            return;
        }
        if (registerForm.mobile.trim() && !/^\+?[0-9]{8,15}$/.test(registerForm.mobile.trim())) {
            setError('Enter a valid mobile number (8-15 digits).');
            return;
        }
        if (!registerForm.email.trim() && !registerForm.mobile.trim()) {
            setError('Provide at least one identifier: email or mobile.');
            return;
        }
        if (registerForm.password.length < 8) {
            setError('Password must be at least 8 characters.');
            return;
        }
        if (registerForm.password !== registerForm.confirmPassword) {
            setError('Passwords do not match.');
            return;
        }

        try {
            setLoading(true);
            const res = await registerUser({
                full_name: registerForm.full_name.trim(),
                email: registerForm.email.trim() || null,
                mobile: registerForm.mobile.trim() || null,
                password: registerForm.password,
            });
            setAuthSession(res.data.token, res.data.user);
            navigate(fromPath, { replace: true });
        } catch (err) {
            setError(err.message || 'Registration failed.');
        } finally {
            setLoading(false);
        }
    };

    const onRequestReset = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        if (!resetRequest.identifier.trim()) {
            setError('Enter your email or mobile.');
            return;
        }
        try {
            setLoading(true);
            const res = await requestPasswordReset({ identifier: resetRequest.identifier.trim() });
            const code = res.data.dev_reset_code ? ` (Demo code: ${res.data.dev_reset_code})` : '';
            setSuccess(`Reset code generated.${code}`);
            setResetConfirm((p) => ({ ...p, identifier: resetRequest.identifier.trim() }));
        } catch (err) {
            setError(err.message || 'Failed to request reset code.');
        } finally {
            setLoading(false);
        }
    };

    const onConfirmReset = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        if (!resetConfirm.identifier.trim() || !resetConfirm.code.trim()) {
            setError('Identifier and reset code are required.');
            return;
        }
        if (resetConfirm.newPassword.length < 8) {
            setError('New password must be at least 8 characters.');
            return;
        }
        if (resetConfirm.newPassword !== resetConfirm.confirmPassword) {
            setError('Passwords do not match.');
            return;
        }
        try {
            setLoading(true);
            await confirmPasswordReset({
                identifier: resetConfirm.identifier.trim(),
                code: resetConfirm.code.trim(),
                new_password: resetConfirm.newPassword,
            });
            setSuccess('Password reset successful. You can log in now.');
            setMode('login');
        } catch (err) {
            setError(err.message || 'Failed to reset password.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="page auth-shell">
            <div className="container" style={{ maxWidth: 520 }}>
                <motion.div className="card auth-card" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}>
                    <div style={{ textAlign: 'center', marginBottom: 20 }}>
                        <h2 style={{ marginBottom: 6 }}>⚡ Unnati</h2>
                        <p style={{ fontSize: '0.9rem' }}>Sign in to continue your assessment journey</p>
                    </div>

                    <div className="auth-segment" role="tablist" aria-label="Authentication mode">
                        <button
                            className={`auth-segment-btn ${mode === 'login' ? 'active' : ''}`}
                            onClick={() => { setMode('login'); setError(''); setSuccess(''); }}
                            type="button"
                        >
                            Login
                        </button>
                        <button
                            className={`auth-segment-btn ${mode === 'register' ? 'active' : ''}`}
                            onClick={() => { setMode('register'); setError(''); setSuccess(''); }}
                            type="button"
                        >
                            Register
                        </button>
                        <button
                            className={`auth-segment-btn ${mode === 'reset' ? 'active' : ''}`}
                            onClick={() => { setMode('reset'); setError(''); setSuccess(''); }}
                            type="button"
                        >
                            Reset Password
                        </button>
                    </div>

                    {mode === 'login' ? (
                        <form className="auth-form" onSubmit={onLogin}>
                            <input
                                className="input"
                                placeholder="Email or Mobile"
                                value={loginForm.identifier}
                                onChange={(e) => setLoginForm({ ...loginForm, identifier: e.target.value })}
                                autoComplete="username"
                            />
                            <input
                                className="input"
                                type="password"
                                placeholder="Password"
                                value={loginForm.password}
                                onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                                autoComplete="current-password"
                            />
                            {error && <div className="alert alert-danger">{error}</div>}
                            {success && <div className="alert alert-success">{success}</div>}
                            <button className="btn btn-primary btn-lg" style={{ width: '100%', justifyContent: 'center' }} disabled={loading}>
                                {loading ? 'Signing in...' : 'Sign In'}
                            </button>
                        </form>
                    ) : mode === 'register' ? (
                        <form className="auth-form" onSubmit={onRegister}>
                            <input
                                className="input"
                                placeholder="Full Name"
                                value={registerForm.full_name}
                                onChange={(e) => setRegisterForm({ ...registerForm, full_name: e.target.value })}
                                autoComplete="name"
                            />
                            <input
                                className="input"
                                placeholder="Email (optional if mobile provided)"
                                value={registerForm.email}
                                onChange={(e) => setRegisterForm({ ...registerForm, email: e.target.value })}
                                autoComplete="email"
                            />
                            <input
                                className="input"
                                placeholder="Mobile (optional if email provided)"
                                value={registerForm.mobile}
                                onChange={(e) => setRegisterForm({ ...registerForm, mobile: e.target.value })}
                                autoComplete="tel"
                            />
                            <input
                                className="input"
                                type="password"
                                placeholder="Password (min 8 chars)"
                                value={registerForm.password}
                                onChange={(e) => setRegisterForm({ ...registerForm, password: e.target.value })}
                                autoComplete="new-password"
                            />
                            <input
                                className="input"
                                type="password"
                                placeholder="Confirm Password"
                                value={registerForm.confirmPassword}
                                onChange={(e) => setRegisterForm({ ...registerForm, confirmPassword: e.target.value })}
                                autoComplete="new-password"
                            />
                            {error && <div className="alert alert-danger">{error}</div>}
                            {success && <div className="alert alert-success">{success}</div>}
                            <button className="btn btn-primary btn-lg" style={{ width: '100%', justifyContent: 'center' }} disabled={loading}>
                                {loading ? 'Creating account...' : 'Create Account'}
                            </button>
                        </form>
                    ) : (
                        <div className="auth-form">
                            <form className="auth-form" onSubmit={onRequestReset}>
                                <input
                                    className="input"
                                    placeholder="Email or Mobile"
                                    value={resetRequest.identifier}
                                    onChange={(e) => setResetRequest({ ...resetRequest, identifier: e.target.value })}
                                />
                                <button className="btn btn-secondary" type="submit" disabled={loading}>
                                    {loading ? 'Requesting...' : 'Request Reset Code'}
                                </button>
                            </form>
                            <form className="auth-form" onSubmit={onConfirmReset}>
                                <input
                                    className="input"
                                    placeholder="Email or Mobile"
                                    value={resetConfirm.identifier}
                                    onChange={(e) => setResetConfirm({ ...resetConfirm, identifier: e.target.value })}
                                />
                                <input
                                    className="input"
                                    placeholder="Reset Code"
                                    value={resetConfirm.code}
                                    onChange={(e) => setResetConfirm({ ...resetConfirm, code: e.target.value })}
                                />
                                <input
                                    className="input"
                                    type="password"
                                    placeholder="New Password"
                                    value={resetConfirm.newPassword}
                                    onChange={(e) => setResetConfirm({ ...resetConfirm, newPassword: e.target.value })}
                                />
                                <input
                                    className="input"
                                    type="password"
                                    placeholder="Confirm New Password"
                                    value={resetConfirm.confirmPassword}
                                    onChange={(e) => setResetConfirm({ ...resetConfirm, confirmPassword: e.target.value })}
                                />
                                {error && <div className="alert alert-danger">{error}</div>}
                                {success && <div className="alert alert-success">{success}</div>}
                                <button className="btn btn-primary btn-lg" style={{ width: '100%', justifyContent: 'center' }} disabled={loading}>
                                    {loading ? 'Resetting...' : 'Reset Password'}
                                </button>
                            </form>
                        </div>
                    )}
                </motion.div>
            </div>
        </div>
    );
}
