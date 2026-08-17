export const GAME_MODES = Object.freeze({
  SIX_SEVEN: 'six_seven',
  LEG_CLAPS: 'leg_claps',
});

const LANDMARK_SETS = Object.freeze({
  [GAME_MODES.SIX_SEVEN]: [11, 12, 15, 16],
  // Leg claps are defined by the knees. Ankles are deliberately not required:
  // MediaPipe often loses feet near the bottom of a phone frame, and foot motion
  // should not decide whether an inward knee clap happened.
  [GAME_MODES.LEG_CLAPS]: [23, 24, 25, 26],
});

export const OVERLAY_GEOMETRY = Object.freeze({
  [GAME_MODES.SIX_SEVEN]: {
    points: [11, 12, 13, 14, 15, 16],
    links: [[11, 13], [13, 15], [12, 14], [14, 16], [11, 12], [15, 16]],
  },
  [GAME_MODES.LEG_CLAPS]: {
    points: [23, 24, 25, 26],
    links: [[23, 24], [23, 25], [24, 26], [25, 26]],
  },
});

function landmarkIsUsable(point) {
  return point
    && (point.visibility ?? 1) > 0.45
    && point.x > 0.02 && point.x < 0.98
    && point.y > 0.02 && point.y < 0.98;
}

export function landmarksAreVisible(mode, landmarks) {
  return Boolean(landmarks)
    && LANDMARK_SETS[mode].every((id) => landmarkIsUsable(landmarks[id]));
}

class SixSevenTracker {
  constructor() {
    this.reset();
  }

  reset() {
    this.lastZone = 0;
    this.lastCountAt = 0;
  }

  observe(landmarks, now) {
    if (!landmarksAreVisible(GAME_MODES.SIX_SEVEN, landmarks)) return false;
    const leftWrist = landmarks[15];
    const rightWrist = landmarks[16];
    const leftShoulder = landmarks[11];
    const rightShoulder = landmarks[12];
    const shoulderWidth = Math.max(
      Math.hypot(leftShoulder.x - rightShoulder.x, leftShoulder.y - rightShoulder.y),
      0.1,
    );
    const normalisedDifference = (leftWrist.y - rightWrist.y) / shoulderWidth;
    const zone = normalisedDifference > 0.20 ? 1 : normalisedDifference < -0.20 ? -1 : 0;
    if (zone === 0) return false;
    if (this.lastZone === 0) {
      this.lastZone = zone;
      return false;
    }
    if (zone !== this.lastZone && now - this.lastCountAt > 90) {
      this.lastZone = zone;
      this.lastCountAt = now;
      return true;
    }
    return false;
  }
}

// For this dance, the knees are roughly one hip-width apart at the inward
// point. Opening the knees makes that horizontal gap clearly wider than the
// hips. The gap between these thresholds is deliberate hysteresis so one pose
// cannot repeatedly count from small landmark jitter.
const LEG_CLAP_CLOSE_RATIO = 1.20;
const LEG_CLAP_REOPEN_RATIO = 1.35;

class LegClapTracker {
  constructor() {
    this.reset();
  }

  reset() {
    this.armed = false;
  }

  kneeRatio(landmarks) {
    const leftHip = landmarks[23];
    const rightHip = landmarks[24];
    const leftKnee = landmarks[25];
    const rightKnee = landmarks[26];
    const hipWidth = Math.max(Math.abs(leftHip.x - rightHip.x), 0.06);
    return Math.abs(leftKnee.x - rightKnee.x) / hipWidth;
  }

  observe(landmarks) {
    if (!landmarksAreVisible(GAME_MODES.LEG_CLAPS, landmarks)) {
      // Require a fresh visible open pose after tracking is lost. This avoids
      // counting a person merely re-entering the frame at the inward point.
      this.armed = false;
      return false;
    }

    const ratio = this.kneeRatio(landmarks);

    if (ratio >= LEG_CLAP_REOPEN_RATIO) {
      this.armed = true;
      return false;
    }

    if (ratio > LEG_CLAP_CLOSE_RATIO || !this.armed) return false;

    this.armed = false;
    return true;
  }
}

export function createGestureTracker(mode) {
  if (mode === GAME_MODES.LEG_CLAPS) return new LegClapTracker();
  return new SixSevenTracker();
}
