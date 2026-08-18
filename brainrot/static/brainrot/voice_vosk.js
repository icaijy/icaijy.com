// Compatibility facade for voice_counter.js. Voice scoring now uses the
// TensorFlow.js Speech Commands word classifier rather than transcript ASR or
// whole-phrase wake-word spotting.
export {
  SixSevenLocalRecognizer,
  loadSixSevenVoiceModel,
  releaseSixSevenVoiceModel,
} from './voice_words.js';
