import { installMp4Download } from './mp4_download.js';
import { MonotonicVoiceScorer } from './voice_engine.js';
import {
  SixSevenLocalRecognizer,
  loadSixSevenVoiceModel,
  releaseSixSevenVoiceModel,
} from './voice_vosk.js';

const app = document.getElementById('voice-app');
if (app) {
  const tr = (message) => typeof gettext === 'function' ? gettext(message) : message;
  const GAME_SECONDS = 20;
  const COUNTDOWN_STEP_MS = 1000;
  const GO_DISPLAY_MS = 250;
  const RECORDING_LEAD_SECONDS = 3 + GO_DISPLAY_MS / 1000;

  const video = document.getElementById('camera');
  const placeholder = document.getElementById('camera-placeholder');
  const countdownEl = document.getElementById('countdown');
  const livePill = document.getElementById('live-pill');
  const status = document.getElementById('voice-status');
  const errorEl = document.getElementById('voice-error');
  const scoreEl = document.getElementById('score');
  const timeEl = document.getElementById('counter-time');
  const heardFinal = document.getElementById('heard-final');
  const heardInterim = document.getElementById('heard-interim');
  const enableButton = document.getElementById('enable-voice');
  const startButton = document.getElementById('start-run');
  const resetButton = document.getElementById('reset-run');
  const resultCard = document.getElementById('voice-result');
  const resultScore = document.getElementById('result-score');
  const resultCopy = document.getElementById('result-copy');
  const shareText = document.getElementById('voice-share-text');
  const copyShareButton = document.getElementById('copy-voice-share');
  const copyShareStatus = document.getElementById('copy-voice-status');
  const recordingReview = document.getElementById('recording-review');
  const recordingPreview = document.getElementById('recording-preview');
  const recordingDownload = document.getElementById('download-recording');
  const submitButton = document.getElementById('submit-hof');
  const displayNameInput = document.getElementById('hof-display-name');
  const discardButton = document.getElementById('discard-recording');
  const uploadStatus = document.getElementById('upload-status');
  const publicationModal = document.getElementById('publication-modal');
  const publicationConsent = document.getElementById('publication-consent');
  const confirmPublication = document.getElementById('confirm-publication');
  const rivalVideo = document.getElementById('rival-video');
  const rivalScoreEl = document.getElementById('rival-score');
  const rivalTimelineNode = document.getElementById('rival-event-timeline');

  const rivalTimeline = rivalTimelineNode ? JSON.parse(rivalTimelineNode.textContent) : [];
  const rivalName = app.dataset.rivalName || '';
  const rivalFinalScore = Number(app.dataset.rivalScore || 0);

  let stream = null;
  let voiceModel = null;
  let modelLoadPromise = null;
  let localRecognizer = null;
  let audioContext = null;
  let microphoneSource = null;
  let recognizerNode = null;
  let silentGain = null;
  let feedRecognizer = false;

  let running = false;
  let countdownActive = false;
  let finalising = false;
  let runStartedAt = 0;
  let endTime = 0;
  let gameLoop = null;
  let score = 0;
  let eventTimeline = [];
  let rivalTimelineIndex = 0;
  let committedSegments = [];
  let partialSegment = '';
  const voiceScorer = new MonotonicVoiceScorer();

  let recorder = null;
  let recordingStream = null;
  let recordingCanvas = null;
  let recordingContext = null;
  let recordingFrame = null;
  let recordingChunks = [];
  let recordingBlob = null;
  let recordingUrl = null;

  function delay(milliseconds) {
    return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
  }

  function csrfToken() {
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function setStatus(message, state = '') {
    status.className = `detector-status ${state}`;
    status.querySelector('span:last-child').textContent = message;
  }

  function showError(message) {
    errorEl.textContent = message || '';
  }

  function updateRecognitionUI() {
    heardFinal.textContent = committedSegments.join(' ').trim() || '—';
    heardInterim.textContent = partialSegment ? `… ${partialSegment}` : '';
  }

  function lockScore(nextScore) {
    if (nextScore <= score) return;

    const elapsed = runStartedAt
      ? Math.min(GAME_SECONDS, Math.max(0, (performance.now() - runStartedAt) / 1000))
      : 0;
    while (eventTimeline.length < nextScore) {
      eventTimeline.push(Number(elapsed.toFixed(3)));
    }
    score = nextScore;
    scoreEl.textContent = String(score);
  }

  function handlePartial(text) {
    if (!running && !finalising) return;
    partialSegment = text || '';
    updateRecognitionUI();
    lockScore(voiceScorer.observePartial(partialSegment));
  }

  function handleResult(text) {
    if (!running && !finalising) return;
    if (text) committedSegments.push(text);
    partialSegment = '';
    updateRecognitionUI();
    lockScore(voiceScorer.commitFinal(text || ''));
  }

  async function ensureVoiceModel() {
    if (voiceModel?.ready) return voiceModel;
    if (!modelLoadPromise) {
      modelLoadPromise = loadSixSevenVoiceModel((message) => {
        if (!stream) setStatus(tr(message), 'busy');
      }).then((model) => {
        voiceModel = model;
        if (!stream) setStatus(tr('Local voice model ready — camera and microphone remain off'), 'ready');
        updateStartAvailability();
        return model;
      }).catch((error) => {
        modelLoadPromise = null;
        showError(`Local voice model: ${error.message}`);
        setStatus(tr('Local voice model failed to load'));
        throw error;
      });
    }
    return modelLoadPromise;
  }

  function updateStartAvailability() {
    const ready = Boolean(stream && voiceModel?.ready);
    startButton.hidden = !stream;
    startButton.disabled = !ready;
    startButton.textContent = ready ? tr("I'm ready") : tr('Loading local voice model…');
    if (stream && !voiceModel?.ready) {
      setStatus(tr('Camera and microphone ready — loading local voice model'), 'busy');
    } else if (ready && !running && !countdownActive) {
      setStatus(tr('Camera, microphone and local voice model ready'), 'ready');
    }
  }

  async function enableVoice() {
    showError('');
    enableButton.disabled = true;
    setStatus(tr('Requesting camera and microphone permission…'), 'busy');

    const modelPromise = ensureVoiceModel();
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          frameRate: { ideal: 30, max: 30 },
        },
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
        },
      });
      video.srcObject = stream;
      await video.play();
      placeholder.hidden = true;
      enableButton.hidden = true;
      updateStartAvailability();

      try {
        await modelPromise;
      } catch {
        // ensureVoiceModel already surfaced the useful error; camera/mic can stay enabled for retry.
      }
      updateStartAvailability();
    } catch (error) {
      enableButton.disabled = false;
      setStatus(tr('Camera or microphone unavailable'));
      showError(error.message || tr('Allow camera and microphone access, then try again.'));
    }
  }

  async function ensureAudioPipeline() {
    if (audioContext) {
      if (audioContext.state === 'suspended') await audioContext.resume();
      return;
    }
    const AudioContextCtor = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextCtor) throw new Error('This browser does not support Web Audio.');

    audioContext = new AudioContextCtor();
    microphoneSource = audioContext.createMediaStreamSource(stream);
    recognizerNode = audioContext.createScriptProcessor(2048, 1, 1);
    silentGain = audioContext.createGain();
    silentGain.gain.value = 0;

    recognizerNode.onaudioprocess = (event) => {
      if (!feedRecognizer || !localRecognizer) return;
      try {
        localRecognizer.acceptWaveform(event.inputBuffer);
      } catch (error) {
        showError(`Local voice recognition: ${error.message}`);
      }
    };

    microphoneSource.connect(recognizerNode);
    recognizerNode.connect(silentGain);
    silentGain.connect(audioContext.destination);
    if (audioContext.state === 'suspended') await audioContext.resume();
  }

  function createLocalRecognizer() {
    localRecognizer?.remove();
    localRecognizer = new SixSevenLocalRecognizer(voiceModel, audioContext.sampleRate, {
      onPartial: handlePartial,
      onResult: handleResult,
      onError(error) {
        showError(`Local voice recognition: ${error.message}`);
      },
    });
  }

  function preferredRecordingType() {
    if (!window.MediaRecorder) return '';
    const candidates = [
      'video/webm;codecs=vp8,opus',
      'video/webm',
      'video/mp4;codecs=avc1.42E01E,mp4a.40.2',
      'video/mp4',
    ];
    return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || '';
  }

  function drawRecordingHud() {
    if (!recordingCanvas || !recordingContext) return;
    const width = recordingCanvas.width;
    const height = recordingCanvas.height;
    const padding = Math.max(14, width * 0.026);
    const scoreSize = Math.max(34, width * 0.085);
    const labelSize = Math.max(12, width * 0.024);
    let time = '20.0';
    if (runStartedAt) time = Math.max(0, (endTime - performance.now()) / 1000).toFixed(1);

    recordingContext.save();
    recordingContext.fillStyle = 'rgba(15, 23, 42, .82)';
    recordingContext.fillRect(padding, padding, scoreSize * 2.25, scoreSize * 1.42);
    recordingContext.fillStyle = '#d8ff62';
    recordingContext.font = `900 ${scoreSize}px Inter, Arial, sans-serif`;
    recordingContext.textBaseline = 'top';
    recordingContext.fillText(String(score), padding * 1.55, padding * 1.15);
    recordingContext.fillStyle = '#ffffff';
    recordingContext.font = `800 ${labelSize}px Inter, Arial, sans-serif`;
    recordingContext.fillText('VOICE 67', padding * 1.55, padding * 1.15 + scoreSize);

    recordingContext.textAlign = 'right';
    recordingContext.fillStyle = 'rgba(15, 23, 42, .76)';
    recordingContext.fillRect(width - padding - scoreSize * 1.75, padding, scoreSize * 1.75, scoreSize * .72);
    recordingContext.fillStyle = '#ffffff';
    recordingContext.font = `850 ${scoreSize * .43}px ui-monospace, monospace`;
    recordingContext.fillText(`${time}s`, width - padding * 1.45, padding * 1.22);

    const countdown = countdownEl.textContent.trim();
    if (countdownActive && countdown) {
      recordingContext.textAlign = 'center';
      recordingContext.textBaseline = 'middle';
      recordingContext.fillStyle = 'rgba(15, 23, 42, .45)';
      recordingContext.fillRect(0, height * .31, width, height * .38);
      recordingContext.fillStyle = '#ffffff';
      recordingContext.font = `950 ${Math.max(80, height * .3)}px Inter, Arial, sans-serif`;
      recordingContext.fillText(countdown, width / 2, height / 2);
    }

    recordingContext.textAlign = 'left';
    recordingContext.textBaseline = 'alphabetic';
    recordingContext.fillStyle = 'rgba(15, 23, 42, .72)';
    recordingContext.fillRect(padding, height - padding - labelSize * 2.1, labelSize * 9.2, labelSize * 2.1);
    recordingContext.fillStyle = '#ffffff';
    recordingContext.font = `800 ${labelSize}px Inter, Arial, sans-serif`;
    recordingContext.fillText('icaijy.com', padding * 1.45, height - padding - labelSize * .55);
    recordingContext.restore();
  }

  function startRecording() {
    const type = preferredRecordingType();
    if (!type) throw new Error('This browser cannot record a compatible video with microphone audio.');

    recordingCanvas = document.createElement('canvas');
    recordingCanvas.width = video.videoWidth || 640;
    recordingCanvas.height = video.videoHeight || 480;
    recordingContext = recordingCanvas.getContext('2d');
    if (!recordingContext || !recordingCanvas.captureStream) {
      throw new Error('This browser cannot create a counted evidence recording.');
    }

    const drawFrame = () => {
      if (!recordingCanvas || !recordingContext) return;
      recordingContext.drawImage(video, 0, 0, recordingCanvas.width, recordingCanvas.height);
      drawRecordingHud();
      recordingFrame = requestAnimationFrame(drawFrame);
    };
    drawFrame();

    recordingStream = recordingCanvas.captureStream(30);
    const microphone = stream?.getAudioTracks()[0];
    if (!microphone) throw new Error('Microphone track disappeared before recording started.');
    recordingStream.addTrack(microphone.clone());

    recordingChunks = [];
    recorder = new MediaRecorder(recordingStream, {
      mimeType: type,
      videoBitsPerSecond: 1_600_000,
    });
    recorder.addEventListener('dataavailable', (event) => {
      if (event.data.size) recordingChunks.push(event.data);
    });
    recorder.start(500);
    livePill.hidden = false;
  }

  function stopRecordingPipeline() {
    if (recordingFrame !== null) cancelAnimationFrame(recordingFrame);
    recordingFrame = null;
    recordingStream?.getTracks().forEach((track) => track.stop());
    recordingStream = null;
    recordingContext = null;
    recordingCanvas = null;
  }

  function stopRecording() {
    return new Promise((resolve) => {
      if (!recorder || recorder.state === 'inactive') {
        recorder = null;
        recordingChunks = [];
        stopRecordingPipeline();
        livePill.hidden = true;
        resolve(null);
        return;
      }
      recorder.addEventListener('stop', () => {
        const baseType = (recorder.mimeType || recordingChunks[0]?.type || 'video/webm').split(';')[0];
        recordingBlob = new Blob(recordingChunks, { type: baseType });
        recorder = null;
        recordingChunks = [];
        stopRecordingPipeline();
        livePill.hidden = true;
        resolve(recordingBlob);
      }, { once: true });
      recorder.stop();
    });
  }

  function updateGameClock() {
    if (!running) return;
    const remaining = Math.max(0, (endTime - performance.now()) / 1000);
    timeEl.textContent = remaining.toFixed(1);

    if (rivalVideo) {
      const rivalGameTime = Math.max(0, rivalVideo.currentTime - RECORDING_LEAD_SECONDS);
      while (rivalTimelineIndex < rivalTimeline.length && rivalTimeline[rivalTimelineIndex] <= rivalGameTime) {
        rivalTimelineIndex += 1;
      }
      rivalScoreEl.textContent = String(rivalTimelineIndex);
    }

    if (remaining <= 0) {
      finishRun();
      return;
    }
    gameLoop = requestAnimationFrame(updateGameClock);
  }

  async function beginRun() {
    if (!stream || !voiceModel?.ready || running || countdownActive || finalising) return;
    showError('');
    resultCard.hidden = true;
    resetButton.hidden = true;
    startButton.hidden = true;
    score = 0;
    eventTimeline = [];
    committedSegments = [];
    partialSegment = '';
    voiceScorer.reset();
    runStartedAt = 0;
    endTime = 0;
    rivalTimelineIndex = 0;
    scoreEl.textContent = '0';
    timeEl.textContent = GAME_SECONDS.toFixed(1);
    updateRecognitionUI();
    if (rivalScoreEl) rivalScoreEl.textContent = '0';

    try {
      await ensureAudioPipeline();
      createLocalRecognizer();
      if (rivalVideo) {
        rivalVideo.muted = true;
        rivalVideo.currentTime = 0;
        await rivalVideo.play();
      }
      startRecording();
    } catch (error) {
      rivalVideo?.pause();
      showError(error.message);
      startButton.hidden = false;
      return;
    }

    countdownActive = true;
    setStatus(tr('Evidence recording started — wait for GO'), 'busy');
    for (const value of ['3', '2', '1']) {
      countdownEl.textContent = value;
      await delay(COUNTDOWN_STEP_MS);
    }
    countdownEl.textContent = 'GO';
    await delay(GO_DISPLAY_MS);
    countdownEl.textContent = '';
    countdownActive = false;

    running = true;
    feedRecognizer = true;
    runStartedAt = performance.now();
    endTime = runStartedAt + GAME_SECONDS * 1000;
    if (rivalVideo && Math.abs(rivalVideo.currentTime - RECORDING_LEAD_SECONDS) > 0.35) {
      rivalVideo.currentTime = RECORDING_LEAD_SECONDS;
    }
    setStatus(tr('Listening locally — clear 67s lock in immediately'), 'ready');
    gameLoop = requestAnimationFrame(updateGameClock);
  }

  async function finishRun() {
    if (!running) return;
    running = false;
    feedRecognizer = false;
    finalising = true;
    cancelAnimationFrame(gameLoop);
    timeEl.textContent = '0.0';
    rivalVideo?.pause();
    if (rivalScoreEl) rivalScoreEl.textContent = String(rivalFinalScore);
    setStatus(tr('Time — locking the last local model result…'), 'busy');

    // Stop evidence at the deadline. The worker may take a moment to flush
    // already-received audio, but no post-deadline microphone samples are fed.
    const recordingPromise = stopRecording();
    const finalResultPromise = localRecognizer?.finalise(1500) || Promise.resolve('');
    const [blob] = await Promise.all([recordingPromise, finalResultPromise]);

    // If the worker timed out without a final event, lock the best complete
    // pair count already seen in the last partial. Awarded points never roll back.
    lockScore(voiceScorer.commitFinal(''));
    finalising = false;
    localRecognizer?.remove();
    localRecognizer = null;

    setStatus(tr('Run complete — awarded voice points are locked'), 'ready');
    resultScore.textContent = String(score);
    resultCopy.textContent = rivalName
      ? score > rivalFinalScore
        ? `You beat ${rivalName} by ${score - rivalFinalScore}.`
        : score === rivalFinalScore
          ? `You tied ${rivalName}.`
          : `${rivalName} is ahead by ${rivalFinalScore - score}.`
      : `Counted ${score} six sevens.`;
    shareText.value = shareableResult();
    copyShareStatus.textContent = '';
    resultCard.hidden = false;
    recordingReview.hidden = false;

    if (blob) {
      if (recordingUrl) URL.revokeObjectURL(recordingUrl);
      recordingUrl = URL.createObjectURL(blob);
      recordingPreview.src = recordingUrl;
      recordingDownload.href = recordingUrl;
      const extension = blob.type === 'video/mp4' ? 'mp4' : 'webm';
      recordingDownload.download = `six-seven-voice-counted.${extension}`;
      recordingDownload.hidden = false;
    }

    resetButton.hidden = false;
    resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function shareableResult() {
    const blocks = score > 0
      ? `${'🟩'.repeat(Math.min(score, 67))}${score > 67 ? ` +${score - 67}` : ''}`
      : '⬜';
    const gameUrl = new URL(app.dataset.gameUrl, window.location.origin);
    const rival = rivalName ? ` · 🆚 ${rivalName} ${rivalFinalScore}` : '';
    return `Six Seven Voice Speedrun — ${score} clear 67s${rival}\n${blocks}\n${gameUrl.href}`;
  }

  async function copyShareResult() {
    if (!shareText.value) return;
    try {
      if (navigator.clipboard?.writeText && window.isSecureContext) {
        await navigator.clipboard.writeText(shareText.value);
      } else {
        shareText.select();
        shareText.setSelectionRange(0, shareText.value.length);
        if (!document.execCommand('copy')) throw new Error('Copy command was rejected.');
      }
      copyShareButton.textContent = tr('Copied! 🎉');
      copyShareStatus.textContent = tr('Result copied.');
    } catch {
      copyShareStatus.textContent = tr('Automatic copy failed. Select the text and copy it manually.');
    }
    window.setTimeout(() => { copyShareButton.textContent = tr('Copy to clipboard'); }, 1500);
  }

  function discardRecording() {
    if (recordingUrl) URL.revokeObjectURL(recordingUrl);
    recordingUrl = null;
    recordingBlob = null;
    recordingPreview.removeAttribute('src');
    recordingPreview.load();
    recordingDownload.removeAttribute('href');
    recordingDownload.hidden = true;
    recordingReview.hidden = true;
    if (uploadStatus) uploadStatus.textContent = tr('Recording discarded. Nothing was uploaded.');
  }

  function resetRun() {
    discardRecording();
    feedRecognizer = false;
    localRecognizer?.remove();
    localRecognizer = null;
    running = false;
    countdownActive = false;
    finalising = false;
    score = 0;
    eventTimeline = [];
    committedSegments = [];
    partialSegment = '';
    voiceScorer.reset();
    runStartedAt = 0;
    endTime = 0;
    rivalTimelineIndex = 0;
    scoreEl.textContent = '0';
    timeEl.textContent = GAME_SECONDS.toFixed(1);
    updateRecognitionUI();
    if (rivalScoreEl) rivalScoreEl.textContent = '0';
    if (rivalVideo) {
      rivalVideo.pause();
      if (rivalVideo.readyState) rivalVideo.currentTime = 0;
    }
    resultCard.hidden = true;
    shareText.value = '';
    copyShareStatus.textContent = '';
    resetButton.hidden = true;
    updateStartAvailability();
    showError('');
  }

  function openPublicationModal() {
    if (!publicationModal) return;
    publicationModal.hidden = false;
    publicationConsent.checked = false;
    confirmPublication.disabled = true;
  }

  function closePublicationModal() {
    if (publicationModal) publicationModal.hidden = true;
  }

  async function submitRecording() {
    if (!recordingBlob || !submitButton) return;
    if (!publicationConsent?.checked) {
      openPublicationModal();
      return;
    }

    const maxBytes = Number(app.dataset.maxUploadMb) * 1024 * 1024;
    if (recordingBlob.size > maxBytes) {
      uploadStatus.textContent = `Recording exceeded the ${app.dataset.maxUploadMb} MB upload limit.`;
      return;
    }

    const turnstileResponse = document.querySelector('[name="cf-turnstile-response"]')?.value || '';
    const extension = recordingBlob.type === 'video/mp4' ? 'mp4' : 'webm';
    const form = new FormData();
    form.append('game_mode', 'voice_67');
    form.append('score', String(score));
    form.append('event_timeline', JSON.stringify(eventTimeline));
    form.append('publication_consent', 'yes');
    form.append('video', recordingBlob, `six-seven-voice.${extension}`);
    if (displayNameInput) form.append('display_name', displayNameInput.value);
    if (turnstileResponse) form.append('cf-turnstile-response', turnstileResponse);

    submitButton.disabled = true;
    uploadStatus.textContent = tr('Uploading video…');
    try {
      const response = await fetch(app.dataset.submitUrl, {
        method: 'POST',
        body: form,
        headers: { 'X-CSRFToken': csrfToken() },
        credentials: 'same-origin',
      });
      const rawResponse = await response.text();
      let payload;
      try {
        payload = JSON.parse(rawResponse);
      } catch {
        throw new Error(`The server returned HTTP ${response.status} instead of JSON.`);
      }
      if (!response.ok) throw new Error(payload.error || 'Upload failed.');
      uploadStatus.textContent = payload.message;
      submitButton.hidden = true;
      if (discardButton) discardButton.hidden = true;
      window.setTimeout(() => {
        window.location.href = payload.entry_url || app.dataset.hallUrl;
      }, 900);
    } catch (error) {
      uploadStatus.textContent = error.message;
      submitButton.disabled = false;
    }
  }

  installMp4Download(recordingDownload, {
    filename: 'six-seven-voice-counted.webm',
    onError(error) {
      showError(`MP4 download failed: ${error.message}`);
    },
  });

  enableButton.addEventListener('click', enableVoice);
  startButton.addEventListener('click', beginRun);
  resetButton.addEventListener('click', resetRun);
  copyShareButton.addEventListener('click', copyShareResult);
  submitButton?.addEventListener('click', () => {
    if (publicationConsent?.checked) submitRecording();
    else openPublicationModal();
  });
  discardButton?.addEventListener('click', discardRecording);
  publicationConsent?.addEventListener('change', () => {
    confirmPublication.disabled = !publicationConsent.checked;
  });
  confirmPublication?.addEventListener('click', async () => {
    if (!publicationConsent.checked) return;
    closePublicationModal();
    await submitRecording();
  });
  document.querySelectorAll('[data-close-publication-modal]').forEach((node) => {
    node.addEventListener('click', closePublicationModal);
  });

  window.addEventListener('pagehide', () => {
    feedRecognizer = false;
    localRecognizer?.remove();
    stream?.getTracks().forEach((track) => track.stop());
    try {
      recognizerNode?.disconnect();
      microphoneSource?.disconnect();
      silentGain?.disconnect();
      audioContext?.close();
    } catch (error) {
      console.debug('Voice audio cleanup failed.', error);
    }
    releaseSixSevenVoiceModel();
  }, { once: true });

  setStatus(tr('Preloading local voice model — camera and microphone remain off'), 'busy');
  ensureVoiceModel().catch(() => {});
}
