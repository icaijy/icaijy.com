export function normaliseVoiceTranscript(value) {
  return String(value ?? '')
    .toLowerCase()
    .replace(/\[unk\]/g, ' [unk] ')
    .replace(/[^\p{L}\[\]]+/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export function countSixSevenPhrases(value) {
  const normalised = normaliseVoiceTranscript(value);
  if (!normalised) return 0;

  const tokens = normalised.split(/\s+/);
  let count = 0;
  for (let index = 0; index + 1 < tokens.length; index += 1) {
    if (tokens[index] === 'six' && tokens[index + 1] === 'seven') {
      count += 1;
      index += 1;
    }
  }
  return count;
}
