import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const engineSource = await readFile(new URL('../static/brainrot/gesture_engine.js', import.meta.url), 'utf8');
const { GAME_MODES, createGestureTracker, landmarksAreVisible } = await import(
  `data:text/javascript;base64,${Buffer.from(engineSource).toString('base64')}`
);

function pose({ leftWristY, rightWristY, kneeGap }) {
  const p = Array.from({ length: 33 }, () => ({ x: 0.5, y: 0.5, visibility: 1 }));
  p[11] = { x: 0.35, y: 0.35, visibility: 1 };
  p[12] = { x: 0.65, y: 0.35, visibility: 1 };
  p[15] = { x: 0.35, y: leftWristY, visibility: 1 };
  p[16] = { x: 0.65, y: rightWristY, visibility: 1 };
  p[23] = { x: 0.40, y: 0.46, visibility: 1 };
  p[24] = { x: 0.60, y: 0.46, visibility: 1 };
  p[25] = { x: 0.50 - kneeGap / 2, y: 0.66, visibility: 1 };
  p[26] = { x: 0.50 + kneeGap / 2, y: 0.66, visibility: 1 };
  return p;
}

test('combine readiness requires both the upper-body and knee landmarks', () => {
  const p = pose({ leftWristY: .7, rightWristY: .3, kneeGap: .30 });
  assert.equal(landmarksAreVisible(GAME_MODES.COMBINE, p), true);
  p[25].visibility = .1;
  assert.equal(landmarksAreVisible(GAME_MODES.COMBINE, p), false);
});

test('combine tracker reports arm and leg events independently from one pose stream', () => {
  const tracker = createGestureTracker(GAME_MODES.COMBINE);
  let result = tracker.observe(pose({ leftWristY: .70, rightWristY: .30, kneeGap: .30 }), 100);
  assert.deepEqual(result, { sixSeven: false, legClaps: false });

  result = tracker.observe(pose({ leftWristY: .30, rightWristY: .70, kneeGap: .22 }), 250);
  assert.deepEqual(result, { sixSeven: true, legClaps: true });

  result = tracker.observe(pose({ leftWristY: .70, rightWristY: .30, kneeGap: .30 }), 400);
  assert.equal(result.sixSeven, true);
  assert.equal(result.legClaps, false);

  result = tracker.observe(pose({ leftWristY: .30, rightWristY: .70, kneeGap: .22 }), 550);
  assert.deepEqual(result, { sixSeven: true, legClaps: true });
});
