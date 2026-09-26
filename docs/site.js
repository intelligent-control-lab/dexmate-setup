'use strict';
const chinese = document.documentElement.lang === 'zh-CN';
document.querySelectorAll('.copy').forEach(button => {
  button.textContent = chinese ? '复制' : 'Copy';
  button.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(button.parentElement.querySelector('pre').innerText);
      button.textContent = chinese ? '已复制' : 'Copied';
    } catch {
      button.textContent = chinese ? '请手动选择复制' : 'Select text to copy';
    }
    setTimeout(() => { button.textContent = chinese ? '复制' : 'Copy'; }, 1800);
  });
});
const languageLink = document.querySelector('.language');
if (languageLink) languageLink.addEventListener('click', () => {
  languageLink.href = languageLink.href.split('#')[0] + location.hash;
});
const links = Array.from(document.querySelectorAll('nav a'));
if ('IntersectionObserver' in window) {
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      for (const link of links) {
        const active = link.hash === '#' + entry.target.id;
        link.classList.toggle('active', active);
        if (active) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
      }
    }
  }, {rootMargin: '-15% 0px -65% 0px'});
  document.querySelectorAll('main section').forEach(section => observer.observe(section));
}
