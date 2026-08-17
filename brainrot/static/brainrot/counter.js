import {
  GAME_MODES,
  OVERLAY_GEOMETRY,
  createGestureTracker,
  landmarksAreVisible,
} from './gesture_engine.js?v=20260817.2';

const app = document.getElementById('counter-app');
if (app) {
  const tr = (message) => typeof gettext === 'function' ? gettext(message) : message;
  const fmt = (message, values) => typeof interpolate === 'function'
    ? interpolate(tr(message), values, true)
    : Object.entries(values).reduce((text, [key, value]) => text.replaceAll(`%(${key})s`, value), message);
  const video = document.getElementById('camera');
  const canvas = document.getElementById('pose-overlay');
  const context = canvas.getContext('2d');
  const placeholder = document.getElementById('camera-placeholder');
  const status = document.getElementById('detector-status');
  const scoreEl = document.getElementById('score');
  const timeEl = document.getElementById('counter-time');
  const countdownEl = document.getElementById('countdown');
  const livePill = document.getElementById('live-pill');
  const enableButton = document.getElementById('enable-camera');
  const startButton = document.getElementById('start-run');
  const resetButton = document.getElementById('reset-run');
  const errorEl = document.getElementById('counter-error');
  const resultCard = document.getElementById('counter-result');
  const resultScore = document.getElementById('result-score');
  const resultCopy = document.getElementById('result-copy');
  const shareText = document.getElementById('counter-share-text');
  const copyShareButton = document.getElementById('copy-counter-share');
  const copyShareStatus = document.getElementById('copy-counter-status');
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
  const counterTitle = document.getElementById('counter-title');
  const counterDescription = document.getElementById('counter-description');
  const scoreLabel = document.getElementById('score-label');
  const resultUnit = document.getElementById('result-unit');
  const placeholderMark = document.getElementById('counter-placeholder-mark');
  const hallMark = document.getElementById('counter-hof-mark');
  const hallPortal = document.getElementById('counter-hof-portal');
  const modeButtons = [...document.querySelectorAll('[data-counter-mode]')];

  const GAME_SECONDS = 20;
  const COUNTDOWN_STEP_MS = 1000;
  const GO_DISPLAY_MS = 250;
  const RECORDING_LEAD_SECONDS = 3 + GO_DISPLAY_MS / 1000;
  const READY_LABEL = tr("I'm ready — record locally");
  const MODEL_URL = 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task';
  const rivalTimeline = rivalTimelineNode ? JSON.parse(rivalTimelineNode.textContent) : [];
  const rivalName = app.dataset.rivalName || '';
  const rivalFinalScore = Number(app.dataset.rivalScore || 0);
  let currentMode = Object.values(GAME_MODES).includes(app.dataset.gameMode)
    ? app.dataset.gameMode
    : GAME_MODES.SIX_SEVEN;
  let gestureTracker = createGestureTracker(currentMode);
  let activeModeConfig = null;
  let stream = null;
  let landmarker = null;
  let runtimePromise = null;
  let detectorLoop = null;
  let gameLoop = null;
  let lastVideoTime = -1;
  let poseReady = false;
  let readyFrames = 0;
  let running = false;
  let armed = false;
  let countdownActive = false;
  let endTime = 0;
  let score = 0;
  let eventTimeline = [];
  let runStartedAt = 0;
  let rivalTimelineIndex = 0;
  let rivalReady = !rivalVideo;
  let recorder = null;
  let recordingStream = null;
  let recordingCanvas = null;
  let recordingContext = null;
  let recordingFrame = null;
  let recordingChunks = [];
  let recordingBlob = null;
  let recordingUrl = null;

  async function loadMediaPipe() {
    const sources = [
      {
        module: 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/vision_bundle.mjs',
        wasm: 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm',
      },
      {
        module: 'https://unpkg.com/@mediapipe/tasks-vision@1.0.1/vision_bundle.mjs',
        wasm: 'https://unpkg.com/@mediapipe/tasks-vision@1.0.1/wasm',
      },
    ];
    let lastError = null;
    for (const source of sources) {
      try {
        const library = await import(source.module);
        return { ...library, wasmRoot: source.wasm };
      } catch (error) {
        lastError = error;
      }
    }
    throw new Error(`Could not load the pose runtime from either CDN: ${lastError?.message || 'network blocked'}`);
  }

  function initialisePoseRuntime() {
    if (landmarker) return Promise.resolve(landmarker);
    if (!runtimePromise) {
      runtimePromise = (async () => {
        const { FilesetResolver, PoseLandmarker, wasmRoot } = await loadMediaPipe();
        const vision = await FilesetResolver.forVisionTasks(wasmRoot);
        // Firefox can spend several seconds failing the GPU delegate before
        // repeating the same initialisation on CPU. Start on CPU there.
        const preferCpu = /Firefox\//.test(navigator.userAgent);
        const options = {
          baseOptions: {
            modelAssetPath: MODEL_URL,
            delegate: preferCpu ? 'CPU' : 'GPU',
          },
          runningMode: 'VIDEO',
          numPoses: 1,
          minPoseDetectionConfidence: 0.55,
          minPosePresenceConfidence: 0.55,
          minTrackingConfidence: 0.55,
        };
        try {
          landmarker = await PoseLandmarker.createFromOptions(vision, options);
        } catch (gpuError) {
          if (preferCpu) throw gpuError;
          options.baseOptions.delegate = 'CPU';
          landmarker = await PoseLandmarker.createFromOptions(vision, options);
        }
        return landmarker;
      })().catch((error) => {
        runtimePromise = null;
        throw error;
      });
    }
    return runtimePromise;
  }

  function preloadPoseRuntime() {
    setStatus(tr('Preloading pose model — camera remains off'), 'busy');
    initialisePoseRuntime().then(() => {
      if (!stream) setStatus(tr('Pose model ready — camera remains off'), 'ready');
    }).catch((error) => {
      if (!stream) setStatus(tr('Pose model preload paused — camera remains off'));
      console.warn('Pose runtime preload failed; the camera button will retry it.', error);
    });
  }

  function setStatus(message, state = '') {
    status.className = `detector-status ${state}`;
    status.querySelector('span:last-child').textContent = message;
  }

  function showError(message) {
    errorEl.textContent = message;
  }

  function delay(milliseconds) {
    return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
  }

  function csrfToken() {
    const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function modeNode(prefix, field) {
    return document.getElementById(`${prefix}-${field}`)?.textContent.trim() || '';
  }

  function modeConfig(mode = currentMode) {
    const prefix = mode === GAME_MODES.LEG_CLAPS ? 'leg-claps' : 'six-seven';
    return {
      title: modeNode(prefix, 'title'),
      description: modeNode(prefix, 'description'),
      scoreLabel: modeNode(prefix, 'score-label'),
      resultUnit: modeNode(prefix, 'result-unit'),
      mark: modeNode(prefix, 'placeholder'),
      hudLabel: mode === GAME_MODES.LEG_CLAPS ? 'LEG CLAPS' : '67 COUNT',
      hudBrand: mode === GAME_MODES.LEG_CLAPS ? 'ICAiJY · TUNG TUNG' : 'ICAiJY · SIX SEVEN',
      downloadSlug: mode === GAME_MODES.LEG_CLAPS ? 'tung-tung-leg-claps' : '67-run',
    };
  }

  function armedStatus() {
    return currentMode === GAME_MODES.LEG_CLAPS
      ? tr('Armed — keep hips, knees and ankles visible')
      : tr('Armed — step back until shoulders and wrists are visible');
  }

  function updateModeUI({ updateUrl = true } = {}) {
    const config = modeConfig();
    activeModeConfig = config;
    app.dataset.gameMode = currentMode;
    if (counterTitle) counterTitle.textContent = config.title;
    if (counterDescription) counterDescription.textContent = config.description;
    scoreLabel.textContent = config.scoreLabel;
    resultUnit.textContent = config.resultUnit;
    placeholderMark.textContent = config.mark;
    hallMark.textContent = config.mark;
    modeButtons.forEach((button) => {
      const active = button.dataset.counterMode === currentMode;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    const hallUrl = new URL(app.dataset.hallUrl, window.location.origin);
    hallUrl.searchParams.set('mode', currentMode);
    hallPortal.href = hallUrl.href;
    if (updateUrl && app.dataset.modeLocked !== 'true') {
      const pageUrl = new URL(window.location.href);
      pageUrl.searchParams.set('mode', currentMode);
      window.history.replaceState({}, '', pageUrl);
    }
  }

  function switchMode(mode) {
    if (!Object.values(GAME_MODES).includes(mode) || mode === currentMode) return;
    if (running || countdownActive || armed || app.dataset.modeLocked === 'true') return;
    if (!resultCard.hidden || recordingBlob) resetRun();
    currentMode = mode;
    gestureTracker = createGestureTracker(currentMode);
    readyFrames = 0;
    poseReady = false;
    updateModeUI();
    if (stream) setStatus(tr('Detector ready — step into frame'), 'busy');
    showError('');
  }

  function setModeControlsDisabled(disabled) {
    modeButtons.forEach((button) => { button.disabled = disabled; });
  }

  function shareableResult() {
    const isLegClaps = currentMode === GAME_MODES.LEG_CLAPS;
    const headline = rivalName
      ? isLegClaps
        ? `I made ${score} Tung Tung Leg Claps in 20 seconds against ${rivalName}'s ${rivalFinalScore}.`
        : `I made ${score} 6️⃣7️⃣ moves in 20 seconds against ${rivalName}'s ${rivalFinalScore}.`
      : isLegClaps
        ? `I made ${score} Tung Tung Leg Claps in 20 seconds. The knees have submitted their findings. 🥒`
        : score === 67
          ? 'I made exactly 67 6️⃣7️⃣ moves in 20 seconds. Peer review is complete. 🧪'
          : `I made ${score} 6️⃣7️⃣ moves in 20 seconds.`;
    const blocks = score > 0
      ? `${'🟩'.repeat(Math.min(score, 67))}${score > 67 ? ` +${score - 67}` : ''}`
      : '⬜';
    const pageUrl = rivalName ? new URL(window.location.href) : new URL('/67/counter/', window.location.origin);
    pageUrl.searchParams.set('mode', currentMode);
    const experiment = isLegClaps ? 'TUNG TUNG LEG CLAPS · 酸黄瓜舞计数' : 'SIX SEVEN';
    return `${headline}\n${blocks}\n${experiment}\nWatch the run or try to beat it.\n${pageUrl.href}`;
  }

  async function copyShareResult() {
    if (!shareText?.value) return;
    try {
      if (navigator.clipboard?.writeText && window.isSecureContext) {
        await navigator.clipboard.writeText(shareText.value);
      } else {
        shareText.select();
        shareText.setSelectionRange(0, shareText.value.length);
        if (!document.execCommand('copy')) throw new Error('Copy command was rejected.');
      }
      copyShareButton.textContent = tr('Copied! 🎉');
      copyShareStatus.textContent = tr('Result copied. Scientific distribution may begin.');
    } catch (error) {
      copyShareStatus.textContent = tr('Automatic copy failed. Select the text and copy it manually.');
    }
    window.setTimeout(() => {
      copyShareButton.textContent = tr('Copy to clipboard');
    }, 1500);
  }

  function preferredRecordingType() {
    if (!window.MediaRecorder) return '';
    const candidates = [
      'video/webm;codecs=vp8',
      'video/webm',
      'video/mp4;codecs=avc1',
      'video/mp4',
    ];
    return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || '';
  }

  function drawPose(landmarks) {
    const width = video.videoWidth || 640;
    const height = video.videoHeight || 480;
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    context.clearRect(0, 0, width, height);
    if (!landmarks) return;

    const geometry = OVERLAY_GEOMETRY[currentMode];
    context.lineWidth = Math.max(3, width / 180);
    context.strokeStyle = '#d8ff62';
    context.fillStyle = '#ffffff';
    context.lineCap = 'round';
    for (const [from, to] of geometry.links) {
      const a = landmarks[from];
      const b = landmarks[to];
      context.beginPath();
      context.moveTo(a.x * width, a.y * height);
      context.lineTo(b.x * width, b.y * height);
      context.stroke();
    }
    for (const id of geometry.points) {
      const point = landmarks[id];
      context.beginPath();
      context.arc(point.x * width, point.y * height, Math.max(4, width / 120), 0, Math.PI * 2);
      context.fill();
    }
  }

  function sufficientlyVisible(landmarks) {
    return landmarksAreVisible(currentMode, landmarks);
  }

  function observeGesture(landmarks, now) {
    // The detector and timer use separate animation-frame loops. Enforce the
    // deadline here too so a detector frame cannot sneak in after 20 seconds
    // but before the timer loop has rendered the finished state.
    if (!running || now >= endTime || !sufficientlyVisible(landmarks)) return;
    if (gestureTracker.observe(landmarks, now)) {
      score += 1;
      scoreEl.textContent = score;
      eventTimeline.push(Number(Math.max(0, (now - runStartedAt) / 1000).toFixed(3)));
    }
  }

  function detectFrame() {
    if (!landmarker || !stream) return;
    if (video.readyState >= 2 && video.currentTime !== lastVideoTime) {
      lastVideoTime = video.currentTime;
      try {
        const result = landmarker.detectForVideo(video, performance.now());
        const landmarks = result.landmarks?.[0] || null;
        drawPose(landmarks);
        if (sufficientlyVisible(landmarks)) readyFrames = Math.min(readyFrames + 1, 12);
        else readyFrames = Math.max(0, readyFrames - 2);
        poseReady = readyFrames >= 5;

        if (!running && !countdownActive) {
          if (armed) {
            if (poseReady) {
              beginRun();
            } else {
              setStatus(armedStatus(), 'busy');
              startButton.textContent = tr('Waiting for your pose…');
            }
          } else if (poseReady) {
            startButton.disabled = false;
            startButton.textContent = READY_LABEL;
            setStatus(tr("Pose detected — click I'm ready, then take your position"), 'ready');
          } else {
            // Readiness is a user decision; a pose is required to start, not to arm the run.
            startButton.disabled = false;
            startButton.textContent = READY_LABEL;
            setStatus(tr("Detector ready — click I'm ready, then step into frame"), 'ready');
          }
        }
        observeGesture(landmarks, performance.now());
      } catch (error) {
        showError(`${tr('Pose detector paused:')} ${error.message}`);
      }
    }
    detectorLoop = requestAnimationFrame(detectFrame);
  }

  async function initialiseDetector() {
    enableButton.disabled = true;
    setStatus(tr('Requesting camera permission…'), 'busy');
    showError('');
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 30, max: 30 } },
        audio: false,
      });
      video.srcObject = stream;
      await video.play();
      placeholder.hidden = true;
      enableButton.hidden = true;
      startButton.hidden = false;
      startButton.disabled = true;
      startButton.textContent = landmarker ? READY_LABEL : tr('Finishing detector setup…');
      setStatus(landmarker ? tr('Pose model ready') : tr('Finishing pose model preload…'), 'busy');
      await initialisePoseRuntime();
      startButton.disabled = false;
      startButton.textContent = READY_LABEL;
      detectorLoop = requestAnimationFrame(detectFrame);
    } catch (error) {
      enableButton.disabled = false;
      enableButton.hidden = false;
      startButton.hidden = true;
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
        stream = null;
        video.srcObject = null;
        placeholder.hidden = false;
        setStatus(tr('Camera permission worked, but the pose runtime did not load'));
        showError(error.message || 'The pose runtime was blocked by this network.');
      } else {
        setStatus(tr('Camera unavailable'));
        showError(tr('Could not start the camera. Use HTTPS, allow camera access, and try a current browser.'));
      }
    }
  }

  function startRecording() {
    const type = preferredRecordingType();
    if (!type) throw new Error('This browser cannot record a compatible WebM/MP4 video.');

    // Firefox can preserve the age of a long-lived camera track in WebM packet
    // timestamps. A canvas capture creates a fresh recording clock without
    // requesting the camera again or changing the stream used by MediaPipe.
    recordingCanvas = document.createElement('canvas');
    recordingCanvas.width = video.videoWidth || 640;
    recordingCanvas.height = video.videoHeight || 480;
    recordingContext = recordingCanvas.getContext('2d');
    if (!recordingContext || !recordingCanvas.captureStream) {
      recordingCanvas = null;
      recordingContext = null;
      throw new Error('This browser cannot create a timestamp-safe recording.');
    }

    const drawRecordingFrame = () => {
      if (!recordingContext || !recordingCanvas) return;
      recordingContext.drawImage(video, 0, 0, recordingCanvas.width, recordingCanvas.height);
      drawRecordingHud();
      recordingFrame = requestAnimationFrame(drawRecordingFrame);
    };

    try {
      drawRecordingFrame();
      recordingStream = recordingCanvas.captureStream(30);
      recordingChunks = [];
      recorder = new MediaRecorder(recordingStream, { mimeType: type, videoBitsPerSecond: 1_600_000 });
      recorder.addEventListener('dataavailable', (event) => {
        if (event.data.size) recordingChunks.push(event.data);
      });
      recorder.start(500);
      livePill.hidden = false;
    } catch (error) {
      recorder = null;
      recordingChunks = [];
      stopRecordingPipeline();
      throw error;
    }
  }

  function drawRecordingHud() {
    const width = recordingCanvas.width;
    const height = recordingCanvas.height;
    const padding = Math.max(14, width * 0.026);
    const scoreSize = Math.max(34, width * 0.085);
    const labelSize = Math.max(12, width * 0.024);
    const time = running ? Math.max(0, (endTime - performance.now()) / 1000).toFixed(1) : '20.0';
    recordingContext.save();
    recordingContext.fillStyle = 'rgba(15, 23, 42, .82)';
    recordingContext.fillRect(padding, padding, scoreSize * 2.25, scoreSize * 1.42);
    recordingContext.fillStyle = '#d8ff62';
    recordingContext.font = `900 ${scoreSize}px Inter, Arial, sans-serif`;
    recordingContext.textBaseline = 'top';
    recordingContext.fillText(String(score), padding * 1.55, padding * 1.15);
    recordingContext.fillStyle = '#ffffff';
    recordingContext.font = `800 ${labelSize}px Inter, Arial, sans-serif`;
    recordingContext.fillText(activeModeConfig.hudLabel, padding * 1.55, padding * 1.15 + scoreSize);

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
    recordingContext.fillText(activeModeConfig.hudBrand, padding * 1.45, height - padding - labelSize * .55);
    recordingContext.restore();
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
    if (rivalVideo) {
      const rivalGameTime = Math.max(0, rivalVideo.currentTime - RECORDING_LEAD_SECONDS);
      while (rivalTimelineIndex < rivalTimeline.length && rivalTimeline[rivalTimelineIndex] <= rivalGameTime) {
        rivalTimelineIndex += 1;
      }
      rivalScoreEl.textContent = rivalTimelineIndex;
    }
    timeEl.textContent = remaining.toFixed(1);
    if (remaining <= 0) {
      finishRun();
      return;
    }
    gameLoop = requestAnimationFrame(updateGameClock);
  }

  function armRun() {
    if (!landmarker || running || countdownActive || armed) return;
    showError('');
    resultCard.hidden = true;
    resetButton.hidden = true;
    startButton.disabled = true;
    startButton.textContent = tr('Waiting for your pose…');
    score = 0;
    eventTimeline = [];
    runStartedAt = 0;
    rivalTimelineIndex = 0;
    if (rivalScoreEl) rivalScoreEl.textContent = '0';
    if (rivalVideo) {
      rivalVideo.pause();
      if (rivalVideo.readyState) rivalVideo.currentTime = 0;
    }
    gestureTracker.reset();
    scoreEl.textContent = '0';
    timeEl.textContent = GAME_SECONDS.toFixed(1);
    armed = true;
    setModeControlsDisabled(true);
    setStatus(armedStatus(), 'busy');
    if (poseReady) beginRun();
  }

  async function beginRun() {
    if (!armed || !poseReady || running || countdownActive) return;
    if (!rivalReady) {
      setStatus(tr('Opponent evidence is still buffering'), 'busy');
      startButton.textContent = tr('Waiting for opponent video…');
      return;
    }
    armed = false;
    countdownActive = true;
    startButton.hidden = true;
    setStatus(tr('Pose locked — countdown commencing'), 'ready');

    try {
      if (rivalVideo) {
        rivalVideo.currentTime = 0;
        await rivalVideo.play();
      }
      startRecording();
    } catch (error) {
      rivalVideo?.pause();
      if (recorder) {
        await stopRecording();
        recordingBlob = null;
      }
      showError(error.message);
      countdownActive = false;
      setModeControlsDisabled(false);
      startButton.hidden = false;
      startButton.disabled = false;
      startButton.textContent = READY_LABEL;
      return;
    }

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
    setStatus(tr('Experiment in progress'), 'ready');
    gameLoop = requestAnimationFrame(updateGameClock);
  }

  async function finishRun() {
    if (!running) return;
    running = false;
    cancelAnimationFrame(gameLoop);
    timeEl.textContent = '0.0';
    setStatus(tr('Run complete — detector remains local'), 'ready');
    rivalVideo?.pause();
    if (rivalScoreEl) rivalScoreEl.textContent = rivalFinalScore;
    const blob = await stopRecording();
    setModeControlsDisabled(false);

    resultScore.textContent = score;
    resultCopy.textContent = rivalName
      ? score > rivalFinalScore
        ? `You defeated ${rivalName} by ${score - rivalFinalScore}. The archive has been destabilised.`
        : score === rivalFinalScore
          ? `A draw with ${rivalName}. Statistically annoying.`
          : `${rivalName} remains ahead by ${rivalFinalScore - score}. Replication is encouraged.`
      : currentMode === GAME_MODES.LEG_CLAPS
        ? score > 0
          ? tr('The knees opened, closed and produced a statistically usable result.')
          : tr('No inward knee events were observed. The pickle remains motionless.')
        : score === 67
          ? tr('Exactly 67. There will be no further questions.')
          : score > 67
            ? tr('The 67 barrier has been disturbed.')
            : tr('The Institute recommends more arm-based research.');
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
      recordingDownload.download = `${activeModeConfig.downloadSlug}-counted.${extension}`;
      recordingDownload.hidden = false;
    }
    startButton.hidden = true;
    resetButton.hidden = false;
    resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
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
    armed = false;
    countdownActive = false;
    score = 0;
    eventTimeline = [];
    gestureTracker.reset();
    runStartedAt = 0;
    rivalTimelineIndex = 0;
    if (rivalScoreEl) rivalScoreEl.textContent = '0';
    if (rivalVideo) {
      rivalVideo.pause();
      if (rivalVideo.readyState) rivalVideo.currentTime = 0;
    }
    scoreEl.textContent = '0';
    timeEl.textContent = GAME_SECONDS.toFixed(1);
    resultCard.hidden = true;
    shareText.value = '';
    copyShareStatus.textContent = '';
    resetButton.hidden = true;
    setModeControlsDisabled(false);
    startButton.hidden = false;
    startButton.disabled = !landmarker;
    startButton.textContent = landmarker ? READY_LABEL : tr('Detector is still loading…');
    showError('');
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
    form.append('game_mode', currentMode);
    form.append('score', String(score));
    form.append('event_timeline', JSON.stringify(eventTimeline));
    form.append('publication_consent', 'yes');
    form.append('video', recordingBlob, `${activeModeConfig.downloadSlug}.${extension}`);
    if (displayNameInput) form.append('display_name', displayNameInput.value);
    if (turnstileResponse) form.append('cf-turnstile-response', turnstileResponse);

    submitButton.disabled = true;
    uploadStatus.textContent = tr('Uploading public evidence after the timer has safely stopped…');
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
        const statusHint = response.status === 403
          ? 'Security check rejected the upload. Refresh this page and try again.'
          : response.status === 413
            ? 'The web server rejected the recording as too large.'
            : response.status >= 500
              ? `The server returned HTTP ${response.status}. The site owner may need to run database migrations or inspect the server log.`
              : `The server returned HTTP ${response.status} instead of JSON.`;
        throw new Error(statusHint);
      }
      if (!response.ok) throw new Error(payload.error || 'Upload failed.');
      uploadStatus.textContent = payload.message;
      submitButton.hidden = true;
      if (discardButton) discardButton.hidden = true;
      window.setTimeout(() => { window.location.href = payload.entry_url || payload.hall_of_fame_url; }, 1200);
    } catch (error) {
      uploadStatus.textContent = error.message;
      submitButton.disabled = false;
      if (window.turnstile) window.turnstile.reset();
    }
  }

  function openPublicationModal() {
    if (!publicationModal) return;
    publicationModal.hidden = false;
    document.body.classList.add('publication-modal-open');
    confirmPublication.disabled = !publicationConsent.checked;
    publicationConsent.focus();
  }

  function closePublicationModal() {
    if (!publicationModal) return;
    publicationModal.hidden = true;
    document.body.classList.remove('publication-modal-open');
  }

  updateModeUI({ updateUrl: false });
  preloadPoseRuntime();
  modeButtons.forEach((button) => {
    button.addEventListener('click', () => switchMode(button.dataset.counterMode));
  });
  enableButton.addEventListener('click', initialiseDetector);
  startButton.addEventListener('click', armRun);
  resetButton.addEventListener('click', resetRun);
  submitButton?.addEventListener('click', openPublicationModal);
  publicationConsent?.addEventListener('change', () => {
    confirmPublication.disabled = !publicationConsent.checked;
  });
  confirmPublication?.addEventListener('click', () => {
    if (!publicationConsent.checked) return;
    closePublicationModal();
    submitRecording();
  });
  document.querySelectorAll('[data-close-publication-modal], #cancel-publication').forEach((button) => {
    button.addEventListener('click', closePublicationModal);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && publicationModal && !publicationModal.hidden) closePublicationModal();
  });
  discardButton?.addEventListener('click', discardRecording);
  copyShareButton?.addEventListener('click', copyShareResult);
  if (rivalVideo) {
    const markRivalReady = () => {
      rivalReady = true;
      if (landmarker && !running && !countdownActive) {
        startButton.disabled = false;
        startButton.textContent = READY_LABEL;
      }
    };
    rivalVideo.addEventListener('canplay', markRivalReady);
    rivalVideo.addEventListener('loadeddata', markRivalReady);
    if (rivalVideo.readyState >= 2) markRivalReady();
  }
  window.addEventListener('beforeunload', () => {
    if (recordingUrl) URL.revokeObjectURL(recordingUrl);
    stopRecordingPipeline();
    stream?.getTracks().forEach((track) => track.stop());
  });
}
