const detail = document.getElementById('hof-detail');
if (detail) {
  const shareText = document.getElementById('hof-share-text');
  const shareButton = document.getElementById('share-hof');
  const copyButton = document.getElementById('copy-hof-link');
  const status = document.getElementById('hof-share-status');
  const url = detail.dataset.entryUrl;
  const text = `${detail.dataset.username} made ${detail.dataset.score} 6️⃣7️⃣ moves in 20 seconds.\nWatch the run and try to beat it:\n${url}`;
  shareText.value = text;

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(url);
      status.textContent = 'Permanent specimen link copied.';
    } catch (error) {
      shareText.select();
      document.execCommand('copy');
      status.textContent = 'Share text copied.';
    }
  }

  shareButton.addEventListener('click', async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title: '67 Hall of Fame', text, url });
        status.textContent = 'Evidence distributed.';
        return;
      } catch (error) {
        if (error.name === 'AbortError') return;
      }
    }
    await copyLink();
  });
  copyButton.addEventListener('click', copyLink);
}
