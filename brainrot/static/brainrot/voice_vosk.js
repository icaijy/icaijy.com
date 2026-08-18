// Compatibility shim for the existing Voice runner. The implementation moved
// from general-purpose Vosk ASR to a dedicated sherpa-onnx keyword spotter.
export {
  SixSevenLocalRecognizer,
  loadSixSevenVoiceModel,
  releaseSixSevenVoiceModel,
} from './voice_kws.js';
