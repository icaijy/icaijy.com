const RUN_SECONDS = 20;
const ROLLING_WINDOW_SECONDS = 2;
const SAMPLE_STEP_SECONDS = 0.25;
const BURST_SECONDS = 5;

export function rollingRateSeries(timeline, duration = RUN_SECONDS) {
  const sorted = [...timeline].map(Number).filter(Number.isFinite).sort((a, b) => a - b);
  const points = [];
  for (let time = 0; time <= duration + 1e-9; time += SAMPLE_STEP_SECONDS) {
    const centre = Math.min(duration, Number(time.toFixed(4)));
    const start = Math.max(0, centre - ROLLING_WINDOW_SECONDS / 2);
    const end = Math.min(duration, centre + ROLLING_WINDOW_SECONDS / 2);
    const span = Math.max(0.001, end - start);
    const count = sorted.filter((event) => event >= start && event <= end).length;
    points.push({ time: centre, rate: count / span });
  }
  return points;
}

export function analyseTimeline(timeline, duration = RUN_SECONDS) {
  const sorted = [...timeline].map(Number).filter(Number.isFinite).sort((a, b) => a - b);
  const series = rollingRateSeries(sorted, duration);
  const interior = series.filter((point) => point.time >= 1 && point.time <= duration - 1);
  const peak = (interior.length ? interior : series).reduce(
    (best, point) => point.rate > best.rate ? point : best,
    { time: 0, rate: 0 },
  );

  let bestBurst = { start: 0, end: Math.min(BURST_SECONDS, duration), count: 0, rate: 0 };
  let right = 0;
  for (let left = 0; left < sorted.length; left += 1) {
    if (right < left) right = left;
    while (right < sorted.length && sorted[right] <= sorted[left] + BURST_SECONDS) right += 1;
    const count = right - left;
    if (count > bestBurst.count) {
      const start = Math.min(sorted[left], Math.max(0, duration - BURST_SECONDS));
      bestBurst = {
        start,
        end: Math.min(duration, start + BURST_SECONDS),
        count,
        rate: count / Math.min(BURST_SECONDS, duration),
      };
    }
  }

  const firstHalfCount = sorted.filter((event) => event <= duration / 2).length;
  const secondHalfCount = sorted.length - firstHalfCount;
  return {
    series,
    averageRate: sorted.length / duration,
    peakRate: peak.rate,
    peakTime: peak.time,
    fastestBurst: bestBurst,
    firstHalfRate: firstHalfCount / (duration / 2),
    secondHalfRate: secondHalfCount / (duration / 2),
  };
}

function formatRate(value) {
  return Number(value || 0).toFixed(1);
}

function drawChart(canvas, series, unit, hoverNode) {
  const context = canvas.getContext('2d');
  const cssWidth = Math.max(300, canvas.clientWidth || 700);
  const cssHeight = 260;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(cssWidth * ratio);
  canvas.height = Math.round(cssHeight * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, cssWidth, cssHeight);

  const padding = { left: 48, right: 18, top: 18, bottom: 34 };
  const plotWidth = cssWidth - padding.left - padding.right;
  const plotHeight = cssHeight - padding.top - padding.bottom;
  const maxRate = Math.max(1, ...series.map((point) => point.rate));
  const yMax = Math.ceil(maxRate * 1.15 * 2) / 2;
  const rootStyle = getComputedStyle(document.documentElement);
  const accent = rootStyle.getPropertyValue('--bs-primary').trim() || '#0d6efd';
  const muted = rootStyle.getPropertyValue('--bs-secondary-color').trim() || '#6c757d';
  const border = rootStyle.getPropertyValue('--bs-border-color').trim() || '#dee2e6';

  const x = (time) => padding.left + (time / RUN_SECONDS) * plotWidth;
  const y = (rate) => padding.top + plotHeight - (rate / yMax) * plotHeight;

  context.font = '12px system-ui, sans-serif';
  context.lineWidth = 1;
  context.strokeStyle = border;
  context.fillStyle = muted;
  context.textAlign = 'center';
  for (const tick of [0, 5, 10, 15, 20]) {
    const px = x(tick);
    context.beginPath();
    context.moveTo(px, padding.top);
    context.lineTo(px, padding.top + plotHeight);
    context.stroke();
    context.fillText(`${tick}s`, px, cssHeight - 10);
  }

  context.textAlign = 'right';
  for (let index = 0; index <= 4; index += 1) {
    const value = yMax * index / 4;
    const py = y(value);
    context.beginPath();
    context.moveTo(padding.left, py);
    context.lineTo(padding.left + plotWidth, py);
    context.stroke();
    context.fillText(value.toFixed(value < 10 ? 1 : 0), padding.left - 7, py + 4);
  }

  context.save();
  context.translate(12, padding.top + plotHeight / 2);
  context.rotate(-Math.PI / 2);
  context.textAlign = 'center';
  context.fillText(unit, 0, 0);
  context.restore();

  context.strokeStyle = accent;
  context.lineWidth = 3;
  context.lineJoin = 'round';
  context.lineCap = 'round';
  context.beginPath();
  series.forEach((point, index) => {
    const px = x(point.time);
    const py = y(point.rate);
    if (index === 0) context.moveTo(px, py);
    else context.lineTo(px, py);
  });
  context.stroke();

  canvas.onpointermove = (event) => {
    const rect = canvas.getBoundingClientRect();
    const localX = Math.max(0, Math.min(rect.width, event.clientX - rect.left));
    const time = (localX / rect.width) * RUN_SECONDS;
    const nearest = series.reduce((best, point) =>
      Math.abs(point.time - time) < Math.abs(best.time - time) ? point : best,
    series[0]);
    if (hoverNode) hoverNode.textContent = `${nearest.time.toFixed(1)}s · ${formatRate(nearest.rate)} ${unit}`;
  };
  canvas.onpointerleave = () => {
    if (hoverNode) hoverNode.textContent = 'Move across the chart to inspect the rolling rate.';
  };
}

const timelineNode = document.getElementById('run-event-timeline');
const analysisRoot = document.getElementById('run-speed-analysis');
if (timelineNode && analysisRoot) {
  const timeline = JSON.parse(timelineNode.textContent || '[]');
  const unit = analysisRoot.dataset.speedUnit || 'moves/s';
  const analysis = analyseTimeline(timeline);

  const setText = (id, value) => {
    const node = document.getElementById(id);
    if (node) node.textContent = value;
  };
  setText('run-average-rate', `${formatRate(analysis.averageRate)} ${unit}`);
  setText('run-peak-rate', `${formatRate(analysis.peakRate)} ${unit}`);
  setText('run-peak-time', `around ${analysis.peakTime.toFixed(1)}s`);
  setText('run-fastest-burst', `${analysis.fastestBurst.count} counts`);
  setText(
    'run-fastest-burst-time',
    `${analysis.fastestBurst.start.toFixed(1)}–${analysis.fastestBurst.end.toFixed(1)}s · ${formatRate(analysis.fastestBurst.rate)} ${unit}`,
  );
  setText('run-first-half-rate', `${formatRate(analysis.firstHalfRate)} ${unit}`);
  setText('run-second-half-rate', `${formatRate(analysis.secondHalfRate)} ${unit}`);

  const canvas = document.getElementById('run-speed-chart');
  const hoverNode = document.getElementById('run-speed-hover');
  if (canvas) {
    const render = () => drawChart(canvas, analysis.series, unit, hoverNode);
    render();
    const observer = new ResizeObserver(render);
    observer.observe(canvas.parentElement || canvas);
  }
}
