const AUTH_TOKEN_KEY = 'unnati_auth_token';
const AUTH_USER_KEY = 'unnati_auth_user';

function notifyAuthChanged() {
  window.dispatchEvent(new Event('auth-changed'));
}

export function getAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

export function getAuthUser() {
  const raw = localStorage.getItem(AUTH_USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function setAuthSession(token, user) {
  localStorage.setItem(AUTH_TOKEN_KEY, token);
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(user));
  notifyAuthChanged();
}

export function clearAuthSession() {
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
  notifyAuthChanged();
}
