const root = document.querySelector('.vce-page[data-start-url]');

if (root) {
  const csrf = root.querySelector('[name=csrfmiddlewaretoken]').value;
  const screens = Object.fromEntries([...root.querySelectorAll('[data-screen]')].map(el => [el.dataset.screen, el]));
  const startButton = root.querySelector('[data-start]');
  const submitButton = root.querySelector('[data-submit]');
  const timeEl = root.querySelector('[data-time]');
  const scoreEl = root.querySelector('[data-score]');
  const progressEl = root.querySelector('[data-progress]');
  const topicEl = root.querySelector('[data-topic]');
  const questionEl = root.querySelector('[data-question]');
  const optionsEl = root.querySelector('[data-options]');
  const sourceEl = root.querySelector('[data-source]');
  const penalty = root.querySelector('[data-penalty]');
  const penaltyCount = root.querySelector('[data-penalty-count]');
  const correctAnswer = root.querySelector('[data-correct-answer]');
  const correctNote = root.querySelector('[data-correct-note]');
  const finalScore = root.querySelector('[data-final-score]');
  const submitError = root.querySelector('[data-submit-error]');

  let token = '';
  let deadline = 0;
  let position = 0;
  let score = 0;
  let nextQuestion = null;
  let running = false;
  let answering = false;
  let frame = 0;

  const post = async (url, fields = {}) => {
    const body = new URLSearchParams(fields);
    const response = await fetch(url, {method: 'POST', headers: {'X-CSRFToken': csrf}, body});
    const payload = await response.json().catch(() => ({error: 'The server returned an unreadable response.'}));
    if (!response.ok) throw Object.assign(new Error(payload.error || 'Request failed.'), {payload, status: response.status});
    return payload;
  };

  const show = name => Object.entries(screens).forEach(([key, element]) => { element.hidden = key !== name; });

  const renderQuestion = question => {
    if (!question) return endRun();
    topicEl.textContent = question.topic;
    questionEl.textContent = question.prompt;
    sourceEl.textContent = question.source;
    optionsEl.replaceChildren(...question.options.map((option, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'vce-option';
      button.innerHTML = `<span>${String.fromCharCode(65 + index)}</span><strong></strong>`;
      button.querySelector('strong').textContent = option;
      button.addEventListener('click', () => choose(index));
      return button;
    }));
  };

  const tick = () => {
    if (!running) return;
    const remaining = Math.max(0, deadline - Date.now());
    timeEl.textContent = (remaining / 1000).toFixed(1);
    progressEl.style.width = `${remaining / 600}%`;
    timeEl.classList.toggle('urgent', remaining <= 10000);
    if (remaining <= 0) return endRun();
    frame = requestAnimationFrame(tick);
  };

  const startRun = async () => {
    if (answering) return;
    answering = true;
    startButton.disabled = true;
    try {
      const data = await post(root.dataset.startUrl);
      token = data.token;
      deadline = Date.parse(data.deadline);
      position = data.position;
      score = data.score;
      scoreEl.textContent = score;
      show('game');
      renderQuestion(data.question);
      running = true;
      tick();
    } catch (error) {
      startButton.disabled = false;
      startButton.querySelector('small').textContent = error.message;
    } finally {
      answering = false;
    }
  };

  const choose = async selected => {
    if (!running || answering || Date.now() >= deadline) return;
    answering = true;
    [...optionsEl.children].forEach(button => { button.disabled = true; });
    try {
      const data = await post(root.dataset.answerUrl, {token, position, selected});
      if (data.finished) return endRun(data.score);
      score = data.score;
      position = data.position;
      scoreEl.textContent = score;
      nextQuestion = data.question;
      if (data.correct) {
        renderQuestion(nextQuestion);
      } else {
        const review = data.review;
        correctAnswer.textContent = `${String.fromCharCode(65 + review.answer_index)}. ${review.answer}`;
        correctNote.textContent = review.explanations[review.answer_index];
        await showPenalty(data.penalty_seconds);
        if (running) renderQuestion(nextQuestion);
      }
    } catch (error) {
      if (error.status === 429 && error.payload?.wait_ms) {
        await new Promise(resolve => setTimeout(resolve, error.payload.wait_ms));
        if (running) renderQuestion(nextQuestion);
      } else {
        sourceEl.textContent = error.message;
        [...optionsEl.children].forEach(button => { button.disabled = false; });
      }
    } finally {
      answering = false;
    }
  };

  const showPenalty = async seconds => {
    penalty.hidden = false;
    const until = Date.now() + seconds * 1000;
    while (running && Date.now() < until && Date.now() < deadline) {
      penaltyCount.textContent = Math.max(1, Math.ceil((until - Date.now()) / 1000));
      await new Promise(resolve => setTimeout(resolve, 80));
    }
    penalty.hidden = true;
  };

  const endRun = async serverScore => {
    if (!running && screens.result.hidden === false) return;
    running = false;
    cancelAnimationFrame(frame);
    penalty.hidden = true;
    score = Number.isInteger(serverScore) ? serverScore : score;
    finalScore.textContent = score;
    show('result');
  };

  const submitRun = async () => {
    submitButton.disabled = true;
    submitError.hidden = true;
    const nameInput = root.querySelector('#vce-name');
    try {
      const data = await post(root.dataset.finishUrl, {token, display_name: nameInput?.value || ''});
      window.location.assign(data.detail_url);
    } catch (error) {
      if (error.status === 409) {
        setTimeout(submitRun, 600);
        return;
      }
      submitError.textContent = error.message;
      submitError.hidden = false;
      submitButton.disabled = false;
    }
  };

  startButton.addEventListener('click', startRun);
  submitButton.addEventListener('click', submitRun);
}
