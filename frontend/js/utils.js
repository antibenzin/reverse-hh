function $(selector, root = document) {
  return root.querySelector(selector);
}

function showError(el, message) {
  if (!el) return;
  el.textContent = message;
  el.classList.remove('hidden');
}

function hideError(el) {
  if (!el) return;
  el.classList.add('hidden');
  el.textContent = '';
}

function formatDate(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('ru-RU');
}
