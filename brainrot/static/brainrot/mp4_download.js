const MEDIABUNNY_URL = 'https://cdn.jsdelivr.net/npm/mediabunny@1.52.2/dist/bundles/mediabunny.min.mjs';
let mediabunnyPromise = null;

function loadMediabunny() {
  if (!mediabunnyPromise) mediabunnyPromise = import(MEDIABUNNY_URL);
  return mediabunnyPromise;
}

function clampProgress(value) {
  return Math.max(0, Math.min(1, Number(value) || 0));
}

function mp4Filename(filename = 'counted-video') {
  return `${filename.replace(/\.(?:webm|mp4)$/i, '')}.mp4`;
}

function isMp4(blob) {
  return (blob.type || '').toLowerCase().split(';')[0] === 'video/mp4';
}

export async function convertVideoToMp4(blob, onProgress = () => {}) {
  if (!(blob instanceof Blob)) throw new TypeError('Expected a video Blob.');
  if (isMp4(blob)) return blob;

  const {
    ALL_FORMATS,
    BlobSource,
    BufferTarget,
    Conversion,
    Input,
    Mp4OutputFormat,
    Output,
  } = await loadMediabunny();

  const input = new Input({
    formats: ALL_FORMATS,
    source: new BlobSource(blob),
  });
  const target = new BufferTarget();
  const output = new Output({
    format: new Mp4OutputFormat({ fastStart: 'in-memory' }),
    target,
  });

  try {
    const conversion = await Conversion.init({
      input,
      output,
      video: {
        codec: 'avc',
        bitrate: 1_600_000,
        keyFrameInterval: 2,
      },
      audio: { discard: true },
    });
    if (!conversion.isValid) {
      throw new Error('This browser cannot convert this recording to MP4.');
    }
    conversion.onProgress = (progress) => onProgress(clampProgress(progress));
    await conversion.execute();
    if (!target.buffer) throw new Error('MP4 conversion completed without output data.');
    onProgress(1);
    return new Blob([target.buffer], { type: 'video/mp4' });
  } finally {
    await input.dispose?.();
  }
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = mp4Filename(filename);
  link.hidden = true;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

export function installMp4Download(anchor, options = {}) {
  if (!anchor || anchor.dataset.mp4DownloadBound === 'true') return;
  anchor.dataset.mp4DownloadBound = 'true';

  anchor.addEventListener('click', async (event) => {
    const href = anchor.href;
    if (!href || anchor.getAttribute('aria-busy') === 'true') return;
    event.preventDefault();

    const originalText = anchor.textContent;
    const originalDownload = anchor.getAttribute('download') || options.filename || 'counted-video.webm';
    const setBusyLabel = (progress = null) => {
      anchor.textContent = progress === null ? 'MP4…' : `MP4… ${Math.round(progress * 100)}%`;
    };

    anchor.setAttribute('aria-busy', 'true');
    anchor.classList.add('disabled');
    setBusyLabel();
    options.onStatus?.('Preparing MP4…');

    try {
      const response = await fetch(href, { credentials: 'same-origin' });
      if (!response.ok) throw new Error(`Could not read the video (HTTP ${response.status}).`);
      const sourceBlob = await response.blob();
      const mp4Blob = await convertVideoToMp4(sourceBlob, (progress) => {
        setBusyLabel(progress);
        options.onProgress?.(progress);
      });
      triggerDownload(mp4Blob, originalDownload);
      options.onStatus?.('MP4 ready.');
    } catch (error) {
      console.error('MP4 download failed.', error);
      options.onError?.(error);
    } finally {
      anchor.textContent = originalText;
      anchor.classList.remove('disabled');
      anchor.removeAttribute('aria-busy');
    }
  });
}
