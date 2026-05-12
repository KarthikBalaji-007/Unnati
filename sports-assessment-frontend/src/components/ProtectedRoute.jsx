import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { getAuthToken } from '../services/auth';

export default function ProtectedRoute() {
    const location = useLocation();
    const token = getAuthToken();

    if (!token) {
        return <Navigate to="/auth" replace state={{ from: location }} />;
    }

    return <Outlet />;
}
