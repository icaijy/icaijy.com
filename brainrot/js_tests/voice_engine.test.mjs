import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const source = await readFile(
  new URL('../static/brainrot/voice_engine.js', import.meta.url),
  'utf8',
);
const {
  MonotonicVoiceScorer,
  countSixSevenPhrases,
  normaliseVoiceTranscript,
} = await import(
  `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`
);

test('normalises local recogniser tokens without fuzzy guessing', () => {
  assert.equal(normaliseVoiceTranscript('Six, seven! [unk] SIX-seven.'), 'six seven [unk] six seven');
});

test('counts explicit repeated six seven pairs', () => {
  assert.equal(countSixSevenPhrases('six seven six seven six seven'), 3);
});

test('allows exactly one unknown between six and seven', () => {
  assert.equal(countSixSevenPhrases('six [unk] seven six seven'), 2);
  assert.equal(countSixSevenPhrases('six [unk] [unk] seven'), 0);
});

test('does not count numbers, sixty seven, fused words, or incomplete pairs', () => {
  assert.equal(countSixSevenPhrases('6 7 67 sixty seven sixseven six'), 0);
});

test('greedily counts only complete ordered pairs', () => {
  assert.equal(countSixSevenPhrases('seven six seven six six seven seven'), 2);
});

test('extra six tokens do not manufacture an extra pair', () => {
  assert.equal(countSixSevenPhrases('six six seven six seven'), 2);
});

test('partial revisions never subtract an awarded point or double count one segment', () => {
  const scorer = new MonotonicVoiceScorer();

  assert.equal(scorer.observePartial('six seven'), 1);
  assert.equal(scorer.observePartial('six'), 1);
  assert.equal(scorer.observePartial('six seven'), 1);
  assert.equal(scorer.commitFinal('six'), 1);

  assert.equal(scorer.observePartial('six [unk] seven'), 2);
  assert.equal(scorer.commitFinal('six seven'), 2);
});
