async function getCurrentUser() {
  return apiJson('/auth/me');
}

async function login(email, password) {
  return apiJson('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

async function register(email, password, display_name) {
  return apiJson('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, display_name }),
  });
}

async function logout() {
  await api('/auth/logout', { method: 'POST' });
  window.location.href = '/pages/login.html';
}

async function requireAuth() {
  const user = await getCurrentUser();
  if (!user) {
    window.location.href = '/pages/login.html';
    return null;
  }
  return user;
}
