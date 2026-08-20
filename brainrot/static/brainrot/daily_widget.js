const widget = document.getElementById('daily-mini-widget');
if (widget) {
  const list = widget.querySelector('[data-daily-mini-list]');
  const status = widget.querySelector('[data-daily-mini-status]');
  fetch(widget.dataset.endpoint, { credentials: 'same-origin' })
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then((payload) => {
      status?.remove();
      const entries = payload.entries || [];
      if (!entries.length) {
        list.innerHTML = '<div class="small text-secondary">Nobody has wasted 20 seconds yet today.</div>';
        return;
      }
      list.innerHTML = entries.map((entry) => `
        <div class="daily-mini-row">
          <span class="daily-mini-rank">#${entry.rank}</span>
          <span class="daily-mini-name">${escapeHtml(entry.name)}</span>
          <strong>${entry.score}${entry.private ? '<span class="daily-mini-lock" title="Private run"> 🔒</span>' : ''}</strong>
        </div>
      `).join('');
    })
    .catch(() => {
      if (status) status.textContent = 'Today board unavailable';
    });
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  })[character]);
}
