const TFJS_VERSION = '4.22.0';
const SPEECH_COMMANDS_VERSION = '0.5.4';
const TFJS_URL = `https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@${TFJS_VERSION}/dist/tf.min.js`;
const SPEECH_COMMANDS_URL = `https://cdn.jsdelivr.net/npm/@tensorflow-models/speech-commands@${SPEECH_COMMANDS_VERSION}/dist/speech-commands.min.js`;

const MIN_TARGET_SCORE = 0.30;
const MIN_TARGET_SHARE_OF_GLOBAL = 0.55;
const MIN_TARGET_MARGIN = 0.05;
const PAIR_TIMEOUT_MS = 1000;
const MIN_REARM_AFTER_COUNT_MS = 70;
const MIN_PAIR_INTERVAL_MS = 180;
const OVERLAP_FACTOR = 0.90;

let runtimePromise = null;
let modelPromise = null;
let loadedModel = null;

function loadScript(url, marker) {
  const attr = `data-${marker}`;
  const existing = document.querySelector(`script[${attr}]`);
  if (existing) {
    if (existing.dataset.loaded === '1') return Promise.resolve();
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
    script.setAttribute(attr, '1');
    script.addEventListener('load', () => {
      script.dataset.loaded = '1';
      resolve();
    }, { once: true });
    script.addEventListener('error', () => reject(new Error(`Could not load ${url}`)), { once: true });
    document.head.appendChild(script);
  });
}

async function loadTfRuntime() {
  if (window.tf && window.speechCommands) return;
  if (runtimePromise) return runtimePromise;

  runtimePromise = (async () => {
    if (!window.tf) await loadScript(TFJS_URL, 'icaijy-tfjs');
    if (!window.speechCommands) {
      await loadScript(SPEECH_COMMANDS_URL, 'icaijy-speech-commands');
    }
    if (!window.tf || !window.speechCommands) {
      throw new Error('The local word-recognition runtime did not initialise.');
    }
    await window.tf.ready();
  })().catch((error) => {
    runtimePromise = null;
    throw error;
  });

  return runtimePromise;
}

export class SixSevenWordPairDetector {
  constructor(options = {}) {
    this.sixIndex = options.sixIndex;
    this.sevenIndex = options.sevenIndex;
    this.minTargetScore = options.minTargetScore ?? MIN_TARGET_SCORE;
    this.minTargetShareOfGlobal = options.minTargetShareOfGlobal ?? MIN_TARGET_SHARE_OF_GLOBAL;
    this.minTargetMargin = options.minTargetMargin ?? MIN_TARGET_MARGIN;
    this.pairTimeoutMs = options.pairTimeoutMs ?? PAIR_TIMEOUT_MS;
    this.minRearmAfterCountMs = options.minRearmAfterCountMs ?? MIN_REARM_AFTER_COUNT_MS;
    this.minPairIntervalMs = options.minPairIntervalMs ?? MIN_PAIR_INTERVAL_MS;
    this.reset();
  }

  reset() {
    this.armedAt = null;
    this.lastCountAt = -Infinity;
    this.lastWord = '';
  }

  classify(scores) {
    if (!scores || this.sixIndex == null || this.sevenIndex == null) return null;
    const sixScore = Number(scores[this.sixIndex] || 0);
    const sevenScore = Number(scores[this.sevenIndex] || 0);
    let globalMax = 0;
    for (const value of scores) globalMax = Math.max(globalMax, Number(value) || 0);

    const choose = (word, targetScore, otherScore) => {
      if (targetScore < this.minTargetScore) return null;
      if (targetScore + 1e-9 < globalMax * this.minTargetShareOfGlobal) return null;
      if (targetScore - otherScore < this.minTargetMargin) return null;
      return { word, targetScore, sixScore, sevenScore, globalMax };
    };

    return sixScore >= sevenScore
      ? choose('six', sixScore, sevenScore)
      : choose('seven', sevenScore, sixScore);
  }

