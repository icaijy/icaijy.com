function csrfToken(root = document) {
  const field = root.closest?.('form')?.querySelector('[name="csrfmiddlewaretoken"]')
    || document.querySelector('[name="csrfmiddlewaretoken"]');
  if (field?.value) return field.value;
  const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : '';
}

function replaceSelection(textarea, before, after = before, placeholder = 'text') {
  const start = textarea.selectionStart ?? textarea.value.length;
  const end = textarea.selectionEnd ?? start;
  const selected = textarea.value.slice(start, end) || placeholder;
  const replacement = `${before}${selected}${after}`;
  textarea.setRangeText(replacement, start, end, 'select');
  textarea.selectionStart = start + before.length;
  textarea.selectionEnd = start + before.length + selected.length;
  textarea.dispatchEvent(new Event('input', { bubbles: true }));
  textarea.focus();
}

function quoteSelection(textarea) {
  const start = textarea.selectionStart ?? textarea.value.length;
  const end = textarea.selectionEnd ?? start;
  const selected = textarea.value.slice(start, end) || 'quoted text';
  const replacement = selected.split('\n').map((line) => `> ${line}`).join('\n');
  textarea.setRangeText(replacement, start, end, 'end');
  textarea.dispatchEvent(new Event('input', { bubbles: true }));
  textarea.focus();
}

function linkSelection(textarea) {
  const start = textarea.selectionStart ?? textarea.value.length;
  const end = textarea.selectionEnd ?? start;
  const selected = textarea.value.slice(start, end) || 'link text';
  const replacement = `[${selected}](https://example.com)`;
  textarea.setRangeText(replacement, start, end, 'end');
  const urlStart = start + selected.length + 3;
  textarea.selectionStart = urlStart;
  textarea.selectionEnd = urlStart + 'https://example.com'.length;
  textarea.dispatchEvent(new Event('input', { bubbles: true }));
  textarea.focus();
}

function initialiseEditor(editor) {
  const textarea = editor.querySelector('textarea');
  const previewPanel = editor.querySelector('[data-md-preview-panel]');
  const previewButton = editor.querySelector('[data-md-preview]');
  const writeButton = editor.querySelector('[data-md-write]');
  const counter = editor.querySelector('[data-md-count]');
  const errorNode = editor.querySelector('[data-md-error]');
  if (!textarea || !previewPanel || !previewButton || !writeButton) return;

  const showWrite = () => {
    textarea.hidden = false;
    previewPanel.hidden = true;
    writeButton.classList.add('btn-dark', 'active');
    writeButton.classList.remove('btn-outline-dark');
    previewButton.classList.remove('btn-dark', 'active');
    previewButton.classList.add('btn-outline-dark');
  };

  const showPreview = async () => {
    errorNode.textContent = '';
    previewButton.disabled = true;
    previewButton.textContent = 'Previewing…';
    try {
      const form = new FormData();
      form.append('body', textarea.value);
      const response = await fetch(editor.dataset.previewUrl, {
        method: 'POST',
        body: form,
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': csrfToken(editor),
          'X-Requested-With': 'XMLHttpRequest',
        },
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'Could not render preview.');
      previewPanel.innerHTML = payload.html;
      textarea.hidden = true;
      previewPanel.hidden = false;
      previewButton.classList.add('btn-dark', 'active');
      previewButton.classList.remove('btn-outline-dark');
      writeButton.classList.remove('btn-dark', 'active');
      writeButton.classList.add('btn-outline-dark');
    } catch (error) {
      errorNode.textContent = error.message;
    } finally {
      previewButton.disabled = false;
      previewButton.textContent = 'Preview';
    }
  };

  editor.querySelectorAll('[data-md-action]').forEach((button) => {
    button.addEventListener('click', () => {
      showWrite();
      const action = button.dataset.mdAction;
      if (action === 'bold') replaceSelection(textarea, '**', '**', 'bold text');
      else if (action === 'italic') replaceSelection(textarea, '*', '*', 'italic text');
      else if (action === 'code') replaceSelection(textarea, '`', '`', 'code');
      else if (action === 'quote') quoteSelection(textarea);
      else if (action === 'link') linkSelection(textarea);
    });
  });

  previewButton.addEventListener('click', showPreview);
  writeButton.addEventListener('click', () => {
    showWrite();
    textarea.focus();
  });

  const updateCount = () => {
    if (counter) counter.textContent = String(textarea.value.length);
  };
  textarea.addEventListener('input', updateCount);
  updateCount();

  editor.showWrite = showWrite;
}

document.querySelectorAll('[data-markdown-editor]').forEach(initialiseEditor);

// The mature pose runner owns the video upload FormData. Keep it untouched and
// attach the optional submission comment only to that one HOF request.
function installSubmissionCommentBridge() {
  const app = document.getElementById('counter-app');
  const textarea = document.getElementById('hof-submission-comment');
  if (!app || !textarea || !app.dataset.submitUrl || window.__hofSubmissionCommentBridge) return;

  const nativeFetch = window.fetch.bind(window);
  const submitUrl = new URL(app.dataset.submitUrl, window.location.href).href;
  window.__hofSubmissionCommentBridge = true;
  window.fetch = (input, init = {}) => {
    try {
      const rawUrl = typeof input === 'string' || input instanceof URL
        ? String(input)
        : input?.url;
      const requestUrl = rawUrl ? new URL(rawUrl, window.location.href).href : '';
      if (
        requestUrl === submitUrl
        && init.body instanceof FormData
        && !init.body.has('submission_comment')
      ) {
        const body = textarea.value.trim();
        if (body) init.body.append('submission_comment', body);
      }
    } catch (error) {
      console.warn('Could not attach the HOF submission comment.', error);
    }
    return nativeFetch(input, init);
  };
}
installSubmissionCommentBridge();

const commentBody = document.getElementById('hof-comment-body');
document.querySelectorAll('[data-comment-reply]').forEach((button) => {
  button.addEventListener('click', () => {
    if (!commentBody) return;
    const editor = commentBody.closest('[data-markdown-editor]');
    editor?.showWrite?.();
    const prefix = `@${button.dataset.author} `;
    const joiner = commentBody.value && !commentBody.value.endsWith('\n') ? '\n' : '';
    commentBody.value += `${joiner}${prefix}`;
    commentBody.dispatchEvent(new Event('input', { bubbles: true }));
    document.getElementById('hof-comment-form')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    commentBody.focus();
    commentBody.selectionStart = commentBody.selectionEnd = commentBody.value.length;
  });
});

const commentForm = document.getElementById('hof-comment-form');
if (commentForm) {
  commentForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = document.getElementById('post-hof-comment');
    const errorNode = document.getElementById('hof-comment-error');
    errorNode.textContent = '';
    if (button) {
      button.disabled = true;
      button.textContent = 'Posting…';
    }
    try {
      const response = await fetch(commentForm.action, {
        method: 'POST',
        body: new FormData(commentForm),
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': csrfToken(commentForm),
          'X-Requested-With': 'XMLHttpRequest',
        },
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'Could not post comment.');
      window.location.href = payload.url;
    } catch (error) {
      errorNode.textContent = error.message;
      if (button) {
        button.disabled = false;
        button.innerHTML = '<i class="fa-regular fa-comment me-1"></i>Post comment';
      }
    }
  });
}
