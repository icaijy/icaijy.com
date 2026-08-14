const app = document.getElementById('counter-app');
if (app) {
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
  const recordingReview = document.getElementById('recording-review');
  const recordingPreview = document.getElementById('recording-preview');
  const submitButton = document.getElementById('submit-hof');
  const discardButton = document.getElementById('discard-recording');
  const uploadStatus = document.getElementById('upload-status');
  const modeInputs = [...document.querySelectorAll('input[name="mode"]')];

  const GAME_SECONDS = 20;
  let stream = null;
  let landmarker = null;
  let detectorLoop = null;
  let gameLoop = null;
  let lastVideoTime = -1;
  let poseReady = false;
  let readyFrames = 0;
  let running = false;
  let currentMode = 'casual';
  let endTime = 0;
  let score = 0;
  let lastZone = 0;
  let lastCountAt = 0;
  let recorder = null;
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

    const pointIds = [11, 12, 13, 14, 15, 16];
    const links = [[11, 13], [13, 15], [12, 14], [14, 16], [11, 12], [15, 16]];
    context.lineWidth = Math.max(3, width / 180);
    context.strokeStyle = '#d8ff62';
    context.fillStyle = '#ffffff';
    context.lineCap = 'round';
    for (const [from, to] of links) {
      const a = landmarks[from];
      const b = landmarks[to];
      context.beginPath();
      context.moveTo(a.x * width, a.y * height);
      context.lineTo(b.x * width, b.y * height);
      context.stroke();
    }
    for (const id of pointIds) {
      const point = landmarks[id];
      context.beginPath();
      context.arc(point.x * width, point.y * height, Math.max(4, width / 120), 0, Math.PI * 2);
      context.fill();
    }
  }

  function sufficientlyVisible(landmarks) {
    if (!landmarks) return false;
    return [11, 12, 13, 14, 15, 16].every((id) => {
      const point = landmarks[id];
      return point && (point.visibility ?? 1) > 0.45 && point.x > 0.02 && point.x < 0.98 && point.y > 0.02 && point.y < 0.98;
    });
  }

  function observeGesture(landmarks, now) {
    if (!running || !sufficientlyVisible(landmarks)) return;
    const leftWrist = landmarks[15];
    const rightWrist = landmarks[16];
    const leftShoulder = landmarks[11];
    const rightShoulder = landmarks[12];
    const shoulderWidth = Math.max(
      Math.hypot(leftShoulder.x - rightShoulder.x, leftShoulder.y - rightShoulder.y),
      0.1,
    );
    const normalisedDifference = (leftWrist.y - rightWrist.y) / shoulderWidth;
    const zone = normalisedDifference > 0.20 ? 1 : normalisedDifference < -0.20 ? -1 : 0;
    if (zone === 0) return;
    if (lastZone === 0) {
      lastZone = zone;
      return;
    }
    if (zone !== lastZone && now - lastCountAt > 90) {
      score += 1;
      scoreEl.textContent = score;
      lastZone = zone;
      lastCountAt = now;
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

        if (!running) {
          if (poseReady) {
            setStatus('Pose detected — alternate both hands vertically', 'ready');
            startButton.disabled = false;
            startButton.textContent = 'Start 20 second run';
          } else {
            setStatus('Detector ready — place shoulders, elbows and wrists in frame', 'busy');
            startButton.disabled = true;
            startButton.textContent = 'Waiting for a visible pose…';
          }
        }
        observeGesture(landmarks, performance.now());
      } catch (error) {
        showError(`Pose detector paused: ${error.message}`);
      }
    }
    detectorLoop = requestAnimationFrame(detectFrame);
  }

  async function initialiseDetector() {
    enableButton.disabled = true;
    setStatus('Requesting camera permission…', 'busy');
    showError('');
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 30, max: 30 } },
        audio: false,
      });
      video.srcObject = stream;
      await video.play();
      placeholder.hidden = true;
      setStatus('Loading the pose model into this browser…', 'busy');

      const { FilesetResolver, PoseLandmarker, wasmRoot } = await loadMediaPipe();
      const vision = await FilesetResolver.forVisionTasks(wasmRoot);
      const options = {
        baseOptions: {
          modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task',
          delegate: 'GPU',
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
        options.baseOptions.delegate = 'CPU';
        landmarker = await PoseLandmarker.createFromOptions(vision, options);
      }
      enableButton.hidden = true;
      detectorLoop = requestAnimationFrame(detectFrame);
    } catch (error) {
      enableButton.disabled = false;
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
        stream = null;
        video.srcObject = null;
        placeholder.hidden = false;
        setStatus('Camera permission worked, but the pose runtime did not load');
        showError(error.message || 'The pose runtime was blocked by this network.');
      } else {
        setStatus('Camera unavailable');
        showError('Could not start the camera. Use HTTPS, allow camera access, and try a current browser.');
      }
    }
  }

  function startRecording() {
    const type = preferredRecordingType();
    if (!type) throw new Error('This browser cannot record a compatible WebM/MP4 video.');
    recordingChunks = [];
    recorder = new MediaRecorder(stream, { mimeType: type, videoBitsPerSecond: 1_600_000 });
    recorder.addEventListener('dataavailable', (event) => {
      if (event.data.size) recordingChunks.push(event.data);
    });
    recorder.start(500);
    livePill.hidden = false;
  }

  function stopRecording() {
    return new Promise((resolve) => {
      if (!recorder || recorder.state === 'inactive') {
        resolve(null);
        return;
      }
      recorder.addEventListener('stop', () => {
        const baseType = (recorder.mimeType || recordingChunks[0]?.type || 'video/webm').split(';')[0];
        recordingBlob = new Blob(recordingChunks, { type: baseType });
        recorder = null;
        recordingChunks = [];
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
    if (remaining <= 0) {
      finishRun();
      return;
    }
    gameLoop = requestAnimationFrame(updateGameClock);
  }

  async function beginRun() {
    if (!poseReady || running) return;
    currentMode = document.querySelector('input[name="mode"]:checked').value;
    showError('');
    resultCard.hidden = true;
    resetButton.hidden = true;
    startButton.disabled = true;
    modeInputs.forEach((input) => { input.disabled = true; });
    score = 0;
    lastZone = 0;
    lastCountAt = 0;
    scoreEl.textContent = '0';
    timeEl.textContent = GAME_SECONDS.toFixed(1);

    if (currentMode === 'hof') {
      try {
        startRecording();
      } catch (error) {
        showError(error.message);
        modeInputs.forEach((input) => { input.disabled = false; });
        startButton.disabled = false;
        return;
      }
    }

    for (const value of ['3', '2', '1']) {
      countdownEl.textContent = value;
      await delay(700);
    }
    countdownEl.textContent = 'GO';
    await delay(350);
    countdownEl.textContent = '';
    running = true;
    endTime = performance.now() + GAME_SECONDS * 1000;
    setStatus('Experiment in progress', 'ready');
    gameLoop = requestAnimationFrame(updateGameClock);
  }

  async function finishRun() {
    if (!running) return;
    running = false;
    cancelAnimationFrame(gameLoop);
    timeEl.textContent = '0.0';
    setStatus('Run complete — detector remains local', 'ready');
    const blob = currentMode === 'hof' ? await stopRecording() : null;

    resultScore.textContent = score;
    resultCopy.textContent = score === 67
      ? 'Exactly 67. There will be no further questions.'
      : score > 67
        ? 'The 67 barrier has been disturbed.'
        : 'The Institute recommends more arm-based research.';
    resultCard.hidden = false;
    recordingReview.hidden = currentMode !== 'hof';
    if (blob) {
      if (recordingUrl) URL.revokeObjectURL(recordingUrl);
      recordingUrl = URL.createObjectURL(blob);
      recordingPreview.src = recordingUrl;
    }
    resetButton.hidden = false;
    resultCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function discardRecording() {
    if (recordingUrl) URL.revokeObjectURL(recordingUrl);
    recordingUrl = null;
    recordingBlob = null;
    recordingPreview.removeAttribute('src');
    recordingPreview.load();
    recordingReview.hidden = true;
    if (uploadStatus) uploadStatus.textContent = 'Recording discarded. Nothing was uploaded.';
  }

  function resetRun() {
    discardRecording();
    score = 0;
    scoreEl.textContent = '0';
    timeEl.textContent = GAME_SECONDS.toFixed(1);
    resultCard.hidden = true;
    resetButton.hidden = true;
    modeInputs.forEach((input) => { input.disabled = false; });
    startButton.disabled = !poseReady;
    startButton.textContent = poseReady ? 'Start 20 second run' : 'Waiting for a visible pose…';
    showError('');
  }

  async function submitRecording() {
    if (!recordingBlob || !submitButton) return;
    const maxBytes = Number(app.dataset.maxUploadMb) * 1024 * 1024;
    if (recordingBlob.size > maxBytes) {
      uploadStatus.textContent = `Recording exceeded the ${app.dataset.maxUploadMb} MB upload limit.`;
      return;
    }

    const turnstileResponse = document.querySelector('[name="cf-turnstile-response"]')?.value || '';
    const extension = recordingBlob.type === 'video/mp4' ? 'mp4' : 'webm';
    const form = new FormData();
    form.append('score', String(score));
    form.append('video', recordingBlob, `67-run.${extension}`);
    if (turnstileResponse) form.append('cf-turnstile-response', turnstileResponse);

    submitButton.disabled = true;
    uploadStatus.textContent = 'Uploading evidence after the timer has safely stopped…';
    try {
      const response = await fetch(app.dataset.submitUrl, {
        method: 'POST',
        body: form,
        headers: { 'X-CSRFToken': csrfToken() },
        credentials: 'same-origin',
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'Upload failed.');
      uploadStatus.textContent = payload.message;
      submitButton.hidden = true;
      if (discardButton) discardButton.hidden = true;
      window.setTimeout(() => { window.location.href = payload.hall_of_fame_url; }, 1200);
    } catch (error) {
      uploadStatus.textContent = error.message;
      submitButton.disabled = false;
      if (window.turnstile) window.turnstile.reset();
    }
  }

  modeInputs.forEach((input) => {
    input.addEventListener('change', () => {
      document.querySelectorAll('.mode-option').forEach((label) => {
        label.classList.toggle('active', label.contains(document.querySelector('input[name="mode"]:checked')));
      });
    });
  });
  enableButton.addEventListener('click', initialiseDetector);
  startButton.addEventListener('click', beginRun);
  resetButton.addEventListener('click', resetRun);
  submitButton?.addEventListener('click', submitRecording);
  discardButton?.addEventListener('click', discardRecording);
  window.addEventListener('beforeunload', () => {
    if (recordingUrl) URL.revokeObjectURL(recordingUrl);
    stream?.getTracks().forEach((track) => track.stop());
  });
}
