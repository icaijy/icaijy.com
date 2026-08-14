const detail = document.getElementById('hof-detail');
if (detail) {
  const shareText = document.getElementById('hof-share-text');
  const shareButton = document.getElementById('share-hof');
  const copyButton = document.getElementById('copy-hof-link');
  const status = document.getElementById('hof-share-status');
  const url = detail.dataset.entryUrl;
  const score = Number(detail.dataset.score);
  const blocks = score > 0
    ? `${'🟩'.repeat(Math.min(score, 20))}${score > 20 ? ` +${score - 20}` : ''}`
    : '⬜';
  const text = `${detail.dataset.username} made ${score} 6️⃣7️⃣ moves in 20 seconds! 🔥\n${blocks}\nSIX SEVEN!\nWatch the run and try to beat it!\n${url}`;
  shareText.value = text;

  async function copyShareMessage() {
    try {
      if (navigator.clipboard?.writeText && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        shareText.select();
        shareText.setSelectionRange(0, shareText.value.length);
        if (!document.execCommand('copy')) throw new Error('Copy command was rejected.');
      }
      copyButton.textContent = 'Copied! 🎉';
      status.textContent = 'Full result copied! The 6️⃣7️⃣ evidence is ready for deployment.';
    } catch (error) {
      shareText.select();
      status.textContent = 'Automatic copy failed. Select the message and copy it manually.';
    }
    window.setTimeout(() => { copyButton.textContent = 'Copy share message'; }, 1500);
  }

  shareButton.addEventListener('click', async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title: '67 Hall of Fame', text });
        status.textContent = 'Result launched into the world! 🚀';
        return;
      } catch (error) {
        if (error.name === 'AbortError') return;
      }
    }
    await copyShareMessage();
  });
  copyButton.addEventListener('click', copyShareMessage);
}
