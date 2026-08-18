const SHERPA_PACKAGE_VERSION = '1.3.1';
const SHERPA_WASM_BASE = `https://cdn.jsdelivr.net/npm/@siteed/sherpa-onnx.rn@${SHERPA_PACKAGE_VERSION}/wasm/`;
const KWS_MODEL_BASE = 'https://huggingface.co/deeeed/sherpa-voice-models/resolve/main/kws';
const KWS_MODEL_DIR = '/icaijy-kws';

// GigaSpeech BPE contains both words as complete pieces. The @suffix is the
// label returned by sherpa-onnx when this keyword path fires.
const SIX_SEVEN_KEYWORD = '▁SIX ▁SEVEN @SIX_SEVEN\n';

const MODEL_FILES = {
  encoder: 'encoder-epoch-12-avg-2-chunk-16-left-64.onnx',
  decoder: 'decoder-epoch-12-avg-2-chunk-16-left-64.onnx',
  joiner: 'joiner-epoch-12-avg-2-chunk-16-left-64.onnx',
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
  return Boolean(
    window.Module?.FS &&
    (typeof window.createKws === 'function' || typeof window.Kws === 'function')
  );
}

async function loadSherpaKwsRuntime() {
  if (sherpaRuntimeReady()) return window.Module;
  if (runtimePromise) return runtimePromise;

  runtimePromise = (async () => {
    // The combined package can load many speech features; only load the core
    // filesystem wrapper and KWS wrapper for this page.
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

function ensureFsDirectory(Module, path) {
  let current = '';
  for (const part of path.split('/').filter(Boolean)) {
    current += `/${part}`;
    try {
      if (!Module.FS.analyzePath(current).exists) Module.FS.mkdir(current);
    } catch (error) {
      if (!Module.FS.analyzePath(current).exists) throw error;
    }
  }
}

async function fetchIntoFs(Module, filename) {
  const destination = `${KWS_MODEL_DIR}/${filename}`;
  try {
    if (Module.FS.analyzePath(destination).exists) return destination;
  } catch {
    // Continue to fetch it.
  }

  const response = await fetch(`${KWS_MODEL_BASE}/${filename}`, { cache: 'force-cache' });
  if (!response.ok) throw new Error(`Could not download ${filename} (HTTP ${response.status}).`);
  const bytes = new Uint8Array(await response.arrayBuffer());
  Module.FS.writeFile(destination, bytes);
  return destination;
}

function makeSpotter(Module, paths) {
  const config = {
    featConfig: {
      samplingRate: 16000,
      featureDim: 80,
    },
    modelConfig: {
      transducer: {
        encoder: paths.encoder,
        decoder: paths.decoder,
        joiner: paths.joiner,
      },
      tokens: paths.tokens,
      provider: 'cpu',
      modelType: '',
      numThreads: 1,
      debug: 0,
      modelingUnit: '',
      bpeVocab: '',
    },
    maxActivePaths: 4,
    // Keep confirmation quick: the game repeatedly says the same phrase with
    // little silence between repetitions.
    numTrailingBlanks: 1,
    keywordsScore: 1.5,
    keywordsThreshold: 0.25,
    keywordsFile: paths.keywords,
  };

  const spotter = typeof window.createKws === 'function'
    ? window.createKws(Module, config)
    : new window.Kws(config, Module);

  if (!spotter?.handle) throw new Error('Could not create the local SIX SEVEN keyword spotter.');
  return spotter;
}

export async function loadSixSevenVoiceModel(onStatus = () => {}) {
  if (loadedModel?.ready) return loadedModel;
  if (modelPromise) return modelPromise;

  modelPromise = (async () => {
    onStatus('Loading local keyword-spotting runtime…');
    const Module = await loadSherpaKwsRuntime();
    ensureFsDirectory(Module, KWS_MODEL_DIR);

    onStatus('Loading local SIX SEVEN keyword model…');
    const entries = await Promise.all(
      Object.entries(MODEL_FILES).map(async ([key, filename]) => [key, await fetchIntoFs(Module, filename)]),
    );
    const paths = Object.fromEntries(entries);

    // @siteed's current browser KWS glue consumes keywords through a file path
    // in the Emscripten filesystem. Keep our one game-specific wake phrase
    // entirely local rather than downloading a generic keywords file.
    paths.keywords = `${KWS_MODEL_DIR}/keywords.txt`;
    Module.FS.writeFile(paths.keywords, SIX_SEVEN_KEYWORD);

    const spotter = makeSpotter(Module, paths);
    loadedModel = {
      ready: true,
      Module,
      spotter,
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
      // Reset immediately after a wake-word hit so the next repeated
      // "six seven" starts from a clean decoder state.
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
    const silence = new Float32Array(Math.round(16000 * 0.45));
    this.stream.acceptWaveform(16000, silence);
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
