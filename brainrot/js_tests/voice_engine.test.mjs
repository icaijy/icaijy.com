import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const source = await readFile(
  new URL('../static/brainrot/voice_engine.js', import.meta.url),
  'utf8',
);
const { countSixSevenPhrases, normaliseVoiceTranscript } = await import(
  `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`
);

test('normalises punctuation without guessing fuzzy speech', () => {
  assert.equal(normaliseVoiceTranscript('Six, seven! SIX-seven.'), 'six seven six seven');
});

test('counts explicit repeated six seven pairs', () => {
  assert.equal(countSixSevenPhrases('six seven six seven six seven'), 3);
});

test('accepts digit normalisation produced by speech recognisers', () => {
  assert.equal(countSixSevenPhrases('6 7 67 six 7'), 3);
});

test('does not count sixty seven, fused words, or incomplete pairs', () => {
  assert.equal(countSixSevenPhrases('sixty seven sixseven six six'), 0);
});

test('greedily counts only complete adjacent pairs', () => {
  assert.equal(countSixSevenPhrases('seven six seven six six seven seven'), 2);
});
