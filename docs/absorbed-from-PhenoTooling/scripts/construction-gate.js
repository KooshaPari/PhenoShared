const STORAGE_KEY = 'portfolio-construction-entered';
const BOT_RE = /Googlebot|bingbot|YandexBot|DuckDuckBot|Baiduspider|Applebot|Slurp|facebookexternalhit|LinkedInBot|Twitterbot|WhatsApp|TelegramBot|Discordbot|Pinterestbot|SemrushBot|AhrefsBot|MJ12bot|DotBot|Sogou|Bytespider|GPTBot|ChatGPT-User|ClaudeBot|anthropic-ai|Omgilibot|Scrapy|curl|wget|HeadlessChrome|Lighthouse|Chrome-Lighthouse|ucbot/i;

function isBot(storage) {
  try {
    if (typeof navigator !== 'undefined' && BOT_RE.test(navigator.userAgent)) return true;
  } catch (_) { /* ignore */ }
  return false;
}

function safeGet(storage) {
  try { return storage?.getItem(STORAGE_KEY) === 'yes'; } catch { return false; }
}

function safeSet(storage) {
  try { storage?.setItem(STORAGE_KEY, 'yes'); } catch { /* session storage is optional */ }
}

function getSessionStorage() {
  try { return globalThis.sessionStorage; } catch { return undefined; }
}

export function initializeConstructionGate(document, storage = getSessionStorage()) {
  const gate = document.getElementById('construction-gate');
  const site = document.getElementById('construction-site');
  const continueLink = document.getElementById('construction-continue');
  if (!gate || !site || !continueLink) return;

  const enter = () => {
    safeSet(storage);
    gate.hidden = true;
    gate.setAttribute('aria-hidden', 'true');
    site.inert = false;
    document.documentElement.dataset.construction = 'entered';
    document.body.classList.remove('construction-locked');
    continueLink.blur();
  };

  // Bots / crawlers bypass the gate entirely to avoid CLS.
  if (isBot(storage)) {
    enter();
    return;
  }

  const hash = document.location?.hash ?? '';
  if (safeGet(storage) || document.documentElement.dataset.construction === 'entered' || hash === '#construction-entered') {
    enter();
    return;
  }

  site.inert = true;
  document.body.classList.add('construction-locked');
  continueLink.focus();
  continueLink.addEventListener('click', (event) => {
    event.preventDefault();
    if (document.defaultView?.history && document.defaultView.location) {
      document.defaultView.history.replaceState(null, '', `${document.defaultView.location.pathname}${document.defaultView.location.search}#construction-entered`);
    }
    enter();
  });
}

