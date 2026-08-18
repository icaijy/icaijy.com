import { installMp4Download } from './mp4_download.js';

const detail = document.getElementById('hof-detail');
if (detail) {
  const tr = (message) => typeof gettext === 'function' ? gettext(message) : message;
  const shareText = document.getElementById('hof-share-text');
  const shareButton = document.getElementById('share-hof');
  const copyButton = document.getElementById('copy-hof-link');
  const status = document.getElementById('hof-share-status');
  const url = detail.dataset.entryUrl;
  const score = Number(detail.dataset.score);
  const isLegClaps = detail.dataset.gameMode === 'leg_claps';
  const isVoice = detail.dataset.gameMode === 'voice_67';
  const blocks = score > 0
    ? `${'🟩'.repeat(Math.min(score, 20))}${score > 20 ? ` +${score - 20}` : ''}`
    : '⬜';
  const fallbackHeadline = isLegClaps
    ? `${detail.dataset.username} made ${score} Tung Tung Leg Claps in 20 seconds! 🥒`
    : isVoice
      ? `${detail.dataset.username} clearly said “six seven” ${score} times in 20 seconds! 🗣️`
      : `${detail.dataset.username} made ${score} 6️⃣7️⃣ moves in 20 seconds! 🔥`;
  // This sentence is already translated by Django in the visible page copy.
  const headline = detail.querySelector('.pb-2 .fw-bold')?.textContent.trim() || fallbackHeadline;
  const text = `${headline}\n${blocks}\n${url}`;
  if (shareText) shareText.value = text;

  const downloadButton = detail.querySelector('a[href*="?download=1"]');
  const safeName = detail.dataset.username.replace(/[^a-z0-9_-]+/gi, '-').replace(/^-+|-+$/g, '') || 'run';
  const downloadSlug = isLegClaps ? 'tung-tung-leg-claps' : isVoice ? 'six-seven-voice' : '67';
  installMp4Download(downloadButton, {
    filename: `${downloadSlug}-${safeName}-${score}.webm`,
    onStatus(message) {
      if (status) status.textContent = message;
    },
    onError(error) {
      if (status) status.textContent = `MP4 download failed: ${error.message}`;
    },
  });

  async function copyShareMessage() {
    if (!shareText || !copyButton) return;
    try {
      if (navigator.clipboard?.writeText && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        shareText.select();
        shareText.setSelectionRange(0, shareText.value.length);
        if (!document.execCommand('copy')) throw new Error('Copy command was rejected.');
      }
      copyButton.textContent = tr('Copied! 🎉');
      if (status) {
        status.textContent = isLegClaps
          ? tr('Full result copied! The knee evidence is ready for deployment.')
          : isVoice
            ? tr('Full result copied! The voice evidence is ready for deployment.')
            : tr('Full result copied! The 6️⃣7️⃣ evidence is ready for deployment.');
      }
    } catch (error) {
      shareText.select();
      if (status) status.textContent = tr('Automatic copy failed. Select the message and copy it manually.');
    }
    window.setTimeout(() => { copyButton.textContent = tr('Copy share message'); }, 1500);
  }

  shareButton?.addEventListener('click', async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title: document.title, text });
        if (status) status.textContent = tr('Result launched into the world! 🚀');
        return;
      } catch (error) {
        if (error.name === 'AbortError') return;
      }
    }
    await copyShareMessage();
  });
  copyButton?.addEventListener('click', copyShareMessage);
}
