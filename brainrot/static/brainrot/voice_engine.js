export function normaliseVoiceTranscript(value) {
  return String(value ?? '')
    .toLowerCase()
    .replace(/\[unk\]/g, ' [unk] ')
    .replace(/[^\p{L}\[\]]+/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export function countSixSevenPhrases(value) {
  const normalised = normaliseVoiceTranscript(value);
  if (!normalised) return 0;

  const tokens = normalised.split(/\s+/);
  let count = 0;
  for (let index = 0; index < tokens.length; index += 1) {
    if (tokens[index] !== 'six') continue;

    if (tokens[index + 1] === 'seven') {
      count += 1;
      index += 1;
      continue;
    }

    // Be slightly forgiving when the acoustic model inserts exactly one
    // unknown token between a clearly recognised "six" and "seven".
    if (tokens[index + 1] === '[unk]' && tokens[index + 2] === 'seven') {
      count += 1;
      index += 2;
    }
  }
  return count;
}

export class MonotonicVoiceScorer {
  constructor() {
    this.reset();
  }

  reset() {
    this.committedScore = 0;
    this.currentSegmentBest = 0;
  }

  get score() {
    return this.committedScore + this.currentSegmentBest;
  }

  observePartial(value) {
    this.currentSegmentBest = Math.max(
      this.currentSegmentBest,
      countSixSevenPhrases(value),
    );
    return this.score;
  }

  commitFinal(value = '') {
    this.currentSegmentBest = Math.max(
      this.currentSegmentBest,
      countSixSevenPhrases(value),
    );
    this.committedScore += this.currentSegmentBest;
    this.currentSegmentBest = 0;
    return this.score;
  }
}
