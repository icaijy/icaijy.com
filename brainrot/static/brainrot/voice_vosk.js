// Compatibility facade: the Voice runner already imports this module name.
// The implementation is now dedicated streaming keyword spotting, not Vosk ASR.
export {
  SixSevenLocalRecognizer,
  loadSixSevenVoiceModel,
  releaseSixSevenVoiceModel,
} from './voice_kws.js';
