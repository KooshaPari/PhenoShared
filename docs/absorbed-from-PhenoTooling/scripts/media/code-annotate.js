/**
 * Code Annotation System
 * ─────────────────────
 * Enhanced code display with line numbers, annotation markers,
 * callout badges, syntax highlighting, and copy-to-clipboard.
 *
 * Annotation markers (parsed from code comments):
 *   // [!highlight]           — highlight the line with teal bg
 *   // [!annotation:text]     — tooltip/popover with annotation text
 *   // [!callout:label]       — numbered callout badge in left margin
 *
 * @module code-annotate
 */

/* ------------------------------------------------------------------ */
/*  Language detection                                                 */
/* ------------------------------------------------------------------ */

const LANG_ALIASES = {
  js: 'javascript', ts: 'typescript', tsx: 'typescript',
  jsx: 'javascript', py: 'python', rb: 'ruby',
  sh: 'bash', shell: 'bash', zsh: 'bash',
  yml: 'yaml', md: 'markdown', rs: 'rust',
  cs: 'csharp', kt: 'kotlin', go: 'go',
  dockerfile: 'dockerfile',
};

function detectLanguage(codeEl) {
  const cls = codeEl.className || '';
  const m = cls.match(/language-(\w+)/);
  if (m) return LANG_ALIASES[m[1]] || m[1];
  if (codeEl.dataset.lang) return codeEl.dataset.lang;
  return null;
}

/* ------------------------------------------------------------------ */
/*  Syntax tokeniser (CSS-class-based, no runtime library)             */
/* ------------------------------------------------------------------ */

