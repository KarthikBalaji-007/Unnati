import { useEffect, useState } from 'react';
import api from '../services/api';
import { getOfflineQueue, syncOfflineQueue } from '../services/offlineQueue';

export default function AppNotifier() {
    const [queueCount, setQueueCount] = useState(getOfflineQueue().length);
    const [message, setMessage] = useState('');

    useEffect(() => {
        const updateCount = () => setQueueCount(getOfflineQueue().length);
        const handleOnline = async () => {
            const result = await syncOfflineQueue((item) =>
                api({
                    method: item.method,
                    url: item.url,
                    data: item.data,
                })
            );
            updateCount();
            if (result.synced > 0) {
                setMessage(`${result.synced} queued item(s) synced.`);
                setTimeout(() => setMessage(''), 3000);
            }
        };

        window.addEventListener('offline-queue-changed', updateCount);
        window.addEventListener('online', handleOnline);
        if (navigator.onLine) {
            handleOnline();
        }
        return () => {
            window.removeEventListener('offline-queue-changed', updateCount);
            window.removeEventListener('online', handleOnline);
        };
    }, []);

    if (!queueCount && !message) return null;

    return (
        <div className="app-notifier">
            {queueCount > 0 && (
                <span className="badge badge-warning">
                    Offline queue: {queueCount}
                </span>
            )}
            {message && (
                <span className="badge badge-success">{message}</span>
            )}
        </div>
    );
}
