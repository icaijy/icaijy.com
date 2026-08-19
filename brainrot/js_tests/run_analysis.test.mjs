import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const source = await readFile(
  new URL('../static/brainrot/run_analysis.js', import.meta.url),
  'utf8',
);
const { analyseTimeline, rollingRateSeries } = await import(
  `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`
);

test('steady pacing produces roughly steady half rates', () => {
  const steady = Array.from({ length: 40 }, (_, index) => (index + 0.5) * 0.5);
  const analysis = analyseTimeline(steady);
  assert.equal(analysis.averageRate, 2);
  assert.ok(Math.abs(analysis.firstHalfRate - 2) < 0.11);
  assert.ok(Math.abs(analysis.secondHalfRate - 2) < 0.11);
  assert.ok(analysis.fastestBurst.count >= 10);
});

test('bursty pacing locates the middle burst', () => {
  const bursty = [
    0.5, 1.0, 1.5,
    8.0, 8.2, 8.4, 8.6, 8.8, 9.0, 9.2, 9.4, 9.6, 9.8,
    17.0, 18.0, 19.0,
  ];
  const analysis = analyseTimeline(bursty);
  assert.ok(analysis.peakTime >= 8 && analysis.peakTime <= 10.5);
  assert.ok(analysis.fastestBurst.start <= 8.0);
  assert.ok(analysis.fastestBurst.end >= 9.8);
  assert.ok(analysis.fastestBurst.count >= 10);
});

test('rolling series covers the complete 20 second run', () => {
  const series = rollingRateSeries([5, 5.2, 5.4, 5.6]);
  assert.equal(series[0].time, 0);
  assert.equal(series.at(-1).time, 20);
  assert.ok(series.find((point) => point.time === 5.25).rate > series.find((point) => point.time === 15).rate);
});
