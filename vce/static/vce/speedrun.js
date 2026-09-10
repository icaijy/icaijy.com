(() => {
  const root = document.getElementById('vce-speedrun');
  if (!root) return;

  const intro = document.getElementById('vce-intro');
  const game = document.getElementById('vce-game');
  const result = document.getElementById('vce-result');
  const startButton = document.getElementById('vce-start');
  const againButton = document.getElementById('vce-again');
  const displayName = document.getElementById('vce-display-name');
  const scoreNode = document.getElementById('vce-score');
  const wrongNode = document.getElementById('vce-wrong');
  const timerNode = document.getElementById('vce-timer');
  const timebarFill = document.getElementById('vce-timebar-fill');
  const topicNode = document.getElementById('vce-question-topic');
  const sourceNode = document.getElementById('vce-question-source');
  const stemNode = document.getElementById('vce-question-stem');
  const optionsNode = document.getElementById('vce-options');
  const penalty = document.getElementById('vce-penalty');
  const penaltyCount = document.getElementById('vce-penalty-count');
  const penaltyCorrect = document.getElementById('vce-penalty-correct');
  const penaltyExplanation = document.getElementById('vce-penalty-explanation');
  const resultScore = document.getElementById('vce-result-score');
  const resultCopy = document.getElementById('vce-result-copy');
  const reviewLast = document.getElementById('vce-review-last');
  const reviewBody = document.getElementById('vce-review-body');
  const reviewTitle = document.getElementById('vceReviewTitle');
  const modalElement = document.getElementById('vceReviewModal');

  const runDuration = Number(root.dataset.runSeconds || 60) * 1000;
  let currentQuestion = null;
  let clientDeadline = 0;
  let timerHandle = null;
  let finishing = false;
  let accepting = false;
  let lastAttemptId = null;
  let score = 0;
  let wrong = 0;

  function csrfToken() {
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  async function postJSON(url, payload = {}) {
    const response = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken(),
      },
      body: JSON.stringify(payload),
    });
    let body = {};
    try { body = await response.json(); } catch (_) {}
    if (!response.ok) {
      const error = new Error(body.error || `Request failed (${response.status})`);
      error.payload = body;
      error.status = response.status;
      throw error;
    }
    return body;
  }

  function showState(which) {
    intro.hidden = which !== 'intro';
    game.hidden = which !== 'game';
    result.hidden = which !== 'result';
  }

  function resyncTimer(remainingMs) {
    clientDeadline = Date.now() + Math.max(0, Number(remainingMs || 0));
  }

  function updateHUD() {
    const remaining = Math.max(0, clientDeadline - Date.now());
    timerNode.textContent = (remaining / 1000).toFixed(1);
    const ratio = Math.min(1, remaining / runDuration);
    timebarFill.style.transform = `scaleX(${ratio})`;
    scoreNode.textContent = score;
    wrongNode.textContent = wrong;
    if (remaining <= 0 && !finishing) finishRun();
  }

  function startTicker() {
    clearInterval(timerHandle);
    timerHandle = setInterval(updateHUD, 50);
    updateHUD();
  }

  function setOptionsDisabled(disabled) {
    optionsNode.querySelectorAll('button').forEach(button => { button.disabled = disabled; });
  }

  function renderQuestion(question) {
    currentQuestion = question;
    topicNode.textContent = question.topic_label || question.topic;
    sourceNode.textContent = question.source || '';
    stemNode.textContent = question.stem;
    optionsNode.replaceChildren();
    ['A', 'B', 'C', 'D'].forEach((letter, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'vce-option';
      button.dataset.choice = letter;

      const badge = document.createElement('span');
      badge.className = 'vce-option-letter';
      badge.textContent = letter;

      const text = document.createElement('span');
      text.className = 'vce-option-text';
      text.textContent = question.options[index];

      button.append(badge, text);
      button.addEventListener('click', () => submitChoice(letter));
      optionsNode.appendChild(button);
    });
    accepting = true;
  }

  async function beginRun() {
    startButton.disabled = true;
    againButton.disabled = true;
    try {
      const payload = await postJSON(root.dataset.startUrl, {
        display_name: displayName ? displayName.value : '',
      });
      score = 0;
      wrong = 0;
      lastAttemptId = null;
      finishing = false;
      penalty.hidden = true;
      resyncTimer(payload.remaining_ms);
      renderQuestion(payload.question);
      showState('game');
      startTicker();
    } catch (error) {
      window.alert(error.message);
    } finally {
      startButton.disabled = false;
      againButton.disabled = false;
    }
  }

  async function submitChoice(choice) {
    if (!accepting || !currentQuestion || finishing) return;
    accepting = false;
    setOptionsDisabled(true);
    try {
      const payload = await postJSON(root.dataset.answerUrl, {
        question_id: currentQuestion.id,
        choice,
      });
      if (payload.finished) {
        showFinished(payload);
        return;
      }
      score = payload.score;
      wrong = payload.wrong_count;
      resyncTimer(payload.remaining_ms);
      updateHUD();

      if (payload.correct) {
        renderQuestion(payload.next_question);
        return;
      }

      penaltyCorrect.textContent = `Correct: ${payload.correct_answer} · ${payload.correct_option}`;
      const pieces = [];
      if (payload.selected_explanation && payload.selected_explanation !== payload.explanation) {
        pieces.push(payload.selected_explanation);
      }
      if (payload.explanation) pieces.push(payload.explanation);
      penaltyExplanation.textContent = pieces.join(' ') || 'Correct answer shown above.';
      penalty.hidden = false;

      const penaltyEnds = Date.now() + Number(payload.penalty_ms || 3000);
      const tickPenalty = () => {
        const left = Math.max(0, penaltyEnds - Date.now());
        penaltyCount.textContent = (left / 1000).toFixed(1);
        if (left <= 0 || Date.now() >= clientDeadline) {
          penalty.hidden = true;
          if (Date.now() < clientDeadline && !finishing) renderQuestion(payload.next_question);
          return;
        }
        requestAnimationFrame(tickPenalty);
      };
      tickPenalty();
    } catch (error) {
      if (error.status === 429 && error.payload?.penalty_remaining_ms) {
        const wait = Math.max(50, error.payload.penalty_remaining_ms);
        setTimeout(() => {
          accepting = true;
          setOptionsDisabled(false);
        }, wait);
      } else {
        accepting = true;
        setOptionsDisabled(false);
        window.alert(error.message);
      }
    }
  }

  async function finishRun() {
    if (finishing) return;
    finishing = true;
    accepting = false;
    setOptionsDisabled(true);
    try {
      const payload = await postJSON(root.dataset.finishUrl, {});
      if (!payload.finished && payload.remaining_ms > 0) {
        finishing = false;
        resyncTimer(payload.remaining_ms);
        setTimeout(finishRun, payload.remaining_ms + 80);
        return;
      }
      showFinished(payload);
    } catch (error) {
      if (error.status === 409 && error.payload?.remaining_ms > 0) {
        finishing = false;
        resyncTimer(error.payload.remaining_ms);
        setTimeout(finishRun, error.payload.remaining_ms + 80);
        return;
      }
      finishing = false;
      window.alert(error.message);
    }
  }

  function showFinished(payload) {
    clearInterval(timerHandle);
    penalty.hidden = true;
    lastAttemptId = payload.attempt_id;
    score = payload.score;
    wrong = payload.wrong_count;
    resultScore.textContent = score;
    resultCopy.textContent = `${wrong} wrong answer${wrong === 1 ? '' : 's'} · run saved to the Hall of Fame.`;
    reviewLast.disabled = !lastAttemptId;
    showState('result');
  }

  function reviewClass(question) {
    if (question.selected == null) return 'skipped';
    return question.correct ? 'good' : 'bad';
  }

  async function openReview(attemptId) {
    if (!attemptId) return;
    reviewBody.innerHTML = '<div class="vce-empty">Loading…</div>';
    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
    modal.show();
    try {
      const url = root.dataset.detailTemplate.replace('__ID__', attemptId);
      const response = await fetch(url, {credentials: 'same-origin'});
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'Could not load run.');
      reviewTitle.textContent = `${payload.player} · ${payload.score} correct`;
      reviewBody.replaceChildren();

      const summary = document.createElement('div');
      summary.className = 'vce-review-summary';
      summary.textContent = `${payload.score} correct · ${payload.wrong_count} wrong · ${payload.questions.length} questions shown`;
      reviewBody.appendChild(summary);

      payload.questions.forEach((question, index) => {
        const item = document.createElement('article');
        item.className = 'vce-review-item';

        const head = document.createElement('div');
        head.className = 'vce-review-qhead';
        const left = document.createElement('span');
        left.textContent = `#${index + 1} · ${question.id} · ${question.topic_label}`;
        const source = document.createElement('span');
        source.textContent = question.source;
        head.append(left, source);

        const h3 = document.createElement('h3');
        h3.textContent = question.stem;

        const answer = document.createElement('div');
        answer.className = `vce-review-answer ${reviewClass(question)}`;
        if (question.selected == null) {
          answer.textContent = `Not answered · correct ${question.correct_answer}`;
        } else if (question.correct) {
          answer.textContent = `✓ Your answer: ${question.selected}`;
        } else {
          answer.textContent = `✕ Your answer: ${question.selected} · correct ${question.correct_answer}`;
        }

        const explanation = document.createElement('p');
        explanation.className = 'vce-review-explanation';
        explanation.textContent = question.explanation || '';

        item.append(head, h3, answer, explanation);
        reviewBody.appendChild(item);
      });
    } catch (error) {
      reviewBody.innerHTML = '';
      const message = document.createElement('div');
      message.className = 'vce-empty';
      message.textContent = error.message;
      reviewBody.appendChild(message);
    }
  }

  startButton.addEventListener('click', beginRun);
  againButton.addEventListener('click', beginRun);
  reviewLast.addEventListener('click', () => openReview(lastAttemptId));
  document.querySelectorAll('.vce-review-link').forEach(button => {
    button.addEventListener('click', () => openReview(button.dataset.attemptId));
  });
})();
