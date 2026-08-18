// Compatibility facade: voice_counter.js already imports this module name.
// The implementation is dedicated streaming keyword spotting, not Vosk ASR.
export {
  SixSevenLocalRecognizer,
  loadSixSevenVoiceModel,
  releaseSixSevenVoiceModel,
} from './voice_kws.js';
