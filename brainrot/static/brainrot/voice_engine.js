export function normaliseVoiceTranscript(value) {
  return String(value ?? '')
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim();
}

export function countSixSevenPhrases(value) {
  const normalised = normaliseVoiceTranscript(value);
  if (!normalised) return 0;

  const tokens = normalised.split(/\s+/);
  let count = 0;
  for (let index = 0; index < tokens.length; index += 1) {
    const token = tokens[index];

    // Some recognisers normalise the spoken pair "six seven" to the number 67.
    // Treat one standalone 67 token as one pair, but do not accept fuzzy words
    // such as "sixty seven" or a fused "sixseven" token.
    if (token === '67') {
      count += 1;
      continue;
    }

    const isSix = token === 'six' || token === '6';
    const next = tokens[index + 1];
    const isSeven = next === 'seven' || next === '7';
    if (isSix && isSeven) {
      count += 1;
      index += 1;
    }
  }
  return count;
}
