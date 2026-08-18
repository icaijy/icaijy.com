import { installMp4Download } from './mp4_download.js';
import { countSixSevenPhrases } from './voice_engine.js';

const app = document.getElementById('voice-app');
if (app) {
  const tr = (message) => typeof gettext === 'function' ? gettext(message) : message;
  const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition || null;
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
  let running = false;
  let countdownActive = false;
  let finalisingRecognition = false;
  let runStartedAt = 0;
  let endTime = 0;
  let gameLoop = null;
  let score = 0;
  let eventTimeline = [];
  let rivalTimelineIndex = 0;

  let recognition = null;
  let recognitionActive = false;
  let recognitionStopping = false;
  let recognitionStopResolve = null;
  let recognitionStopTimer = null;
  let completedTranscript = [];
  let sessionFinalTranscript = '';
  let sessionInterimTranscript = '';

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

  function officialTranscript() {
    return [...completedTranscript, sessionFinalTranscript].filter(Boolean).join(' ').trim();
  }

  function updateTranscriptUI() {
    const finalText = officialTranscript();
    heardFinal.textContent = finalText || '—';
    heardInterim.textContent = sessionInterimTranscript ? `… ${sessionInterimTranscript}` : '';
  }

  function syncOfficialScore() {
    const nextScore = countSixSevenPhrases(officialTranscript());
    if (nextScore > score) {
      const elapsed = runStartedAt
        ? Math.min(GAME_SECONDS, Math.max(0, (performance.now() - runStartedAt) / 1000))
        : 0;
      while (eventTimeline.length < nextScore) {
        eventTimeline.push(Number(elapsed.toFixed(3)));
      }
    }
    score = nextScore;
    scoreEl.textContent = String(score);
  }

  function commitRecognitionSession() {
    if (sessionFinalTranscript.trim()) completedTranscript.push(sessionFinalTranscript.trim());
    sessionFinalTranscript = '';
    sessionInterimTranscript = '';
    updateTranscriptUI();
    syncOfficialScore();
  }

  function createRecognition() {
    const instance = new SpeechRecognitionCtor();
    instance.lang = 'en-AU';
    instance.continuous = true;
    instance.interimResults = true;
    instance.maxAlternatives = 1;

    // Newer implementations can bias the recogniser toward the literal phrase.
    // This is optional; scoring never depends on this experimental API existing.
    if ('phrases' in instance && window.SpeechRecognitionPhrase) {
      try {
        instance.phrases = [new window.SpeechRecognitionPhrase('six seven', 6)];
      } catch (error) {
        console.debug('Speech phrase bias is unavailable.', error);
      }
    }

    instance.addEventListener('start', () => {
      recognitionActive = true;
      if (running) setStatus(tr('Listening — say six seven'), 'ready');
    });

    instance.addEventListener('result', (event) => {
      let finalText = '';
      let interimText = '';
      for (let index = 0; index < event.results.length; index += 1) {
        const result = event.results[index];
        const transcript = result[0]?.transcript?.trim() || '';
        if (!transcript) continue;
        if (result.isFinal) finalText += `${transcript} `;
        else interimText += `${transcript} `;
      }
      sessionFinalTranscript = finalText.trim();
      sessionInterimTranscript = interimText.trim();
      updateTranscriptUI();
      if (running || finalisingRecognition) syncOfficialScore();
    });

    instance.addEventListener('error', (event) => {
      if (event.error === 'aborted' && recognitionStopping) return;
      if (event.error === 'no-speech') {
        if (running) setStatus(tr('Still listening — speak clearly'), 'busy');
        return;
      }
      showError(`Speech recognition: ${event.error || 'unknown error'}`);
    });

    instance.addEventListener('end', () => {
      recognitionActive = false;
      commitRecognitionSession();

      if (recognitionStopping) {
        recognitionStopping = false;
        if (recognitionStopTimer) window.clearTimeout(recognitionStopTimer);
        recognitionStopTimer = null;
        const resolve = recognitionStopResolve;
        recognitionStopResolve = null;
        resolve?.();
        return;
      }

      if (running && performance.now() < endTime) {
        window.setTimeout(() => {
          if (running && !recognitionActive && !recognitionStopping) startRecognitionSession();
        }, 60);
      }
    });

    return instance;
  }

  function startRecognitionSession() {
    if (!SpeechRecognitionCtor || recognitionActive || recognitionStopping || !running) return;
    recognition = createRecognition();
    sessionFinalTranscript = '';
    sessionInterimTranscript = '';
    try {
      recognition.start();
    } catch (error) {
      showError(`Could not start speech recognition: ${error.message}`);
    }
  }

  function stopRecognition() {
    finalisingRecognition = true;
    return new Promise((resolve) => {
      if (!recognition || !recognitionActive) {
        commitRecognitionSession();
        finalisingRecognition = false;
        resolve();
        return;
      }

      recognitionStopping = true;
      recognitionStopResolve = () => {
        finalisingRecognition = false;
        resolve();
      };
      try {
        recognition.stop();
      } catch (error) {
        console.warn('Speech recognition stop failed.', error);
        recognitionStopping = false;
        commitRecognitionSession();
        recognitionStopResolve = null;
        finalisingRecognition = false;
        resolve();
        return;
      }

      recognitionStopTimer = window.setTimeout(() => {
        try { recognition?.abort(); } catch (error) { console.debug(error); }
        recognitionActive = false;
        recognitionStopping = false;
        commitRecognitionSession();
        const finish = recognitionStopResolve;
        recognitionStopResolve = null;
        recognitionStopTimer = null;
        finalisingRecognition = false;
        finish?.();
      }, 2500);
    });
  }

  async function enableVoice() {
    showError('');
    if (!SpeechRecognitionCtor) {
      showError(tr('This browser does not expose SpeechRecognition. Try a current browser with Web Speech recognition support.'));
      return;
    }

    enableButton.disabled = true;
    setStatus(tr('Requesting camera and microphone permission…'), 'busy');
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 30, max: 30 } },
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      video.srcObject = stream;
      await video.play();
      placeholder.hidden = true;
      enableButton.hidden = true;
      startButton.hidden = false;
      startButton.disabled = false;
      startButton.textContent = tr("I'm ready");
      setStatus(tr('Camera, microphone and recogniser ready'), 'ready');
    } catch (error) {
      enableButton.disabled = false;
      setStatus(tr('Camera or microphone unavailable'));
      showError(error.message || tr('Allow camera and microphone access, then try again.'));
    }
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
    recorder = new MediaRecorder(recordingStream, { mimeType: type, videoBitsPerSecond: 1_600_000 });
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
    if (!stream || running || countdownActive) return;
    showError('');
    resultCard.hidden = true;
    resetButton.hidden = true;
    startButton.hidden = true;
    score = 0;
    eventTimeline = [];
    completedTranscript = [];
    sessionFinalTranscript = '';
    sessionInterimTranscript = '';
    runStartedAt = 0;
    endTime = 0;
    rivalTimelineIndex = 0;
    scoreEl.textContent = '0';
    timeEl.textContent = GAME_SECONDS.toFixed(1);
    updateTranscriptUI();
    if (rivalScoreEl) rivalScoreEl.textContent = '0';

    try {
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
    runStartedAt = performance.now();
    endTime = runStartedAt + GAME_SECONDS * 1000;
    if (rivalVideo && Math.abs(rivalVideo.currentTime - RECORDING_LEAD_SECONDS) > 0.35) {
      rivalVideo.currentTime = RECORDING_LEAD_SECONDS;
    }
    startRecognitionSession();
    setStatus(tr('Listening — say six seven'), 'ready');
    gameLoop = requestAnimationFrame(updateGameClock);
  }

  async function finishRun() {
    if (!running) return;
    running = false;
    cancelAnimationFrame(gameLoop);
    timeEl.textContent = '0.0';
    rivalVideo?.pause();
    if (rivalScoreEl) rivalScoreEl.textContent = String(rivalFinalScore);
    setStatus(tr('Time — finalising the recogniser…'), 'busy');

    await stopRecognition();
    syncOfficialScore();
    const blob = await stopRecording();

    setStatus(tr('Run complete — final recognitions locked'), 'ready');
    resultScore.textContent = String(score);
    resultCopy.textContent = rivalName
      ? score > rivalFinalScore
        ? `You beat ${rivalName} by ${score - rivalFinalScore}.`
        : score === rivalFinalScore
          ? `You tied ${rivalName}.`
          : `${rivalName} is ahead by ${rivalFinalScore - score}.`
      : `Counted ${score} clear six sevens.`;
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
    } catch (error) {
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
    try { recognition?.abort(); } catch (error) { console.debug(error); }
    recognition = null;
    recognitionActive = false;
    recognitionStopping = false;
    finalisingRecognition = false;
    score = 0;
    eventTimeline = [];
    completedTranscript = [];
    sessionFinalTranscript = '';
    sessionInterimTranscript = '';
    runStartedAt = 0;
    endTime = 0;
    rivalTimelineIndex = 0;
    scoreEl.textContent = '0';
    timeEl.textContent = GAME_SECONDS.toFixed(1);
    updateTranscriptUI();
    if (rivalScoreEl) rivalScoreEl.textContent = '0';
    if (rivalVideo) {
      rivalVideo.pause();
      if (rivalVideo.readyState) rivalVideo.currentTime = 0;
    }
    resultCard.hidden = true;
    shareText.value = '';
    copyShareStatus.textContent = '';
    resetButton.hidden = true;
    startButton.hidden = false;
    startButton.disabled = !stream;
    showError('');
    setStatus(tr('Ready for another voice run'), 'ready');
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
      window.setTimeout(() => { window.location.href = payload.entry_url || app.dataset.hallUrl; }, 900);
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

  if (!SpeechRecognitionCtor) {
    enableButton.disabled = true;
    setStatus(tr('Speech recognition is unavailable in this browser'));
    showError(tr('This browser does not expose SpeechRecognition. Use a supported browser for Voice Speedrun.'));
  } else {
    setStatus(tr('Ready to request camera and microphone'), 'ready');
  }

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
}
