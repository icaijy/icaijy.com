(() => {
  const app = document.getElementById('counter-app');
  const resultCard = document.getElementById('counter-result');
  const shareText = document.getElementById('counter-share-text');
  const scoreEl = document.getElementById('score');
  if (!app || !resultCard || !shareText || !scoreEl) return;

  function translatedModeCopy(mode, field) {
    const prefix = mode === 'leg_claps' ? 'leg-claps' : 'six-seven';
    return document.getElementById(`${prefix}-${field}`)?.textContent.trim() || '';
  }

  function updateShareText() {
    if (resultCard.hidden) return;

    const mode = app.dataset.gameMode === 'leg_claps' ? 'leg_claps' : 'six_seven';
    const title = translatedModeCopy(mode, 'title');
    const resultUnit = translatedModeCopy(mode, 'result-unit');
    const score = Number(scoreEl.textContent || 0);
    const blocks = score > 0
      ? `${'🟩'.repeat(Math.min(score, 67))}${score > 67 ? ` +${score - 67}` : ''}`
      : '⬜';

    const pageUrl = app.dataset.rivalName
      ? new URL(window.location.href)
      : new URL('/67/counter/', window.location.origin);
    pageUrl.searchParams.set('mode', mode);

    const rival = app.dataset.rivalName
      ? ` · 🆚 ${app.dataset.rivalName} ${Number(app.dataset.rivalScore || 0)}`
      : '';

    shareText.value = `${title} — ${score} ${resultUnit}${rival}\n${blocks}\n${pageUrl.href}`;
  }

  new MutationObserver(updateShareText).observe(resultCard, {
    attributes: true,
    attributeFilter: ['hidden'],
  });

  document.getElementById('copy-counter-share')?.addEventListener('pointerdown', updateShareText, { capture: true });
})();
