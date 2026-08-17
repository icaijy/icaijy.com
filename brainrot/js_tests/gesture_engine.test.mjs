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

function legPose(kneeGap, { ankleShift = 0, hipShift = 0 } = {}) {
  const pose = blankPose();
  pose[23] = { x: 0.40 + hipShift, y: 0.46, visibility: 1 };
  pose[24] = { x: 0.60 + hipShift, y: 0.46, visibility: 1 };
  pose[25] = { x: 0.50 - kneeGap / 2, y: 0.66, visibility: 1 };
  pose[26] = { x: 0.50 + kneeGap / 2, y: 0.66, visibility: 1 };
  pose[27] = { x: 0.30 + ankleShift, y: 0.90, visibility: 1 };
  pose[28] = { x: 0.70 + ankleShift, y: 0.90, visibility: 1 };
  return pose;
}

test('the existing 67 direction-change rule is preserved', () => {
  const tracker = createGestureTracker(GAME_MODES.SIX_SEVEN);
  assert.equal(tracker.observe(sixSevenPose(0.70, 0.30), 100), false);
  assert.equal(tracker.observe(sixSevenPose(0.30, 0.70), 250), true);
  assert.equal(tracker.observe(sixSevenPose(0.70, 0.30), 400), true);
});

test('a leg clap requires open, inward, then open before another count', () => {
  const tracker = createGestureTracker(GAME_MODES.LEG_CLAPS);
  for (const time of [100, 133, 166]) assert.equal(tracker.observe(legPose(0.36), time), false);
  assert.equal(tracker.observe(legPose(0.16), 220), false);
  assert.equal(tracker.observe(legPose(0.12), 253), true);
  assert.equal(tracker.observe(legPose(0.10), 300), false);
  assert.equal(tracker.observe(legPose(0.12), 360), false);

  for (const time of [420, 453, 486]) assert.equal(tracker.observe(legPose(0.36), time), false);
  assert.equal(tracker.observe(legPose(0.14), 540), false);
  assert.equal(tracker.observe(legPose(0.10), 573), true);
});

test('starting closed does not count and unstable feet invalidate the cycle', () => {
  const tracker = createGestureTracker(GAME_MODES.LEG_CLAPS);
  assert.equal(tracker.observe(legPose(0.10), 200), false);
  assert.equal(tracker.observe(legPose(0.10), 240), false);
  for (const time of [300, 333, 366]) assert.equal(tracker.observe(legPose(0.36), time), false);
  assert.equal(tracker.observe(legPose(0.12, { ankleShift: 0.20 }), 420), false);
  assert.equal(tracker.observe(legPose(0.10, { ankleShift: 0.20 }), 453), false);
});

test('leg-clap readiness requires hips, knees and ankles', () => {
  const pose = legPose(0.36);
  pose[25].visibility = 0.1;
  assert.equal(landmarksAreVisible(GAME_MODES.LEG_CLAPS, pose), false);
});
