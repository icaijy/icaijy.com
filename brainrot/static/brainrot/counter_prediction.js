const GAME_SECONDS = 20;
const RECENT_WINDOW_SECONDS = 4;

const tr = (message) => typeof gettext === 'function' ? gettext(message) : message;

function ensureProjectionUi() {
  const scoreCard = document.querySelector('.score-card');
  const timer = document.getElementById('counter-time');
  if (!scoreCard || !timer || document.getElementById('counter-projection')) return null;

  const row = document.createElement('div');
  row.className = 'd-flex justify-content-between align-items-end border-top pt-3 mb-3';
  row.innerHTML = `
    <span class="text-secondary small text-uppercase fw-semibold">${tr('projected 20s score')}</span>
    <strong class="timer-value" id="counter-projection">—</strong>
  `;
  timer.closest('.d-flex')?.insertAdjacentElement('afterend', row);

  const note = document.createElement('p');
  note.className = 'small text-secondary mt-n2 mb-3';
  note.textContent = tr('Live estimate from your overall pace and the last few seconds. It becomes more stable as the run continues.');
  row.insertAdjacentElement('afterend', note);
  return row.querySelector('#counter-projection');
}

function initialisePrediction() {
  const app = document.getElementById('counter-app');
  const scoreNode = document.getElementById('score');
  const timeNode = document.getElementById('counter-time');
  const projectionNode = ensureProjectionUi();
  if (!app || !scoreNode || !timeNode || !projectionNode) return;

  let samples = [];
  let lastElapsed = 0;
  let lastSampleAt = 0;

  const reset = () => {
    samples = [];
    lastElapsed = 0;
    lastSampleAt = 0;
    projectionNode.textContent = '—';
  };

  function tick(timestamp) {
    const remaining = Number(timeNode.textContent || GAME_SECONDS);
    const score = Number(scoreNode.textContent || 0);
    const elapsed = Math.max(0, Math.min(GAME_SECONDS, GAME_SECONDS - remaining));

    if (elapsed + 0.25 < lastElapsed || remaining >= GAME_SECONDS - 0.01) reset();
    lastElapsed = elapsed;

    if (elapsed > 0 && elapsed < GAME_SECONDS && timestamp - lastSampleAt >= 200) {
      samples.push({ elapsed, score });
      lastSampleAt = timestamp;
      const cutoff = elapsed - RECENT_WINDOW_SECONDS - 0.5;
      samples = samples.filter((sample) => sample.elapsed >= cutoff);
    }

    if (elapsed < 1.5 || score < 1 || remaining <= 0 || remaining >= GAME_SECONDS) {
      projectionNode.textContent = remaining <= 0 ? String(score) : '—';
      requestAnimationFrame(tick);
      return;
    }

    const overallRate = score / elapsed;
    let recentRate = overallRate;
    const oldest = samples.find((sample) => sample.elapsed >= Math.max(0, elapsed - RECENT_WINDOW_SECONDS));
    if (oldest && elapsed - oldest.elapsed >= 1) {
      recentRate = Math.max(0, (score - oldest.score) / (elapsed - oldest.elapsed));
    }

    // Early on, trust the full-run average because a 4-second window is noisy.
    // Later, recent pace gets enough weight to reflect a genuine surge/fade.
    const recentWeight = Math.min(0.45, Math.max(0, (elapsed - 4) / 20));
    const projectedRate = overallRate * (1 - recentWeight) + recentRate * recentWeight;
    const projected = Math.max(score, Math.round(score + projectedRate * (GAME_SECONDS - elapsed)));
    projectionNode.textContent = String(projected);

    requestAnimationFrame(tick);
  }

  document.getElementById('reset-run')?.addEventListener('click', reset);
  requestAnimationFrame(tick);
}

if (typeof document !== 'undefined') initialisePrediction();
