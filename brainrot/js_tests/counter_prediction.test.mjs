import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const source = await readFile(
  new URL('../static/brainrot/counter_prediction.js', import.meta.url),
  'utf8',
);
const { projectFinalScore } = await import(
  `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`
);

test('early projection extrapolates the overall pace', () => {
  assert.equal(projectFinalScore(20, 2), 200);
});

test('late projection reacts to a slowdown without falling below current score', () => {
  const projected = projectFinalScore(120, 15, 4);
  assert.ok(projected >= 120);
  assert.ok(projected < 160);
});

test('projection stays hidden until enough evidence exists', () => {
  assert.equal(projectFinalScore(0, 5), null);
  assert.equal(projectFinalScore(5, 1), null);
});
