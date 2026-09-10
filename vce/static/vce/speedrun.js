const root = document.querySelector('.vce-page[data-start-url]');

if (root) {
  const $ = selector => root.querySelector(selector);
  const csrf = $('[name=csrfmiddlewaretoken]').value;
  const screens = Object.fromEntries([...root.querySelectorAll('[data-screen]')].map(el => [el.dataset.screen, el]));
  const optionsEl = $('[data-options]');
  const startButton = $('[data-start]');
  const submitButton = $('[data-submit]');
  const video = $('[data-camera]');
  const canvas = $('[data-pose-overlay]');
  const context = canvas.getContext('2d');
  const MODEL_URL = 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task';
  let token = '', deadline = 0, position = 0, score = 0, nextQuestion = null, mode = root.dataset.initialMode || 'normal';
  let running = false, answering = false, frame = 0, detectorFrame = 0, stream = null, landmarker = null, tracker = null, engine = null;
  let timelines = {six_seven: [], leg_claps: []}, runStartedAt = 0, lastVideoTime = -1;

  const post = async (url, fields = {}) => {
    const response = await fetch(url, {method: 'POST', headers: {'X-CSRFToken': csrf}, body: new URLSearchParams(fields)});
    const payload = await response.json().catch(() => ({error: 'Unreadable server response.'}));
    if (!response.ok) throw Object.assign(new Error(payload.error || 'Request failed.'), {payload, status: response.status});
    return payload;
  };
  const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
  const show = name => Object.entries(screens).forEach(([key, el]) => { el.hidden = key !== name; });
  const hasMath = text => /\\\\[([]/.test(text || '');
  const typeset = node => window.MathJax?.Hub?.Queue(['Typeset', window.MathJax.Hub, node]);
  const setText = (selector, text) => { const node = $(selector); node.textContent = text; if (hasMath(text)) typeset(node); };
  const isPhysical = () => mode !== 'normal';

  function selectMode(nextMode) {
    if (running) return;
    mode = nextMode;
    const chaos = isPhysical();
    if ($('[data-chaos-modes]')) $('[data-chaos-modes]').hidden = !chaos;
    root.querySelectorAll('[data-mode]').forEach(button => button.classList.toggle('active', chaos ? button.dataset.mode !== 'normal' : button.dataset.mode === 'normal'));
    root.querySelectorAll('[data-chaos-mode]').forEach(button => button.classList.toggle('active', button.dataset.chaosMode === mode));
    startButton.disabled = chaos && !stream;
    startButton.querySelector('small').textContent = chaos && !stream ? 'ENABLE CAMERA FIRST' : '60 SECOND SPEEDRUN';
  }

  root.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click', () => selectMode(button.dataset.mode)));
  root.querySelectorAll('[data-chaos-mode]').forEach(button => button.addEventListener('click', () => {
    if (running || button.dataset.chaosMode === mode) return;
    const url = new URL(window.location.href);
    url.searchParams.set('mode', button.dataset.chaosMode);
    url.hash = '';
    window.location.assign(url);
  }));

  async function loadVision() {
    if (landmarker) return;
    const sources = [
      ['https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/vision_bundle.mjs', 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm'],
      ['https://unpkg.com/@mediapipe/tasks-vision@1.0.1/vision_bundle.mjs', 'https://unpkg.com/@mediapipe/tasks-vision@1.0.1/wasm'],
    ];
    let lastError;
    for (const [moduleUrl, wasm] of sources) {
      try {
        const {FilesetResolver, PoseLandmarker} = await import(moduleUrl);
        const vision = await FilesetResolver.forVisionTasks(wasm);
        const options = {baseOptions: {modelAssetPath: MODEL_URL, delegate: /Firefox\//.test(navigator.userAgent) ? 'CPU' : 'GPU'}, runningMode: 'VIDEO', numPoses: 1, minPoseDetectionConfidence: .55, minPosePresenceConfidence: .55, minTrackingConfidence: .55};
        try { landmarker = await PoseLandmarker.createFromOptions(vision, options); }
        catch (error) { options.baseOptions.delegate = 'CPU'; landmarker = await PoseLandmarker.createFromOptions(vision, options); }
        return;
      } catch (error) { lastError = error; }
    }
    throw lastError || new Error('Pose model could not load.');
  }

  $('[data-enable-camera]')?.addEventListener('click', async () => {
    const status = $('[data-camera-status]');
    status.textContent = 'Loading pose model…';
    try {
      [engine, stream] = await Promise.all([import(root.dataset.gestureEngineUrl), navigator.mediaDevices.getUserMedia({video: {facingMode: 'user', width: {ideal: 960}, height: {ideal: 720}}, audio: false})]);
      await loadVision();
      video.srcObject = stream;
      await video.play();
      status.textContent = 'Camera ready. Keep your body in frame.';
      $('[data-enable-camera]').textContent = 'CAMERA READY';
      startButton.disabled = false;
      detectorLoop();
    } catch (error) {
      stream?.getTracks().forEach(track => track.stop()); stream = null;
      status.textContent = `Camera failed: ${error.message}`;
    }
  });

  function drawPose(landmarks) {
    const ratio = window.devicePixelRatio || 1, width = video.clientWidth, height = video.clientHeight;
    if (canvas.width !== width * ratio || canvas.height !== height * ratio) { canvas.width = width * ratio; canvas.height = height * ratio; }
    context.setTransform(ratio, 0, 0, ratio, 0, 0); context.clearRect(0, 0, width, height);
    if (!landmarks || !engine) return;
    const geometry = engine.OVERLAY_GEOMETRY[mode];
    context.strokeStyle = '#38e8ff'; context.fillStyle = '#fff'; context.lineWidth = 3;
    for (const [a, b] of geometry.links) { context.beginPath(); context.moveTo((1-landmarks[a].x)*width, landmarks[a].y*height); context.lineTo((1-landmarks[b].x)*width, landmarks[b].y*height); context.stroke(); }
    for (const id of geometry.points) { context.beginPath(); context.arc((1-landmarks[id].x)*width, landmarks[id].y*height, 4, 0, Math.PI*2); context.fill(); }
  }

  function detectorLoop() {
    if (stream && landmarker && video.readyState >= 2 && video.currentTime !== lastVideoTime) {
      lastVideoTime = video.currentTime;
      const landmarks = landmarker.detectForVideo(video, performance.now()).landmarks?.[0];
      drawPose(landmarks);
      if (running && tracker && landmarks && engine.landmarksAreVisible(mode, landmarks)) {
        const event = tracker.observe(landmarks, performance.now());
        const stamp = Math.min(60, Math.max(0, (performance.now() - runStartedAt) / 1000));
        if (mode === 'combine') { if (event.sixSeven) timelines.six_seven.push(stamp); if (event.legClaps) timelines.leg_claps.push(stamp); }
        else if (event) timelines[mode].push(stamp);
        updateMovement();
      }
    }
    detectorFrame = requestAnimationFrame(detectorLoop);
  }

  function movementScore() { return mode === 'combine' ? timelines.six_seven.length * timelines.leg_claps.length : isPhysical() ? timelines[mode].length : 1; }
  function updateMovement() {
    $('[data-movement-score]').textContent = movementScore();
    $('[data-movement-label]').textContent = mode === 'leg_claps' ? 'TUNG COUNT' : mode === 'combine' ? 'COMBO SCORE' : '67 COUNT';
    $('[data-combo-live]').hidden = mode !== 'combine'; $('[data-six-score]').textContent = timelines.six_seven.length; $('[data-leg-score]').textContent = timelines.leg_claps.length;
  }

  function renderQuestion(question) {
    if (!question) return endRun();
    setText('[data-topic]', question.topic); setText('[data-question]', question.prompt); setText('[data-source]', question.source);
    optionsEl.replaceChildren(...question.options.map((option, index) => {
      const button = document.createElement('button'); button.type = 'button'; button.className = 'vce-option'; button.innerHTML = `<span>${String.fromCharCode(65 + index)}</span><strong></strong>`;
      button.querySelector('strong').textContent = option; button.addEventListener('click', () => choose(index)); return button;
    }));
    if (question.options.some(hasMath)) typeset(optionsEl);
  }

  function tick() {
    if (!running) return; const remaining = Math.max(0, deadline - Date.now());
    $('[data-time]').textContent = (remaining / 1000).toFixed(1); $('[data-progress]').style.width = `${remaining / 600}%`; $('[data-time]').classList.toggle('urgent', remaining <= 10000);
    if (remaining <= 0) return endRun(); frame = requestAnimationFrame(tick);
  }

  async function startRun() {
    if (answering || (isPhysical() && !stream)) return; answering = true; startButton.disabled = true;
    try {
      const data = await post(root.dataset.startUrl, {game_mode: mode, bank_id: root.dataset.bankId}); token = data.token; deadline = Date.parse(data.deadline); position = 0; score = 0; timelines = {six_seven: [], leg_claps: []};
      if (isPhysical()) { tracker = engine.createGestureTracker(mode); runStartedAt = performance.now(); }
      $('[data-score]').textContent = '0'; updateMovement(); $('[data-sidebar="leaderboard"]').hidden = true; $('[data-sidebar="tools"]').hidden = false; $('[data-camera-panel]').hidden = !isPhysical(); show('game'); renderQuestion(data.question); running = true; tick();
    } catch (error) { startButton.disabled = false; startButton.querySelector('small').textContent = error.message; }
    finally { answering = false; }
  }

  async function choose(selected) {
    if (!running || answering || Date.now() >= deadline) return; answering = true; [...optionsEl.children].forEach(button => { button.disabled = true; });
    try {
      const data = await post(root.dataset.answerUrl, {token, position, selected}); if (data.finished) return endRun(data.score);
      score = data.score; position = data.position; $('[data-score]').textContent = score; nextQuestion = data.question;
      if (data.correct) { optionsEl.children[selected]?.classList.add('is-correct'); $('[data-correct-flash]').hidden = false; await delay(260); $('[data-correct-flash]').hidden = true; if (running) renderQuestion(nextQuestion); }
      else { const review = data.review; setText('[data-correct-answer]', `${String.fromCharCode(65 + review.answer_index)}. ${review.answer}`); setText('[data-correct-note]', review.explanations[review.answer_index]); await showPenalty(data.penalty_seconds); if (running) renderQuestion(nextQuestion); }
    } catch (error) { if (error.status === 429 && error.payload?.wait_ms) await delay(error.payload.wait_ms); else { setText('[data-source]', error.message); [...optionsEl.children].forEach(button => { button.disabled = false; }); } }
    finally { answering = false; }
  }

  async function showPenalty(seconds) { $('[data-penalty]').hidden = false; const until = Date.now() + seconds*1000; while (running && Date.now() < until && Date.now() < deadline) { $('[data-penalty-count]').textContent = Math.max(1, Math.ceil((until-Date.now())/1000)); await delay(80); } $('[data-penalty]').hidden = true; }
  function endRun(serverScore) { if (!running && !screens.result.hidden) return; running = false; cancelAnimationFrame(frame); $('[data-penalty]').hidden = true; $('[data-correct-flash]').hidden = true; score = Number.isInteger(serverScore) ? serverScore : score; const movement = movementScore(), final = score * movement; $('[data-final-score]').textContent = final; $('[data-result-copy]').textContent = isPhysical() ? 'correct × movement' : 'correct answers in 60 seconds'; $('[data-result-equation]').hidden = !isPhysical(); $('[data-result-equation]').textContent = `${score} correct × ${movement} movement = ${final}`; show('result'); }
  async function submitRun() { submitButton.disabled = true; $('[data-submit-error]').hidden = true; try { const data = await post(root.dataset.finishUrl, {token, display_name: $('#vce-name')?.value || '', metrics: JSON.stringify(timelines)}); window.location.assign(data.detail_url); } catch (error) { if (error.status === 409) return setTimeout(submitRun, 600); $('[data-submit-error]').textContent = error.message; $('[data-submit-error]').hidden = false; submitButton.disabled = false; } }
  startButton.addEventListener('click', startRun); submitButton.addEventListener('click', submitRun); selectMode(mode);
}
