/* Drop-in news renderer. It expects an element with id="news" or class="news-grid". */
(function () {
  const target = document.querySelector('#news, .news-grid');
  if (!target) return;
  const api = (window.SERVERGUARD_NEWS_API || 'https://api.serverguard.site') + '/api/news';
  const escapeHtml = value => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const render = posts => {
    target.innerHTML = posts.length ? posts.map(post => `<article class="news-card">${post.image_url ? `<img src="${escapeHtml(post.image_url)}" alt="">` : ''}<span class="news-category">${escapeHtml(post.category)}</span><h3>${escapeHtml(post.title)}</h3><p>${escapeHtml(post.content).replace(/\n/g, '<br>')}</p><time datetime="${escapeHtml(post.published_at)}">${new Date(post.published_at).toLocaleDateString()}</time></article>`).join('') : '<p class="news-empty">No news yet.</p>';
  };
  const load = () => fetch(api, { headers: { Accept: 'application/json' }, cache: 'no-store' }).then(r => { if (!r.ok) throw Error(); return r.json(); }).then(data => render(data.posts || [])).catch(() => { if (!target.children.length) target.innerHTML = '<p class="news-empty">News is temporarily unavailable.</p>'; });
  load();
  setInterval(load, 20000);
})();
