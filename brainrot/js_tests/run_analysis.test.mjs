import assert from 'node:assert/strict';
import { analyseTimeline, rollingRateSeries } from '../static/brainrot/run_analysis.js';

const steady = Array.from({ length: 40 }, (_, index) => (index + 0.5) * 0.5);
const steadyAnalysis = analyseTimeline(steady);
assert.equal(steadyAnalysis.averageRate, 2);
assert.ok(Math.abs(steadyAnalysis.firstHalfRate - 2) < 0.11);
assert.ok(Math.abs(steadyAnalysis.secondHalfRate - 2) < 0.11);
assert.ok(steadyAnalysis.fastestBurst.count >= 10);

const bursty = [
  0.5, 1.0, 1.5,
  8.0, 8.2, 8.4, 8.6, 8.8, 9.0, 9.2, 9.4, 9.6, 9.8,
  17.0, 18.0, 19.0,
];
const burstyAnalysis = analyseTimeline(bursty);
assert.ok(burstyAnalysis.peakTime >= 8 && burstyAnalysis.peakTime <= 10.5);
assert.ok(burstyAnalysis.fastestBurst.start <= 8.0);
assert.ok(burstyAnalysis.fastestBurst.end >= 9.8);
assert.ok(burstyAnalysis.fastestBurst.count >= 10);

const series = rollingRateSeries([5, 5.2, 5.4, 5.6]);
assert.equal(series[0].time, 0);
assert.equal(series.at(-1).time, 20);
assert.ok(series.find((point) => point.time === 5.25).rate > series.find((point) => point.time === 15).rate);

console.log('run_analysis tests passed');
