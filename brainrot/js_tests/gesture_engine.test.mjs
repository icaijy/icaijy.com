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

test('a leg clap counts close once and requires a clear reopen before re-arming', () => {
  const tracker = createGestureTracker(GAME_MODES.LEG_CLAPS);

  // hip width is .20, so .14 knee gap = .70 (open) and .07 = .35 (closed).
  assert.equal(tracker.observe(legPose(0.14), 100), false);
  assert.equal(tracker.observe(legPose(0.14), 133), false);
  assert.equal(tracker.observe(legPose(0.07), 200), false);
  assert.equal(tracker.observe(legPose(0.07), 233), true);

  // Staying closed cannot farm counts.
  assert.equal(tracker.observe(legPose(0.06), 266), false);
  assert.equal(tracker.observe(legPose(0.07), 299), false);

  // A partial opening inside the hysteresis band is not enough.
  assert.equal(tracker.observe(legPose(0.11), 332), false);
  assert.equal(tracker.observe(legPose(0.07), 365), false);

  // Reopen for two frames, then another close can count.
  assert.equal(tracker.observe(legPose(0.14), 400), false);
  assert.equal(tracker.observe(legPose(0.14), 433), false);
  assert.equal(tracker.observe(legPose(0.07), 466), false);
  assert.equal(tracker.observe(legPose(0.07), 499), true);
});

test('starting closed never counts until an open pose has armed the tracker', () => {
  const tracker = createGestureTracker(GAME_MODES.LEG_CLAPS);
  assert.equal(tracker.observe(legPose(0.06), 100), false);
  assert.equal(tracker.observe(legPose(0.06), 133), false);
  assert.equal(tracker.observe(legPose(0.14), 166), false);
  assert.equal(tracker.observe(legPose(0.14), 199), false);
  assert.equal(tracker.observe(legPose(0.07), 232), false);
  assert.equal(tracker.observe(legPose(0.07), 265), true);
});

test('leg-clap readiness only requires hips and knees, not feet', () => {
  const pose = legPose(0.14, { ankleVisible: false });
  assert.equal(landmarksAreVisible(GAME_MODES.LEG_CLAPS, pose), true);
  pose[25].visibility = 0.1;
  assert.equal(landmarksAreVisible(GAME_MODES.LEG_CLAPS, pose), false);
});

test('losing knee tracking disarms the current leg-clap cycle', () => {
  const tracker = createGestureTracker(GAME_MODES.LEG_CLAPS);
  assert.equal(tracker.observe(legPose(0.14), 100), false);
  assert.equal(tracker.observe(legPose(0.14), 133), false);
  const lost = legPose(0.07);
  lost[25].visibility = 0.1;
  assert.equal(tracker.observe(lost, 166), false);
  assert.equal(tracker.observe(legPose(0.07), 199), false);
  assert.equal(tracker.observe(legPose(0.07), 232), false);
});
