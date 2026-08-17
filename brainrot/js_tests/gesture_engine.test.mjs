import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const engineSource = await readFile(
  new URL('../static/brainrot/gesture_engine.js', import.meta.url),
  'utf8',
);
const {
  GAME_MODES,
  createGestureTracker,
  landmarksAreVisible,
} = await import(`data:text/javascript;base64,${Buffer.from(engineSource).toString('base64')}`);

function blankPose() {
  return Array.from({ length: 33 }, () => ({ x: 0.5, y: 0.5, visibility: 1 }));
}

function sixSevenPose(leftWristY, rightWristY) {
  const pose = blankPose();
  pose[11] = { x: 0.35, y: 0.35, visibility: 1 };
  pose[12] = { x: 0.65, y: 0.35, visibility: 1 };
  pose[15] = { x: 0.35, y: leftWristY, visibility: 1 };
  pose[16] = { x: 0.65, y: rightWristY, visibility: 1 };
  return pose;
}

function legPose(kneeGap, { ankleVisible = true } = {}) {
  const pose = blankPose();
  pose[23] = { x: 0.40, y: 0.46, visibility: 1 };
  pose[24] = { x: 0.60, y: 0.46, visibility: 1 };
  pose[25] = { x: 0.50 - kneeGap / 2, y: 0.66, visibility: 1 };
  pose[26] = { x: 0.50 + kneeGap / 2, y: 0.66, visibility: 1 };
  pose[27] = { x: 0.30, y: 0.90, visibility: ankleVisible ? 1 : 0 };
  pose[28] = { x: 0.70, y: 0.90, visibility: ankleVisible ? 1 : 0 };
  return pose;
}

test('the existing 67 direction-change rule is preserved', () => {
  const tracker = createGestureTracker(GAME_MODES.SIX_SEVEN);
  assert.equal(tracker.observe(sixSevenPose(0.70, 0.30), 100), false);
  assert.equal(tracker.observe(sixSevenPose(0.30, 0.70), 250), true);
  assert.equal(tracker.observe(sixSevenPose(0.70, 0.30), 400), true);
});

test('a leg clap counts when knee gap returns to about hip width', () => {
  const tracker = createGestureTracker(GAME_MODES.LEG_CLAPS);

  // Hip width is .20. An open .30 gap is 1.50x hip width; a .22 inward gap is 1.10x.
  assert.equal(tracker.observe(legPose(0.30), 100), false);
  assert.equal(tracker.observe(legPose(0.22), 133), true);

  // Staying inward cannot farm counts.
  assert.equal(tracker.observe(legPose(0.20), 166), false);
  assert.equal(tracker.observe(legPose(0.23), 199), false);

  // A partial opening inside the hysteresis band is not enough to re-arm.
  assert.equal(tracker.observe(legPose(0.25), 232), false);
  assert.equal(tracker.observe(legPose(0.21), 265), false);

  // A clearly wider knee gap re-arms immediately for the next inward swing.
  assert.equal(tracker.observe(legPose(0.29), 298), false);
  assert.equal(tracker.observe(legPose(0.21), 331), true);
});

test('starting inward never counts until a clearly open pose has armed the tracker', () => {
  const tracker = createGestureTracker(GAME_MODES.LEG_CLAPS);
  assert.equal(tracker.observe(legPose(0.20), 100), false);
  assert.equal(tracker.observe(legPose(0.22), 133), false);
  assert.equal(tracker.observe(legPose(0.30), 166), false);
  assert.equal(tracker.observe(legPose(0.23), 199), true);
});

test('a slightly wider-than-hip knee gap still counts as inward', () => {
  const tracker = createGestureTracker(GAME_MODES.LEG_CLAPS);
  assert.equal(tracker.observe(legPose(0.30), 100), false);
  assert.equal(tracker.observe(legPose(0.24), 133), true);
});

test('leg-clap readiness only requires hips and knees, not feet', () => {
  const pose = legPose(0.30, { ankleVisible: false });
  assert.equal(landmarksAreVisible(GAME_MODES.LEG_CLAPS, pose), true);
  pose[25].visibility = 0.1;
  assert.equal(landmarksAreVisible(GAME_MODES.LEG_CLAPS, pose), false);
});

test('losing knee tracking disarms the current leg-clap cycle', () => {
  const tracker = createGestureTracker(GAME_MODES.LEG_CLAPS);
  assert.equal(tracker.observe(legPose(0.30), 100), false);

  const lost = legPose(0.22);
  lost[25].visibility = 0.1;
  assert.equal(tracker.observe(lost, 133), false);

  // Reappearing inward is not enough; a new open pose is required.
  assert.equal(tracker.observe(legPose(0.22), 166), false);
  assert.equal(tracker.observe(legPose(0.30), 199), false);
  assert.equal(tracker.observe(legPose(0.22), 232), true);
});
