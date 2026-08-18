const VOSK_SCRIPT_URL = 'https://cdn.jsdelivr.net/npm/vosk-browser@0.0.8/dist/vosk.js';
const VOSK_MODEL_URL = 'https://fiddle-app.github.io/voice-models/vosk-model-small-en-us-0.15.tar.gz';
const SIX_SEVEN_GRAMMAR = JSON.stringify(['six', 'seven', '[unk]']);

let scriptPromise = null;
let modelPromise = null;
let loadedModel = null;

function loadScript(url) {
  if (window.Vosk?.createModel) return Promise.resolve();
  if (scriptPromise) return scriptPromise;

  scriptPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[data-voice-vosk="${url}"]`);
    if (existing) {
      existing.addEventListener('load', resolve, { once: true });
      existing.addEventListener('error', () => reject(new Error('Could not load the local voice runtime.')), { once: true });
      return;
    }

    const script = document.createElement('script');
    script.src = url;
    script.async = true;
    script.crossOrigin = 'anonymous';
    script.dataset.voiceVosk = url;
    script.addEventListener('load', resolve, { once: true });
    script.addEventListener('error', () => reject(new Error('Could not load the local voice runtime.')), { once: true });
    document.head.appendChild(script);
  }).then(() => {
    if (!window.Vosk?.createModel) throw new Error('The local voice runtime loaded without the Vosk API.');
  }).catch((error) => {
    scriptPromise = null;
    throw error;
  });

  return scriptPromise;
}

export async function loadSixSevenVoiceModel(onStatus = () => {}) {
  if (loadedModel?.ready) return loadedModel;
  if (!modelPromise) {
    modelPromise = (async () => {
      onStatus('Loading local voice runtime…');
      await loadScript(VOSK_SCRIPT_URL);
      onStatus('Loading local English voice model (~40 MB on first visit)…');
      const model = await window.Vosk.createModel(VOSK_MODEL_URL);
      if (!model?.ready) throw new Error('The local voice model did not become ready.');
      loadedModel = model;
      onStatus('Local voice model ready');
      return model;
    })().catch((error) => {
      modelPromise = null;
      throw error;
    });
  }
  return modelPromise;
}

export class SixSevenLocalRecognizer {
  constructor(model, sampleRate, handlers = {}) {
    this.handlers = handlers;
    this.lastPartial = '';
    this.finalising = null;
    this.recognizer = new model.KaldiRecognizer(sampleRate, SIX_SEVEN_GRAMMAR);
    this.recognizer.setWords(true);

    this.recognizer.on('partialresult', (message) => {
      this.lastPartial = message?.result?.partial?.trim() || '';
      this.handlers.onPartial?.(this.lastPartial);
    });

    this.recognizer.on('result', (message) => {
      const text = message?.result?.text?.trim() || '';
      this.lastPartial = '';
      this.handlers.onResult?.(text, message?.result?.result || []);
      if (this.finalising) {
        const resolve = this.finalising;
        this.finalising = null;
        resolve(text);
      }
    });

    this.recognizer.on('error', (message) => {
      const error = new Error(message?.error || 'Local voice recognition failed.');
      this.handlers.onError?.(error);
      if (this.finalising) {
        const resolve = this.finalising;
        this.finalising = null;
        resolve('');
      }
    });
  }

  acceptWaveform(audioBuffer) {
    this.recognizer.acceptWaveform(audioBuffer);
  }

  finalise(timeoutMs = 1500) {
    if (this.finalising) return Promise.resolve('');

    return new Promise((resolve) => {
      let settled = false;
      const finish = (text = '') => {
        if (settled) return;
        settled = true;
        window.clearTimeout(timer);
        if (this.finalising === finish) this.finalising = null;
        resolve(text);
      };
      this.finalising = finish;

      const timer = window.setTimeout(() => finish(''), timeoutMs);
      try {
        this.recognizer.retrieveFinalResult();
      } catch (error) {
        this.handlers.onError?.(error);
        finish('');
      }
    });
  }

  remove() {
    try {
      this.recognizer?.remove();
    } finally {
      this.recognizer = null;
      this.finalising = null;
    }
  }
}

export function releaseSixSevenVoiceModel() {
  if (loadedModel) {
    try {
      loadedModel.terminate();
    } catch (error) {
      console.debug('Vosk model cleanup failed.', error);
    }
  }
  loadedModel = null;
  modelPromise = null;
}
