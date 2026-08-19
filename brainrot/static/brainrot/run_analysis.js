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

export function unitScale(mode) {
  return mode === 'per-20s' ? RUN_SECONDS : 1;
}

function formatRate(value) {
  const numeric = Number(value || 0);
  return numeric >= 100 ? numeric.toFixed(0) : numeric.toFixed(1);
}

function chartGeometry(width, height) {
  const padding = { left: 52, right: 18, top: 20, bottom: 36 };
  return {
    padding,
    plotWidth: width - padding.left - padding.right,
    plotHeight: height - padding.top - padding.bottom,
  };
}

function drawChart(canvas, baseSeries, unit, scale, hoverNode, hoverPoint = null) {
  const context = canvas.getContext('2d');
  const cssWidth = Math.max(300, canvas.clientWidth || 700);
  const cssHeight = 270;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(cssWidth * ratio);
  canvas.height = Math.round(cssHeight * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, cssWidth, cssHeight);

  const { padding, plotWidth, plotHeight } = chartGeometry(cssWidth, cssHeight);
  const series = baseSeries.map((point) => ({ ...point, displayRate: point.rate * scale }));
  const maxRate = Math.max(1, ...series.map((point) => point.displayRate));
  const yMax = Math.ceil(maxRate * 1.15 * 2) / 2;
  const rootStyle = getComputedStyle(document.documentElement);
  const accent = rootStyle.getPropertyValue('--bs-primary').trim() || '#0d6efd';
  const muted = rootStyle.getPropertyValue('--bs-secondary-color').trim() || '#6c757d';
  const border = rootStyle.getPropertyValue('--bs-border-color').trim() || '#dee2e6';
  const body = rootStyle.getPropertyValue('--bs-body-color').trim() || '#212529';
  const surface = rootStyle.getPropertyValue('--bs-body-bg').trim() || '#ffffff';

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
    context.fillText(formatRate(value), padding.left - 7, py + 4);
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
    const py = y(point.displayRate);
    if (index === 0) context.moveTo(px, py);
    else context.lineTo(px, py);
  });
  context.stroke();

  if (hoverPoint) {
    const px = x(hoverPoint.time);
    const displayRate = hoverPoint.rate * scale;
    const py = y(displayRate);

    context.save();
    context.setLineDash([5, 5]);
    context.strokeStyle = muted;
    context.lineWidth = 1;
    context.beginPath();
    context.moveTo(px, padding.top);
    context.lineTo(px, padding.top + plotHeight);
    context.stroke();
    context.restore();

    context.fillStyle = surface;
    context.strokeStyle = accent;
    context.lineWidth = 3;
    context.beginPath();
    context.arc(px, py, 5, 0, Math.PI * 2);
    context.fill();
    context.stroke();

    const text = `${hoverPoint.time.toFixed(1)}s · ${formatRate(displayRate)} ${unit}`;
    context.font = '600 12px system-ui, sans-serif';
    const textWidth = context.measureText(text).width;
    const bubbleWidth = textWidth + 18;
    const bubbleHeight = 28;
    const bubbleX = Math.max(
      padding.left,
      Math.min(padding.left + plotWidth - bubbleWidth, px - bubbleWidth / 2),
    );
    const aboveY = py - bubbleHeight - 12;
    const bubbleY = aboveY >= padding.top ? aboveY : py + 12;
    context.fillStyle = body;
    context.fillRect(bubbleX, bubbleY, bubbleWidth, bubbleHeight);
    context.fillStyle = surface;
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText(text, bubbleX + bubbleWidth / 2, bubbleY + bubbleHeight / 2);
    context.textBaseline = 'alphabetic';

    if (hoverNode) hoverNode.textContent = text;
  }

  return { padding, plotWidth };
}

function initialisePage() {
  const timelineNode = document.getElementById('run-event-timeline');
  const analysisRoot = document.getElementById('run-speed-analysis');
  if (!timelineNode || !analysisRoot) return;

  const timeline = JSON.parse(timelineNode.textContent || '[]');
  const analysis = analyseTimeline(timeline);
  const unitPerSecond = analysisRoot.dataset.unitPerSecond || analysisRoot.dataset.speedUnit || 'moves/s';
  const unitPer20 = analysisRoot.dataset.unitPer20 || 'moves/20s';
  let displayMode = 'per-second';
  let hoverPoint = null;

  const setText = (id, value) => {
    const node = document.getElementById(id);
    if (node) node.textContent = value;
  };

  const currentUnit = () => displayMode === 'per-20s' ? unitPer20 : unitPerSecond;
  const currentScale = () => unitScale(displayMode);

  function renderMetrics() {
    const scale = currentScale();
    const unit = currentUnit();
    setText('run-average-rate', `${formatRate(analysis.averageRate * scale)} ${unit}`);
    setText('run-peak-rate', `${formatRate(analysis.peakRate * scale)} ${unit}`);
    setText('run-peak-time', `${analysis.peakTime.toFixed(1)}s`);
    setText('run-fastest-burst', `${analysis.fastestBurst.count}`);
    setText(
      'run-fastest-burst-time',
      `${analysis.fastestBurst.start.toFixed(1)}–${analysis.fastestBurst.end.toFixed(1)}s · ${formatRate(analysis.fastestBurst.rate * scale)} ${unit}`,
    );
    setText('run-first-half-rate', `${formatRate(analysis.firstHalfRate * scale)} ${unit}`);
    setText('run-second-half-rate', `${formatRate(analysis.secondHalfRate * scale)} ${unit}`);
  }

  const canvas = document.getElementById('run-speed-chart');
  const hoverNode = document.getElementById('run-speed-hover');

  function renderChart() {
    if (!canvas) return;
    drawChart(canvas, analysis.series, currentUnit(), currentScale(), hoverNode, hoverPoint);
  }

  if (canvas) {
    canvas.addEventListener('pointermove', (event) => {
      const rect = canvas.getBoundingClientRect();
      const { padding, plotWidth } = chartGeometry(rect.width, 270);
      const localX = Math.max(padding.left, Math.min(padding.left + plotWidth, event.clientX - rect.left));
      const time = ((localX - padding.left) / plotWidth) * RUN_SECONDS;
      hoverPoint = analysis.series.reduce((best, point) =>
        Math.abs(point.time - time) < Math.abs(best.time - time) ? point : best,
      analysis.series[0]);
      renderChart();
    });
    canvas.addEventListener('pointerleave', () => {
      hoverPoint = null;
      if (hoverNode) hoverNode.textContent = hoverNode.dataset.defaultText || '';
      renderChart();
    });
  }

  document.querySelectorAll('[data-speed-mode]').forEach((button) => {
    button.addEventListener('click', () => {
      displayMode = button.dataset.speedMode === 'per-20s' ? 'per-20s' : 'per-second';
      document.querySelectorAll('[data-speed-mode]').forEach((candidate) => {
        const active = candidate.dataset.speedMode === displayMode;
        candidate.classList.toggle('btn-dark', active);
        candidate.classList.toggle('btn-outline-dark', !active);
        candidate.setAttribute('aria-pressed', String(active));
      });
      renderMetrics();
      renderChart();
    });
  });

  renderMetrics();
  renderChart();
  if ('ResizeObserver' in window && canvas) {
    const observer = new ResizeObserver(renderChart);
    observer.observe(canvas.parentElement || canvas);
  }
}

if (typeof document !== 'undefined') initialisePage();
