import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const source = await readFile(
  new URL('../static/brainrot/voice_kws.js', import.meta.url),
  'utf8',
);
const {
  SixSevenLocalRecognizer,
  buildSixSevenKeywords,
  enumerateBpeWordPaths,
} = await import(
  `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`
);

function makeFakeModel() {
  const queue = [];
  const stream = {
    handle: 1,
    accepted: [],
    finished: false,
    freed: false,
    acceptWaveform(sampleRate, samples) {
      this.accepted.push({ sampleRate, samples: Array.from(samples) });
    },
    inputFinished() {
      this.finished = true;
    },
    free() {
      this.freed = true;
      this.handle = 0;
    },
  };
  const spotter = {
    queue,
    resets: 0,
    createStream() {
      return stream;
    },
    isReady() {
      return queue.length > 0;
    },
    decode() {},
    getResult() {
      return queue.shift();
    },
    reset() {
      this.resets += 1;
    },
  };
  return { model: { ready: true, spotter }, spotter, stream };
}

function fakeAudioBuffer(sampleRate = 48000) {
  const samples = new Float32Array([0.1, -0.2, 0.3]);
  return {
    numberOfChannels: 1,
    sampleRate,
    getChannelData(channel) {
      assert.equal(channel, 0);
      return samples;
    },
  };
}

test('whole-word BPE pieces create the simple SIX SEVEN keyword path', () => {
  const tokens = {
    '<blank>': 0,
    '<unk>': 1,
    '▁SIX': 2,
    '▁SEVEN': 3,
  };

  assert.deepEqual(enumerateBpeWordPaths('SIX', tokens), [['▁SIX']]);
  assert.deepEqual(enumerateBpeWordPaths('SEVEN', tokens), [['▁SEVEN']]);
  assert.equal(buildSixSevenKeywords(tokens), '▁SIX ▁SEVEN @SIX_SEVEN');
});

test('SEVEN may be split across BPE pieces without blocking model startup', () => {
  const tokens = {
    '<blank>': 0,
    '<unk>': 1,
    '▁SIX': 2,
    '▁SE': 3,
    'V': 4,
    'EN': 5,
    'E': 6,
    'N': 7,
  };

  const sevenPaths = enumerateBpeWordPaths('SEVEN', tokens);
  assert.ok(sevenPaths.some((path) => path.join(' ') === '▁SE V EN'));
  assert.ok(sevenPaths.some((path) => path.join(' ') === '▁SE V E N'));

  const keywords = buildSixSevenKeywords(tokens).split('\n');
  assert.ok(keywords.includes('▁SIX ▁SE V EN @SIX_SEVEN'));
  assert.ok(keywords.includes('▁SIX ▁SE V E N @SIX_SEVEN'));
});

test('keyword generation fails clearly only when the vocabulary truly cannot spell a word', () => {
  assert.throws(
    () => buildSixSevenKeywords({ '▁SIX': 1, '▁SE': 2 }),
    /cannot tokenise: SEVEN/,
  );
});

test('one keyword hit fires one score event and immediately resets the stream', () => {
  const { model, spotter, stream } = makeFakeModel();
  const hits = [];
  const recognizer = new SixSevenLocalRecognizer(model, 48000, {
    onResult(text, result) {
      hits.push({ text, keyword: result.keyword });
    },
  });

  spotter.queue.push({ keyword: 'SIX_SEVEN' });
  recognizer.acceptWaveform(fakeAudioBuffer());

  assert.deepEqual(hits, [{ text: 'six seven', keyword: 'SIX_SEVEN' }]);
  assert.equal(spotter.resets, 1);
  assert.equal(stream.accepted.length, 1);
  assert.equal(stream.accepted[0].sampleRate, 48000);
});

test('empty decoder results never manufacture a score', () => {
  const { model, spotter } = makeFakeModel();
  let hits = 0;
  const recognizer = new SixSevenLocalRecognizer(model, 48000, {
    onResult() { hits += 1; },
  });

  spotter.queue.push({ keyword: '' }, {});
  recognizer.acceptWaveform(fakeAudioBuffer());

  assert.equal(hits, 0);
  assert.equal(spotter.resets, 0);
});

test('deadline finalisation keeps the live input rate and may flush a pending hit', async () => {
  const { model, spotter, stream } = makeFakeModel();
  let hits = 0;
  const recognizer = new SixSevenLocalRecognizer(model, 48000, {
    onResult() { hits += 1; },
  });

  spotter.queue.push({ keyword: 'SIX_SEVEN' });
  await recognizer.finalise();

  assert.equal(hits, 1);
  assert.equal(stream.finished, true);
  assert.equal(stream.accepted.length, 1);
  assert.equal(stream.accepted[0].sampleRate, 48000);
  assert.equal(stream.accepted[0].samples.length, 21600);
});

test('remove frees only the per-run stream', () => {
  const { model, stream } = makeFakeModel();
  const recognizer = new SixSevenLocalRecognizer(model, 48000);
  recognizer.remove();
  assert.equal(stream.freed, true);
});
