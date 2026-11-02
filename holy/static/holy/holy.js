(() => {
  const panel = document.querySelector('#hc-sync');
  if (!panel || panel.dataset.requested !== 'yes') return;
  const line = document.querySelector('#hc-sync-status');
  const url = new URL(panel.dataset.statusUrl, location.origin);
  url.searchParams.set('cf', panel.dataset.cf);
  url.searchParams.set('ac', panel.dataset.ac);
  let timer;
  let failures = 0;
  const poll = async () => {
    if (document.hidden) return;
    try {
      const response = await fetch(url, { headers: { Accept: 'application/json' } });
      if (!response.ok) throw new Error('Status unavailable');
      const data = await response.json();
      const account = data.accounts[panel.dataset.platform];
      if (account?.complete) { clearInterval(timer); location.reload(); return; }
      line.textContent = account?.error
        ? `Sync failed: ${account.error}. The collector will retry with backoff.`
        : `Syncing submission history · ${data.backlog} requests queued · ${panel.dataset.rateSummary}`;
      failures = 0;
    } catch {
      if (++failures >= 3) {
        clearInterval(timer);
        line.textContent = 'Progress is temporarily unavailable. The collector is still running independently; try refreshing later.';
      }
    }
  };
  timer = setInterval(poll, 30000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); });
})();
