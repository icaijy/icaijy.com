const SHERPA_PACKAGE_VERSION = '1.3.1';
const SHERPA_WASM_BASE = `https://cdn.jsdelivr.net/npm/@siteed/sherpa-onnx.rn@${SHERPA_PACKAGE_VERSION}/wasm/`;
const KWS_MODEL_BASE = 'https://modelscope.cn/models/pkufool/sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01/resolve/master';
const KWS_MODEL_DIR = '/icaijy-kws';
const SIX_SEVEN_LABEL = 'SIX_SEVEN';

// Use the official int8 export: substantially smaller to download in-browser
// while keeping the encoder/decoder/joiner/token table from one exact model.
const MODEL_FILES = {
  encoder: 'encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx',
  decoder: 'decoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx',
  joiner: 'joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx',
  tokens: 'tokens.txt',
};

let runtimePromise = null;
let modelPromise = null;
let loadedModel = null;

function loadScript(url, marker) {
  const markerAttribute = `data-${marker}`;
  const existing = document.querySelector(`script[${markerAttribute}]`);
  if (existing) {
    if (existing.getAttribute('data-loaded') === '1') return Promise.resolve();
    return new Promise((resolve, reject) => {
      existing.addEventListener('load', resolve, { once: true });
      existing.addEventListener('error', () => reject(new Error(`Could not load ${url}`)), { once: true });
    });
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = url;
    script.async = false;
    script.crossOrigin = 'anonymous';
    script.setAttribute(markerAttribute, '1');
    script.addEventListener('load', () => {
      script.setAttribute('data-loaded', '1');
      resolve();
    }, { once: true });
    script.addEventListener('error', () => reject(new Error(`Could not load ${url}`)), { once: true });
    document.head.appendChild(script);
  });
}

function sherpaRuntimeReady() {
  return Boolean(window.Module?.FS && window.SherpaOnnx?.KWS);
}

async function loadSherpaKwsRuntime() {
  if (sherpaRuntimeReady()) return window.Module;
  if (runtimePromise) return runtimePromise;

  runtimePromise = (async () => {
    // The combined runtime supports many speech features. Restrict the page to
    // the core filesystem helper plus keyword spotting only.
    window.sherpaOnnxModulePaths = [
      `${SHERPA_WASM_BASE}sherpa-onnx-core.js`,
      `${SHERPA_WASM_BASE}sherpa-onnx-kws.js`,
    ];

    await loadScript(`${SHERPA_WASM_BASE}sherpa-onnx-wasm-combined.js`, 'icaijy-sherpa-wasm');

    await new Promise((resolve, reject) => {
      if (sherpaRuntimeReady()) {
        resolve();
        return;
      }

      let settled = false;
      const previousReady = window.onSherpaOnnxReady;
      let timer = null;
      const finish = (error = null) => {
        if (settled) return;
        settled = true;
        if (timer !== null) window.clearTimeout(timer);
        if (error) reject(error);
        else resolve();
      };

      window.onSherpaOnnxReady = (loaded) => {
        try {
          previousReady?.(loaded);
        } catch (error) {
          console.debug('Previous sherpa ready callback failed.', error);
        }
        if (loaded && sherpaRuntimeReady()) finish();
        else if (!loaded) finish(new Error('The local keyword-spotting runtime failed to initialise.'));
      };

      timer = window.setTimeout(() => {
        if (sherpaRuntimeReady()) finish();
        else finish(new Error('The local keyword-spotting runtime timed out while loading.'));
      }, 45_000);

      loadScript(`${SHERPA_WASM_BASE}sherpa-onnx-combined.js`, 'icaijy-sherpa-modules')
        .catch((error) => finish(error));
    });

    if (!sherpaRuntimeReady()) {
      throw new Error('Sherpa KWS loaded without the expected browser API.');
    }
    return window.Module;
  })().catch((error) => {
    runtimePromise = null;
    throw error;
  });

  return runtimePromise;
}

function modelUrl(filename) {
  return `${KWS_MODEL_BASE}/${filename}`;
}

/**
 * Enumerate every vocabulary-token path whose concatenated SentencePiece text
 * is exactly the requested word. For these tiny words there are at most a few
 * dozen character-boundary segmentations, so registering all valid paths is
 * cheap and avoids hard-coding a tokenizer-specific BPE split.
 */
export function enumerateBpeWordPaths(word, tokensMap) {
  if (!tokensMap || typeof tokensMap !== 'object') return [];

  const target = `▁${String(word).toUpperCase()}`;
  const vocabulary = Object.keys(tokensMap).filter((token) => {
    if (!token || token.startsWith('<')) return false;
    if (token.includes(' ') || token.includes('@')) return false;
    return target.includes(token);
  });

  const memo = new Map();
  const visit = (offset) => {
    if (offset === target.length) return [[]];
    if (memo.has(offset)) return memo.get(offset);

    const paths = [];
    for (const token of vocabulary) {
      if (!target.startsWith(token, offset)) continue;
      const suffixPaths = visit(offset + token.length);
      for (const suffix of suffixPaths) {
        paths.push([token, ...suffix]);
      }
    }
    memo.set(offset, paths);
    return paths;
  };

  return visit(0);
}

