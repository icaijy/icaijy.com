export const GAME_MODES = Object.freeze({
  SIX_SEVEN: 'six_seven',
  LEG_CLAPS: 'leg_claps',
});

const LANDMARK_SETS = Object.freeze({
  [GAME_MODES.SIX_SEVEN]: [11, 12, 15, 16],
  [GAME_MODES.LEG_CLAPS]: [23, 24, 25, 26, 27, 28],
});

export const OVERLAY_GEOMETRY = Object.freeze({
  [GAME_MODES.SIX_SEVEN]: {
    points: [11, 12, 13, 14, 15, 16],
    links: [[11, 13], [13, 15], [12, 14], [14, 16], [11, 12], [15, 16]],
  },
  [GAME_MODES.LEG_CLAPS]: {
    points: [23, 24, 25, 26, 27, 28],
    links: [[23, 24], [23, 25], [25, 27], [24, 26], [26, 28], [25, 26], [27, 28]],
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

function midpoint(a, b) {
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
}

function distance(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

class LegClapTracker {
  constructor() {
    this.reset();
  }

  reset() {
    this.openFrames = 0;
    this.closedFrames = 0;
    this.readyForClose = false;
    this.openBaseline = null;
    this.lastCountAt = 0;
  }

  metrics(landmarks) {
    const leftHip = landmarks[23];
    const rightHip = landmarks[24];
    const leftKnee = landmarks[25];
    const rightKnee = landmarks[26];
    const leftAnkle = landmarks[27];
    const rightAnkle = landmarks[28];
    const ankleGap = Math.abs(leftAnkle.x - rightAnkle.x);
    const hipGap = Math.abs(leftHip.x - rightHip.x);
    const scale = Math.max(ankleGap, hipGap, 0.08);
    return {
      kneeRatio: Math.abs(leftKnee.x - rightKnee.x) / scale,
      scale,
      leftAnkle,
      rightAnkle,
      hipCentre: midpoint(leftHip, rightHip),
    };
  }

  stableSinceOpen(metrics) {
    if (!this.openBaseline) return false;
    const ankleTolerance = metrics.scale * 0.28;
    const hipTolerance = metrics.scale * 0.30;
    return distance(metrics.leftAnkle, this.openBaseline.leftAnkle) <= ankleTolerance
      && distance(metrics.rightAnkle, this.openBaseline.rightAnkle) <= ankleTolerance
      && distance(metrics.hipCentre, this.openBaseline.hipCentre) <= hipTolerance;
  }

  observe(landmarks, now) {
    if (!landmarksAreVisible(GAME_MODES.LEG_CLAPS, landmarks)) {
      this.openFrames = Math.max(0, this.openFrames - 1);
      this.closedFrames = 0;
      return false;
    }

    const metrics = this.metrics(landmarks);
    if (metrics.kneeRatio >= 0.72) {
      this.openFrames += 1;
      this.closedFrames = 0;
      if (this.openFrames >= 3) {
        this.readyForClose = true;
        this.openBaseline = {
          leftAnkle: { ...metrics.leftAnkle },
          rightAnkle: { ...metrics.rightAnkle },
          hipCentre: { ...metrics.hipCentre },
        };
      }
      return false;
    }

    this.openFrames = 0;
    if (metrics.kneeRatio > 0.45) {
      this.closedFrames = 0;
      return false;
    }
    if (!this.readyForClose) return false;

    this.closedFrames += 1;
    if (this.closedFrames < 2) return false;
    if (!this.stableSinceOpen(metrics)) {
      this.readyForClose = false;
      this.closedFrames = 0;
      return false;
    }
    if (now - this.lastCountAt <= 120) return false;

    this.readyForClose = false;
    this.closedFrames = 0;
    this.lastCountAt = now;
    return true;
  }
}

export function createGestureTracker(mode) {
  if (mode === GAME_MODES.LEG_CLAPS) return new LegClapTracker();
  return new SixSevenTracker();
}
