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
        ? `同步遇到问题：${account.error}。后台将退避重试。`
        : `历史提交同步中 · ${data.backlog} 个请求待处理 · ${panel.dataset.rateSummary}`;
      failures = 0;
    } catch {
      if (++failures >= 3) {
        clearInterval(timer);
        line.textContent = '暂时无法取得进度。后台队列独立运行，可以稍后刷新页面。';
      }
    }
  };
  timer = setInterval(poll, 30000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) poll(); });
})();
