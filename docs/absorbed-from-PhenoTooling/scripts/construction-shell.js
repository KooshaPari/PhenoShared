// construction-gate.css is included in the pages.css bundle — no separate link needed.
const STORAGE_KEY = 'portfolio-construction-entered';

const GATE_MARKUP = `
  <div id="construction-gate" class="construction-gate" role="dialog" aria-modal="true" aria-labelledby="construction-title" aria-describedby="construction-copy">
    <div class="construction-gate__chrome" aria-hidden="true"></div>
    <div class="construction-gate__content">
      <svg class="construction-gate__icon" viewBox="0 0 96 96" role="img" aria-label="Construction icon" focusable="false">
        <path d="M25 65 61 29l10 10-36 36H25V65Z" />
        <path d="m55 35 8-8 10 10-8 8M31 75l-9-9M27 61l8 9M43 45l9 9M51 37l9 9" />
        <path d="M17 80h62" />
      </svg>
      <p class="construction-gate__eyebrow">Technical atelier</p>
      <h1 id="construction-title">Under construction</h1>
      <p id="construction-copy">Rebuilding this portfolio; some pages and project visuals are still being refined.</p>
    </div>
    <a id="construction-continue" class="construction-gate__continue" href="#construction-entered">Continue to site</a>
    <span id="construction-entered" class="construction-gate__target" aria-hidden="true"></span>
  </div>
`;

const EARLY_SCRIPT = `<script>(function(){try{var k='${STORAGE_KEY}';if(sessionStorage.getItem(k)==='yes'){document.documentElement.dataset.construction='entered';return;}if(/Googlebot|bingbot|YandexBot|DuckDuckBot|Baiduspider|Applebot|Slurp|facebookexternalhit|LinkedInBot|Twitterbot|WhatsApp|TelegramBot|Discordbot|Pinterestbot|SemrushBot|AhrefsBot|MJ12bot|DotBot|Sogou|Bytespider|GPTBot|ChatGPT-User|ClaudeBot|anthropic-ai|Omgilibot|Scrapy|curl|wget|HeadlessChrome|Lighthouse|Chrome-Lighthouse|ucbot/i.test(navigator.userAgent))document.documentElement.dataset.construction='entered';}catch(_){}}());</script><style>html[data-construction="entered"] #construction-gate{display:none!important}html[data-construction="entered"] #construction-site{inset:auto}</style>`;

export function injectConstructionGate(html) {
  if (html.includes('id="construction-gate"')) return html;
  // No separate CSS link — construction-gate.css is in the pages.css bundle.
  const withScript = html.replace('</head>', `  ${EARLY_SCRIPT}\n</head>`);
  return withScript.replace(/(<body[^>]*>)/, `$1${GATE_MARKUP}\n  <div id="construction-site">`).replace('</body>', '  </div>\n</body>');
}
