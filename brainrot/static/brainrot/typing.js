(() => {
  const app = document.getElementById('typing-app');
  if (!app) return;

  const viewport = document.getElementById('typing-viewport');
  const stream = document.getElementById('typing-stream');
  const timeEl = document.getElementById('typing-time');
  const wpmEl = document.getElementById('typing-wpm');
  const accuracyEl = document.getElementById('typing-accuracy');
  const result = document.getElementById('typing-result');
  const durationButtons = [...document.querySelectorAll('[data-duration]')];

  let duration = 30;
  let groups = [];
  let charElements = [];
  let position = 0;
  let correct = 0;
  let errors = 0;
  let startedAt = null;
  let timerId = null;
  let finished = false;

  function randomGroup() {
    const bit = new Uint8Array(1);
    crypto.getRandomValues(bit);
    return bit[0] & 1 ? '67' : '61';
  }

  function appendGroups(amount) {
    const fragment = document.createDocumentFragment();
    for (let i = 0; i < amount; i += 1) {
      const value = randomGroup();
      groups.push(value);
      const groupEl = document.createElement('span');
      groupEl.className = 'typing-group';
      for (const character of value) {
        const charEl = document.createElement('span');
        charEl.className = 'typing-char';
        charEl.textContent = character;
        charElements.push(charEl);
        groupEl.appendChild(charEl);
      }
      fragment.appendChild(groupEl);
    }
    stream.appendChild(fragment);
  }

  function targetAt(index) {
    const group = groups[Math.floor(index / 2)];
    return group[index % 2];
  }

  function elapsedSeconds() {
    return startedAt ? Math.min((performance.now() - startedAt) / 1000, duration) : 0;
  }

  function stats() {
    const typed = correct + errors;
    const elapsed = elapsedSeconds();
    const wpm = elapsed > 0 ? Math.round((typed / 5) / (elapsed / 60)) : 0;
    const accuracy = typed > 0 ? Math.round((correct / typed) * 100) : 100;
    return { typed, elapsed, wpm, accuracy };
  }

  function updateStats() {
    const current = stats();
    timeEl.textContent = Math.max(0, Math.ceil(duration - current.elapsed));
    wpmEl.textContent = current.wpm;
    accuracyEl.textContent = `${current.accuracy}%`;
  }

  function updateCaret() {
    charElements.forEach((el) => el.classList.remove('current'));
    if (!finished && charElements[position]) {
      charElements[position].classList.add('current');
      const active = charElements[position];
      const viewportRect = viewport.getBoundingClientRect();
      const activeRect = active.getBoundingClientRect();
      if (activeRect.bottom > viewportRect.bottom - 42) {
        stream.style.transform = `translateY(-${Math.max(0, active.offsetTop - 42)}px)`;
      }
    }
  }

  function finish() {
    if (finished) return;
    finished = true;
    clearInterval(timerId);
    updateStats();
    timeEl.textContent = '0';
    updateCaret();

    const current = stats();
    const completedGroups = Math.floor(position / 2);
    const completed = groups.slice(0, completedGroups);
    const count61 = completed.filter((value) => value === '61').length;
    const count67 = completedGroups - count61;

    document.getElementById('result-wpm').textContent = current.wpm;
    document.getElementById('result-accuracy').textContent = `${current.accuracy}%`;
    document.getElementById('result-characters').textContent = current.typed;
    document.getElementById('result-groups').textContent = completedGroups;
    document.getElementById('result-61').textContent = count61;
    document.getElementById('result-67').textContent = count67;

    let verdict = 'Statistically significant brainrot.';
    if (current.wpm === 67) verdict = 'Exactly 67 WPM. The prophecy has cleared peer review.';
    else if (current.wpm === 61) verdict = 'Exactly 61 WPM. Close enough to be culturally important.';
    else if (current.accuracy === 67) verdict = '67% accuracy. Incorrect in precisely the correct way.';
    else if (completedGroups >= 67) verdict = '67 groups survived contact with the keyboard.';
    document.getElementById('typing-verdict').textContent = verdict;
    result.hidden = false;
  }

  function start() {
    if (startedAt || finished) return;
    startedAt = performance.now();
    timerId = window.setInterval(() => {
      updateStats();
      if (elapsedSeconds() >= duration) finish();
    }, 100);
  }

  function handleKey(event) {
    if (event.key === 'Backspace') {
      event.preventDefault();
      return;
    }
    if (event.ctrlKey || event.metaKey || event.altKey || event.key.length !== 1) return;
    if (!['1', '6', '7'].includes(event.key) || finished) return;
    event.preventDefault();
    start();

    const target = targetAt(position);
    const currentEl = charElements[position];
    if (event.key === target) {
      correct += 1;
      currentEl.classList.add('correct');
    } else {
      errors += 1;
      currentEl.classList.add('error');
      currentEl.dataset.typed = event.key;
      currentEl.title = `typed ${event.key}`;
    }
    position += 1;
    if (groups.length - Math.floor(position / 2) < 50) appendGroups(80);
    updateStats();
    updateCaret();
  }

  function reset() {
    clearInterval(timerId);
    groups = [];
    charElements = [];
    position = 0;
    correct = 0;
    errors = 0;
    startedAt = null;
    timerId = null;
    finished = false;
    stream.replaceChildren();
    stream.style.transform = '';
    result.hidden = true;
    appendGroups(120);
    timeEl.textContent = duration;
    wpmEl.textContent = '0';
    accuracyEl.textContent = '100%';
    updateCaret();
    viewport.focus();
  }

  viewport.addEventListener('keydown', handleKey);
  document.getElementById('typing-restart').addEventListener('click', reset);
  durationButtons.forEach((button) => {
    button.addEventListener('click', () => {
      duration = Number(button.dataset.duration);
      durationButtons.forEach((item) => item.classList.toggle('active', item === button));
      reset();
    });
  });

  reset();
})();
