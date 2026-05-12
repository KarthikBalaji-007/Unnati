const OFFLINE_QUEUE_KEY = 'unnati_offline_queue';

function readQueue() {
  const raw = localStorage.getItem(OFFLINE_QUEUE_KEY);
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeQueue(queue) {
  localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(queue));
  window.dispatchEvent(new Event('offline-queue-changed'));
}

export function getOfflineQueue() {
  return readQueue();
}

export function queueMutation(mutation) {
  const queue = readQueue();
  queue.push({
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    createdAt: new Date().toISOString(),
    ...mutation,
  });
  writeQueue(queue);
}

export async function syncOfflineQueue(executor) {
  const queue = readQueue();
  if (!queue.length) return { synced: 0, failed: 0 };

  let synced = 0;
  const remaining = [];
  for (const item of queue) {
    try {
      // executor should throw on failure
      await executor(item);
      synced += 1;
    } catch {
      remaining.push(item);
    }
  }
  writeQueue(remaining);
  return { synced, failed: remaining.length };
}
