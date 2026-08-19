import { rollingRateSeries } from './run_analysis.js';

const tr = (message) => typeof gettext === 'function' ? gettext(message) : message;

function drawSparkline(root) {
  const canvas = root.querySelector('.hof-mini-chart');
  const label = root.querySelector('[data-mini-pace-label]');
  if (!canvas) return;

  let timeline = [];
  try {
    timeline = JSON.parse(root.dataset.eventTimeline || '[]');
  } catch (error) {
    console.warn('Could not parse HOF mini pacing timeline.', error);
    return;
  }

  const series = rollingRateSeries(timeline);
  const context = canvas.getContext('2d');
  if (!context || !series.length) return;

  const width = Math.max(220, canvas.clientWidth || 320);
  const height = 76;
  const ratio = window.devicePixelRatio || 1;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  context.clearRect(0, 0, width, height);

  const style = getComputedStyle(document.documentElement);
  const accent = style.getPropertyValue('--bs-primary').trim() || '#0d6efd';
  const border = style.getPropertyValue('--bs-border-color').trim() || '#dee2e6';
  const maxRate = Math.max(1, ...series.map((point) => point.rate));
  const padding = 4;
  const x = (time) => padding + (time / 20) * (width - padding * 2);
  const y = (rate) => height - padding - (rate / maxRate) * (height - padding * 2);

  context.strokeStyle = border;
  context.lineWidth = 1;
  context.beginPath();
  context.moveTo(padding, height - padding);
  context.lineTo(width - padding, height - padding);
  context.stroke();

  context.strokeStyle = accent;
  context.lineWidth = 2.25;
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

  if (label) {
    const unit = root.dataset.speedUnit || 'moves/s';
    const average = timeline.length / 20;
    label.textContent = `${tr('avg')} ${average.toFixed(1)} ${unit}`;
  }
}

const roots = [...document.querySelectorAll('[data-mini-analysis]')];
roots.forEach(drawSparkline);

if ('ResizeObserver' in window) {
  const observer = new ResizeObserver((entries) => {
    entries.forEach((entry) => {
      const root = entry.target.closest('[data-mini-analysis]');
      if (root) drawSparkline(root);
    });
  });
  roots.forEach((root) => observer.observe(root));
}
