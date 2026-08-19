const tr = (message) => typeof gettext === 'function' ? gettext(message) : message;

function csrfToken(bar) {
  const embedded = bar?.dataset.csrfToken || '';
  if (embedded && embedded !== 'NOTPROVIDED') return embedded;
  const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : '';
}

async function toggleReaction(bar, button) {
  if (button.disabled) return;
  const status = bar.querySelector('[data-reaction-status]');
  const emoji = button.dataset.reactionEmoji;
  const form = new FormData();
  form.append('target_type', bar.dataset.targetType);
  form.append('target_id', bar.dataset.targetId);
  form.append('emoji', emoji);

  button.disabled = true;
  if (status) status.textContent = '';
  try {
    const response = await fetch(bar.dataset.reactionUrl, {
      method: 'POST',
      body: form,
      credentials: 'same-origin',
      headers: {
        'X-CSRFToken': csrfToken(bar),
        'X-Requested-With': 'XMLHttpRequest',
      },
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || tr('Could not react.'));

    bar.querySelectorAll('[data-reaction-count]').forEach((countNode) => {
      const key = countNode.dataset.reactionCount;
      countNode.textContent = String(payload.counts?.[key] ?? 0);
    });

    button.classList.toggle('btn-dark', payload.active);
    button.classList.toggle('active', payload.active);
    button.classList.toggle('btn-outline-secondary', !payload.active);
    button.setAttribute('aria-pressed', String(Boolean(payload.active)));
  } catch (error) {
    if (status) status.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

document.querySelectorAll('[data-reaction-bar]').forEach((bar) => {
  bar.querySelectorAll('[data-reaction-emoji]').forEach((button) => {
    button.addEventListener('click', () => toggleReaction(bar, button));
  });
});