export function buildSixSevenKeywords(tokensMap) {
  const sixPaths = enumerateBpeWordPaths('SIX', tokensMap);
  const sevenPaths = enumerateBpeWordPaths('SEVEN', tokensMap);

  if (!sixPaths.length || !sevenPaths.length) {
    const missing = [];
    if (!sixPaths.length) missing.push('SIX');
    if (!sevenPaths.length) missing.push('SEVEN');
    throw new Error(`The local keyword model cannot tokenise: ${missing.join(', ')}.`);
  }

  const lines = [];
  const seen = new Set();
  for (const six of sixPaths) {
    for (const seven of sevenPaths) {
      const line = `${six.join(' ')} ${seven.join(' ')} @${SIX_SEVEN_LABEL}`;
      if (!seen.has(line)) {
        seen.add(line);
        lines.push(line);
      }
    }
  }

  // SIX and SEVEN are short enough that the theoretical number of character
  // boundary segmentations is tiny. Guard anyway if a future model has an
  // unexpectedly pathological vocabulary.
  if (lines.length > 256) {
    throw new Error(`The local keyword model produced too many SIX SEVEN token paths (${lines.length}).`);
  }
  return lines.join('\n');
}

export async function loadSixSevenVoiceModel(onStatus = () => {}) {
  if (loadedModel?.ready) return loadedModel;
  if (modelPromise) return modelPromise;

  modelPromise = (async () => {
    onStatus('Loading local keyword-spotting runtime…');
    await loadSherpaKwsRuntime();

    const KWS = window.SherpaOnnx.KWS;
    onStatus('Loading local SIX SEVEN keyword model (~5 MB)…');
    const modelInfo = await KWS.loadModel({
      modelDir: KWS_MODEL_DIR,
      encoder: modelUrl(MODEL_FILES.encoder),
      decoder: modelUrl(MODEL_FILES.decoder),
      joiner: modelUrl(MODEL_FILES.joiner),
      tokens: modelUrl(MODEL_FILES.tokens),
      debug: false,
    });

    const keywords = buildSixSevenKeywords(modelInfo?.paths?.tokensMap);
    console.debug('Voice 67 KWS token paths:', keywords);

    const spotter = KWS.createKeywordSpotter(modelInfo, {
      keywords,
      sampleRate: 16000,
      numThreads: 1,
      provider: 'cpu',
      maxActivePaths: 4,
      // The game repeats the phrase with very little silence. Keep the
      // post-keyword confirmation requirement as short as the runtime allows.
      numTrailingBlanks: 1,
      keywordsScore: 1.5,
      keywordsThreshold: 0.25,
      debug: false,
    });
    if (!spotter?.handle) throw new Error('Could not create the local SIX SEVEN keyword spotter.');

    loadedModel = {
      ready: true,
      spotter,
      keywords,
    };
    onStatus('Local SIX SEVEN keyword spotter ready');
    return loadedModel;
  })().catch((error) => {
    modelPromise = null;
    throw error;
  });

  return modelPromise;
}

export class SixSevenLocalRecognizer {
  constructor(model, sampleRate, handlers = {}) {
    if (!model?.ready || !model.spotter) throw new Error('The local keyword model is not ready.');
    this.model = model;
    this.sampleRate = sampleRate;
    this.handlers = handlers;
    this.stream = model.spotter.createStream();
    if (!this.stream?.handle) throw new Error('Could not create a keyword-spotting stream.');
  }

  drain() {
    if (!this.stream) return 0;
    let detections = 0;
    const { spotter } = this.model;

    while (spotter.isReady(this.stream)) {
      spotter.decode(this.stream);
      const result = spotter.getResult(this.stream);
      if (!result?.keyword) continue;

      detections += 1;
      // Wake-word semantics: one complete SIX SEVEN emits one event, then the
      // decoder resets immediately so the next repetition can start cleanly.
      spotter.reset(this.stream);
      this.handlers.onResult?.('six seven', result);
    }
    return detections;
  }

  acceptWaveform(audioBuffer) {
    if (!this.stream) return;
    if (!audioBuffer || audioBuffer.numberOfChannels < 1) return;
    const samples = audioBuffer.getChannelData(0);
    this.stream.acceptWaveform(audioBuffer.sampleRate || this.sampleRate, samples);
    this.drain();
  }

  async finalise() {
    if (!this.stream) return '';

    // Human audio stops exactly at the 20-second boundary. Feed only synthetic
    // silence afterwards so a phrase completed just before time can satisfy
    // the spotter's trailing-blank requirement without accepting late speech.
    // Keep the same input sample rate used by the live stream: sherpa's
    // resampler is stateful and intentionally rejects a mid-stream rate change.
    const inputRate = this.sampleRate || 16000;
    const silence = new Float32Array(Math.round(inputRate * 0.45));
    this.stream.acceptWaveform(inputRate, silence);
    this.stream.inputFinished();
    this.drain();
    return '';
  }

  remove() {
    try {
      this.stream?.free();
    } finally {
      this.stream = null;
    }
  }
}

export function releaseSixSevenVoiceModel() {
  if (loadedModel?.spotter) {
    try {
      loadedModel.spotter.free();
    } catch (error) {
      console.debug('Sherpa KWS cleanup failed.', error);
    }
  }
  loadedModel = null;
  modelPromise = null;
}
