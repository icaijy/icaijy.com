import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

const source = await readFile(
  new URL('../static/brainrot/voice_kws.js', import.meta.url),
  'utf8',
);
const { SixSevenLocalRecognizer } = await import(
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

test('deadline finalisation adds only synthetic silence and may flush a pending hit', async () => {
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
  assert.equal(stream.accepted[0].sampleRate, 16000);
  assert.equal(stream.accepted[0].samples.length, 7200);
});

test('remove frees only the per-run stream', () => {
  const { model, stream } = makeFakeModel();
  const recognizer = new SixSevenLocalRecognizer(model, 48000);
  recognizer.remove();
  assert.equal(stream.freed, true);
});