  observe(scores, now = performance.now()) {
    const classified = this.classify(scores);
    const word = classified?.word || '';
    this.lastWord = word;

    if (this.armedAt !== null && now - this.armedAt > this.pairTimeoutMs) {
      this.armedAt = null;
    }

    if (word === 'six') {
      if (now - this.lastCountAt >= this.minRearmAfterCountMs) {
        this.armedAt = now;
      }
      return { word, counted: false, classified };
    }

    if (word === 'seven' && this.armedAt !== null) {
      if (now - this.lastCountAt >= this.minPairIntervalMs) {
        this.armedAt = null;
        this.lastCountAt = now;
        return { word, counted: true, classified };
      }
    }

    return { word, counted: false, classified };
  }
}

export async function loadSixSevenVoiceModel(onStatus = () => {}) {
  if (loadedModel?.ready) return loadedModel;
  if (modelPromise) return modelPromise;

  modelPromise = (async () => {
    onStatus('Loading local six/seven word model…');
    await loadTfRuntime();

    const recognizer = window.speechCommands.create('BROWSER_FFT', '18w');
    await recognizer.ensureModelLoaded();
    const labels = recognizer.wordLabels();
    const sixIndex = labels.indexOf('six');
    const sevenIndex = labels.indexOf('seven');
    if (sixIndex < 0 || sevenIndex < 0) {
      throw new Error('The local word model does not contain six and seven.');
    }

    loadedModel = {
      ready: true,
      recognizer,
      labels,
      sixIndex,
      sevenIndex,
    };
    onStatus('Local six/seven word model ready');
    return loadedModel;
  })().catch((error) => {
    modelPromise = null;
    throw error;
  });

  return modelPromise;
}

export class SixSevenLocalRecognizer {
  constructor(model, _sampleRate, handlers = {}) {
    if (!model?.ready || !model.recognizer) {
      throw new Error('The local six/seven word model is not ready.');
    }
    this.model = model;
    this.handlers = handlers;
    this.listening = false;
    this.detector = new SixSevenWordPairDetector({
      sixIndex: model.sixIndex,
      sevenIndex: model.sevenIndex,
    });
    // voice_counter.js historically creates a recognizer synchronously and
    // then spends 3.25 s in its countdown. Start the TF.js-owned microphone
    // pipeline immediately so it is warm before GO without rewriting that
    // mature runner.
    this.startPromise = this.start().catch((error) => {
      this.handlers.onError?.(error);
      throw error;
    });
  }

  async start() {
    if (this.listening) return;
    this.detector.reset();
    await this.model.recognizer.listen((result) => {
      try {
        const observed = this.detector.observe(result.scores, performance.now());
        this.handlers.onPartial?.(observed.word || '');
        if (observed.counted) {
          this.handlers.onResult?.('six seven', observed.classified || {});
        }
      } catch (error) {
        this.handlers.onError?.(error);
      }
    }, {
      probabilityThreshold: 0,
      invokeCallbackOnNoiseAndUnknown: true,
      overlapFactor: OVERLAP_FACTOR,
      suppressionTimeMillis: 0,
      includeSpectrogram: false,
      audioTrackConstraints: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
        channelCount: 1,
      },
    });
    this.listening = true;
  }

  // The TF.js recognizer owns its own WebAudio microphone pipeline. The
  // existing Voice runner still calls this method for the old sherpa/Vosk
  // adapters, so keep it as an intentional no-op compatibility hook.
  acceptWaveform() {}

  async finalise() {
    try {
      await this.startPromise;
    } catch {
      return '';
    }
    if (!this.listening) return '';
    try {
      await this.model.recognizer.stopListening();
    } finally {
      this.listening = false;
    }
    return '';
  }

  remove() {
    if (!this.listening) return;
    this.model.recognizer.stopListening().catch((error) => {
      console.debug('Voice word detector cleanup failed.', error);
    });
    this.listening = false;
  }
}

export function releaseSixSevenVoiceModel() {
  loadedModel = null;
  modelPromise = null;
}