const TOKEN_RULES = [
  // Order matters: comments and strings first to prevent inner matches
  { re: /(\/\/.*$|\/\*[\s\S]*?\*\/|#(?!{).*$)/gm, cls: 'tok-cmt' },
  { re: /("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|`(?:[^`\\]|\\.)*`)/g, cls: 'tok-str' },
  { re: /\b(\d+(?:\.\d+)?(?:_\d+)?)\b/g, cls: 'tok-num' },
  { re: /(@\w+)/g, cls: 'tok-deco' },
  { re: /\b(function|return|if|else|for|while|do|switch|case|break|continue|class|extends|new|this|super|import|from|export|default|const|let|var|async|await|try|catch|finally|throw|typeof|instanceof|in|of|yield|void|delete|static|get|set)\b/g, cls: 'tok-kw' },
  { re: /\b(def|self|None|True|False|and|or|not|is|with|as|elif|lambda|pass|raise|from|import|class|yield|async|await|global|nonlocal|assert|del|print)\b/g, cls: 'tok-kw' },
  { re: /\b(fn|pub|struct|impl|trait|enum|mod|use|crate|self|mut|ref|match|move|loop|where|type|const|static|unsafe|extern|async|await|dyn|as|super)\b/g, cls: 'tok-kw' },
  { re: /\b(func|package|import|return|if|else|for|range|switch|case|default|defer|go|chan|select|map|struct|interface|var|const|type|break|continue|fallthrough|go|goroutine)\b/g, cls: 'tok-kw' },
  { re: /\b(public|private|protected|abstract|final|sealed|override|virtual|async|await|using|namespace|class|struct|enum|interface|void|bool|int|long|string|double|float|decimal|var|new|return|if|else|for|while|do|switch|case|break|continue|try|catch|finally|throw)\b/g, cls: 'tok-kw' },
  { re: /\b(SELECT|FROM|WHERE|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|TABLE|INDEX|VIEW|JOIN|LEFT|RIGHT|INNER|OUTER|ON|AND|OR|NOT|IN|AS|SET|VALUES|INTO|FROM|GROUP|BY|ORDER|ASC|DESC|HAVING|LIMIT|OFFSET|UNION|ALL|DISTINCT|EXISTS|BETWEEN|LIKE|IS|NULL|TRUE|FALSE|PRIMARY|KEY|FOREIGN|REFERENCES|CONSTRAINT|DEFAULT|CHECK|UNIQUE|CASCADE|RESTRICT)\b/gi, cls: 'tok-kw' },
  { re: /\b(function|=>)\s*(?=\w)/g, cls: 'tok-fn' },
  { re: /\b([A-Z]\w*)\b/g, cls: 'tok-type' },
  { re: /([=<>!+\-*/%&|^~?:]+)/g, cls: 'tok-op' },
];

/**
 * Tokenise raw code text into HTML with syntax classes.
 * Returns the code string wrapped in <span> elements.
 *
 * Uses a priority-based overlay: each token rule is applied in
 * sequence, and spans already applied by earlier rules are kept.
 * This is intentionally lightweight — no full AST, no grammar files.
 */
function tokeniseCode(raw) {
  // Collect all token ranges
  const ranges = [];

  for (const { re, cls } of TOKEN_RULES) {
    const rx = new RegExp(re.source, re.flags);
    let match;
    while ((match = rx.exec(raw)) !== null) {
      const start = match.index;
      const end = start + match[0].length;
      // Skip if overlaps an existing (higher-priority) range
      if (ranges.some(r => start < r.end && end > r.start)) continue;
      ranges.push({ start, end, cls, text: match[0] });
    }
  }

  ranges.sort((a, b) => a.start - b.start);

  // Build output
  const parts = [];
  let pos = 0;
  for (const r of ranges) {
    if (r.start > pos) {
      parts.push(escapeHtml(raw.slice(pos, r.start)));
    }
    parts.push(`<span class="${r.cls}">${escapeHtml(r.text)}</span>`);
    pos = r.end;
  }
  if (pos < raw.length) {
    parts.push(escapeHtml(raw.slice(pos)));
  }
  return parts.join('');
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/* ------------------------------------------------------------------ */
/*  Annotation marker parsing                                         */
/* ------------------------------------------------------------------ */

const MARKER_RE = /\/\*\s*\[!(\w+)(?::([^\]]*))?\]\s*\*\/|\/\/\s*\[!(\w+)(?::([^\]]*))?\]/;

function parseMarkers(line) {
  const m = line.match(MARKER_RE);
  if (!m) return null;
  const type = m[1] || m[3];
  const payload = m[2] || m[4] || '';
  return { type, payload };
}

function stripMarker(line) {
  return line.replace(MARKER_RE, '').trimEnd();
}

/* ------------------------------------------------------------------ */
/*  Block builder                                                     */
/* ------------------------------------------------------------------ */

/**
 * Process a single <pre><code> block and return the enhanced wrapper.
 */
function processCodeBlock(pre) {
  const codeEl = pre.querySelector('code');
  if (!codeEl) return;

  const rawText = codeEl.textContent;
  const lines = rawText.split('\n');
  // Remove trailing empty line if present (common in fenced blocks)
  if (lines.length && lines[lines.length - 1].trim() === '') lines.pop();

  const lang = detectLanguage(codeEl) || '';
  const calloutCount = { value: 0 };

  // --- Build line number cells and code line elements ---
  const lineNumbers = [];
  const codeLines = [];

  for (const line of lines) {
    const marker = parseMarkers(line);
    const clean = stripMarker(line);

    // Line number
    const numSpan = document.createElement('span');
    numSpan.textContent = lineNumbers.length + 1;
    lineNumbers.push(numSpan);

    // Code line
    const lineEl = document.createElement('span');
    lineEl.className = 'code-block__line';

    // Apply marker effects
    if (marker) {
      switch (marker.type) {
        case 'highlight':
          lineEl.classList.add('code-block__highlight-line');
          break;
        case 'annotation':
          lineEl.classList.add('code-block__annotation-line');
          const tip = document.createElement('span');
          tip.className = 'code-block__annotation';
          tip.textContent = marker.payload || 'Note';
          lineEl.appendChild(tip);
          break;
        case 'callout':
          calloutCount.value++;
          lineEl.classList.add('code-block__callout-line');
          const badge = document.createElement('span');
          badge.className = 'code-block__callout-badge';
          badge.textContent = calloutCount.value;
          lineEl.appendChild(badge);
          break;
      }
    }

    // Tokenised code content
    const codeSpan = document.createElement('span');
    codeSpan.innerHTML = tokeniseCode(clean) || ' ';
    lineEl.appendChild(codeSpan);

    codeLines.push(lineEl);
  }

  // --- Assemble wrapper ---
  const wrapper = document.createElement('div');
  wrapper.className = 'code-block';

  // Header
  const header = document.createElement('div');
  header.className = 'code-block__header';

  if (lang) {
    const langBadge = document.createElement('span');
    langBadge.className = 'code-block__lang';
    langBadge.textContent = lang;
    header.appendChild(langBadge);
  }

  const copyBtn = document.createElement('button');
  copyBtn.className = 'code-block__copy-btn';
  copyBtn.type = 'button';
  copyBtn.textContent = 'Copy';
  copyBtn.addEventListener('click', () => handleCopy(copyBtn, rawText));
  header.appendChild(copyBtn);

  wrapper.appendChild(header);

  // Scroll container
  const scroll = document.createElement('div');
  scroll.className = 'code-block__scroll';

  const table = document.createElement('div');
  table.className = 'code-block__table';

  // Line numbers gutter
  const gutter = document.createElement('div');
  gutter.className = 'code-block__line-numbers';
  gutter.setAttribute('aria-hidden', 'true');
  for (const num of lineNumbers) gutter.appendChild(num);

  // Code column
  const codeCol = document.createElement('div');
  codeCol.className = 'code-block__code';
  const codeBlock = document.createElement('code');
  for (const line of codeLines) codeBlock.appendChild(line);
  codeCol.appendChild(codeBlock);

  table.appendChild(gutter);
  table.appendChild(codeCol);
  scroll.appendChild(table);
  wrapper.appendChild(scroll);

  // Replace original
  pre.replaceWith(wrapper);
}

/* ------------------------------------------------------------------ */
/*  Copy handler                                                      */
/* ------------------------------------------------------------------ */

async function handleCopy(btn, text) {
  try {
    await navigator.clipboard.writeText(text);
    btn.textContent = 'Copied!';
    btn.classList.add('code-block__copy-btn--copied');
    setTimeout(() => {
      btn.textContent = 'Copy';
      btn.classList.remove('code-block__copy-btn--copied');
    }, 2000);
  } catch {
    // Fallback for older browsers
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;left:-9999px';
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand('copy');
      btn.textContent = 'Copied!';
      btn.classList.add('code-block__copy-btn--copied');
      setTimeout(() => {
        btn.textContent = 'Copy';
        btn.classList.remove('code-block__copy-btn--copied');
      }, 2000);
    } catch { /* silent */ }
    document.body.removeChild(ta);
  }
}

/* ------------------------------------------------------------------ */
/*  Public API                                                        */
/* ------------------------------------------------------------------ */

/**
 * Initialise the code annotation system.
 * Finds all `<pre><code>` blocks and enhances them.
 *
 * @param {Element} [root=document] — optional root to scope search
 */
export function initCodeAnnotation(root = document) {
  const blocks = root.querySelectorAll('pre > code');
  // Process in reverse so DOM replacement doesn't shift indices
  const pres = Array.from(blocks).map(c => c.parentElement).reverse();
  for (const pre of pres) {
    processCodeBlock(pre);
  }
}

export default initCodeAnnotation;
