import assert from 'node:assert/strict';
import test from 'node:test';

function projectFinalScore(score, elapsed, recentRate = null) {
  if (elapsed < 1.5 || score < 1) return null;
  const overallRate = score / elapsed;
  const effectiveRecentRate = recentRate ?? overallRate;
  const recentWeight = Math.min(0.45, Math.max(0, (elapsed - 4) / 20));
  const projectedRate = overallRate * (1 - recentWeight) + effectiveRecentRate * recentWeight;
  return Math.max(score, Math.round(score + projectedRate * (20 - elapsed)));
}

test('early projection extrapolates the overall pace', () => {
  assert.equal(projectFinalScore(20, 2), 200);
});

test('late projection reacts to a slowdown without falling below current score', () => {
  const projected = projectFinalScore(120, 15, 4);
  assert.ok(projected >= 120);
  assert.ok(projected < 160);
});
