const API_BASE = '/api/v1';

async function api(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  const response = await fetch(API_BASE + path, {
    ...options,
    headers,
    credentials: 'include',
  });

  if (response.status === 401 && !path.startsWith('/auth/')) {
    window.location.href = '/pages/login.html';
    return null;
  }

  return response;
}

async function apiJson(path, options = {}) {
  const response = await api(path, options);
  if (!response) return null;
  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail || response.statusText;
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail));
  }
  return data;
}
