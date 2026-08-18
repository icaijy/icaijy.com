import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const source = await readFile(
  new URL('../static/brainrot/voice_words.js', import.meta.url),
  'utf8',
);
const { SixSevenWordPairDetector } = await import(
  `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`
);

function detector() {
  return new SixSevenWordPairDetector({
    sixIndex: 0,
    sevenIndex: 1,
    minTargetScore: 0.30,
    minTargetShareOfGlobal: 0.55,
    minTargetMargin: 0.05,
    pairTimeoutMs: 1000,
    minRearmAfterCountMs: 70,
    minPairIntervalMs: 180,
  });
}

const six = [0.72, 0.08, 0.20];
const seven = [0.09, 0.70, 0.21];
const unknown = [0.12, 0.10, 0.78];

test('a six followed by seven counts exactly one pair', () => {
  const d = detector();
  assert.equal(d.observe(six, 0).counted, false);
  assert.equal(d.observe(seven, 100).counted, true);
  assert.equal(d.observe(seven, 200).counted, false);
});

test('unknown windows between six and seven do not erase the armed pair', () => {
  const d = detector();
  d.observe(six, 0);
  assert.equal(d.observe(unknown, 80).counted, false);
  assert.equal(d.observe(seven, 160).counted, true);
});

test('rapid repeated six-seven pairs can count without phrase-level reset delay', () => {
  const d = detector();
  const hits = [];
  for (const [time, scores] of [
    [0, six], [100, seven], [180, six], [280, seven],
    [360, six], [460, seven], [540, six], [640, seven],
  ]) {
    if (d.observe(scores, time).counted) hits.push(time);
  }
  assert.deepEqual(hits, [100, 280, 460, 640]);
});

test('low target confidence or a much stronger competing class does not arm', () => {
  const d = detector();
  assert.equal(d.observe([0.22, 0.05, 0.73], 0).word, '');
  assert.equal(d.observe([0.31, 0.04, 0.90], 100).word, '');
  assert.equal(d.observe(seven, 200).counted, false);
});

test('stale six expires instead of pairing with a much later seven', () => {
  const d = detector();
  d.observe(six, 0);
  assert.equal(d.observe(seven, 1200).counted, false);
});
