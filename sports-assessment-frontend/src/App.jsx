import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import Navbar from './components/Navbar';
import AppNotifier from './components/AppNotifier';
import ProtectedRoute from './components/ProtectedRoute';
import Dashboard from './pages/Dashboard';
import TestRunner from './pages/TestRunner';
import History from './pages/History';
import Profile from './pages/Profile';
import Leaderboard from './pages/Leaderboard';
import Benchmarks from './pages/Benchmarks';
import Auth from './pages/Auth';
import Sessions from './pages/Sessions';
import CoachDashboard from './pages/CoachDashboard';
import { getAuthToken } from './services/auth';
import './styles/index.css';

function AppRoutes() {
    const location = useLocation();
    const hasSession = Boolean(getAuthToken());
    const showNavbar = location.pathname !== '/auth' && hasSession;
    const defaultRoute = hasSession ? '/' : '/auth';

    return (
        <>
            {showNavbar && <Navbar />}
            {hasSession && <AppNotifier />}
            <Routes>
                <Route path="/auth" element={<Auth />} />

                <Route element={<ProtectedRoute />}>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/test" element={<TestRunner />} />
                    <Route path="/history" element={<History />} />
                    <Route path="/profile" element={<Profile />} />
                    <Route path="/leaderboard" element={<Leaderboard />} />
                    <Route path="/benchmarks" element={<Benchmarks />} />
                    <Route path="/sessions" element={<Sessions />} />
                    <Route path="/coach" element={<CoachDashboard />} />
                </Route>

                <Route path="*" element={<Navigate to={defaultRoute} replace />} />
            </Routes>
        </>
    );
}

export default function App() {
    return (
        <BrowserRouter>
            <AppRoutes />
        </BrowserRouter>
    );
}
