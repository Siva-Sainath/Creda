const ATS_HOST_PATTERNS = [
  { provider: 'greenhouse', re: /greenhouse\.io|\.jobs\/search\?gh_jid=/i },
  { provider: 'lever', re: /jobs\.lever\.co/i },
  { provider: 'ashby', re: /jobs\.ashbyhq\.com/i },
];

const JOB_LINK_RE = /(https?:\/\/[^\s"'<>]+(?:gh_jid=\d+|jobs\.lever\.co\/[^/]+\/[0-9a-f-]{36}|jobs\.ashbyhq\.com\/[^/]+\/[0-9a-f-]{36}|greenhouse\.io\/[^/]+\/jobs\/\d+)[^\s"'<>]*)/gi;

function detectProvider(url) {
  for (const entry of ATS_HOST_PATTERNS) {
    if (entry.re.test(url)) return entry.provider;
  }
  return '';
}

function collectJobLinks(root) {
  const links = new Set();
  root.querySelectorAll('a[href]').forEach((a) => {
    try {
      const href = new URL(a.getAttribute('href'), document.baseURI).href;
      if (JOB_LINK_RE.test(href) || /gh_jid=\d+/.test(href)) links.add(href);
    } catch (e) {}
  });
  const pageUrl = window.location.href;
  if (/gh_jid=\d+/.test(pageUrl) || detectProvider(pageUrl)) links.add(pageUrl);
  return [...links];
}

function pageTitleHint() {
  const h1 = document.querySelector('h1');
  if (h1 && h1.textContent.trim()) return h1.textContent.trim();
  const og = document.querySelector('meta[property="og:title"]');
  if (og && og.content) return og.content.trim();
  return document.title || '';
}

function pageTextSnippet(maxLen = 4000) {
  const main = document.querySelector('main, article, [role="main"], .job-description, .content');
  const text = (main ? main.innerText : document.body.innerText || '').replace(/\s+/g, ' ').trim();
  return text.slice(0, maxLen);
}

function buildPageContext() {
  const url = window.location.href;
  const provider = detectProvider(url);
  const jobLinks = collectJobLinks(document);
  const selection = window.getSelection().toString().trim();
  return {
    url,
    title: pageTitleHint(),
    provider,
    jobLinks,
    selection,
    snippet: selection ? '' : pageTextSnippet(),
  };
}
