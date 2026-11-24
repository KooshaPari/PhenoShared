/* ================================================================
   Cast Player — asciinema .cast file terminal replay engine.

   Parses the .cast format (JSON header + event lines), renders
   output into a terminal-like viewport with typewriter animation,
   and exposes play/pause/speed/restart controls.

   Usage:
     import { initCastPlayers } from './media/cast-player.js';
     initCastPlayers();           // auto-discovers .cast-player[data-src]

   Expected HTML:
     <div class="cast-player"
          data-src="/path/to/recording.cast"
          data-title="Terminal session">
     </div>
   ================================================================ */

import { el } from '../components/dom.js';

/* ---- .cast format parser ------------------------------------ */

/**
 * Parse a .cast file string into a structured playback object.
 *
 * Format:
 *   Line 1  — JSON header { version, term: { cols, rows }, title, command, ... }
 *   Line N  — JSON array [relative_seconds, event_type, data]
 *
 * @param {string} raw  Raw .cast file contents
 * @returns {{ header: object, events: Array<{ dt: number, type: string, data: string }> }}
 */
function parseCast(raw) {
  const lines = raw.split('\n').filter(l => l.trim());
  const header = JSON.parse(lines[0]);

  const events = [];
  for (let i = 1; i < lines.length; i++) {
    const arr = JSON.parse(lines[i]);
    events.push({ dt: arr[0], type: arr[1], data: arr[2] || '' });
  }

  return { header, events };
}

/* ---- Playback scheduler ------------------------------------- */

/**
 * Flatten cast events into a timeline of absolute timestamps with
 * accumulated output buffers, suitable for requestAnimationFrame
 * driven playback.
 *
 * @param {Array<{ dt: number, type: string, data: string }>} events
 * @returns {Array<{ time: number, type: string, data: string }>}
 */
function buildTimeline(events) {
  const timeline = [];
  let t = 0;
  for (const ev of events) {
    t += ev.dt;
    timeline.push({ time: t, type: ev.type, data: ev.data });
  }
  return timeline;
}

/* ---- DOM construction --------------------------------------- */

function buildDOM(title, command) {
  const root = el('div', { class: 'cast-player' });

  // Title bar with traffic-light dots
  const header = el('div', { class: 'cast-player__header' },
    el('div', { class: 'cast-player__dots' },
      el('span', { class: 'cast-player__dot cast-player__dot--close' }),
      el('span', { class: 'cast-player__dot cast-player__dot--min' }),
      el('span', { class: 'cast-player__dot cast-player__dot--max' }),
    ),
    el('span', { class: 'cast-player__title' }, title || 'Terminal'),
  );

  // Terminal viewport
  const terminal = el('div', { class: 'cast-player__terminal' });
  const output = el('span', { class: 'cast-player__output' });
  const cursor = el('span', { class: 'cast-player__cursor' });
  output.append(cursor);
  terminal.append(output);

  // Controls
  const playBtn = el('button', {
    class: 'cast-player__btn cast-player__btn--play',
    type: 'button',
    'aria-label': 'Play',
  }, '\u25b6');

  const restartBtn = el('button', {
    class: 'cast-player__btn',
    type: 'button',
    'aria-label': 'Restart',
  }, '\u21ba');

  const speeds = [0.5, 1, 2];
  const speedBtns = speeds.map(s => el('button', {
    class: `cast-player__speed-btn${s === 1 ? ' cast-player__speed-btn--active' : ''}`,
    type: 'button',
    'data-speed': String(s),
    'aria-label': `${s}x speed`,
  }, `${s}x`));

  const controls = el('div', { class: 'cast-player__controls' },
    playBtn,
    restartBtn,
    el('div', { class: 'cast-player__speed-group' }, ...speedBtns),
  );

  root.append(header, terminal, controls);

  if (command) {
    root.append(el('span', { class: 'cast-player__command' }, `$ ${command}`));
  }

  return { root, terminal, output, cursor, playBtn, restartBtn, speedBtns };
}

/* ---- Player controller -------------------------------------- */

function createPlayer(container) {
  const src = container.getAttribute('data-src');
  const title = container.getAttribute('data-title') || '';
  if (!src) return null;

  const { root, terminal, output, cursor, playBtn, restartBtn, speedBtns } =
    buildDOM(title);

  container.appendChild(root);

  let parsed = null;
  let timeline = [];
  let speed = 1;
  let playing = false;
  let finished = false;
  let startTime = 0;
  let elapsed = 0;        // accumulated time in ms (at current speed)
  let rafId = null;
  let eventIdx = 0;

  /* --- helpers --- */

  function applySpeed(s) {
    // Adjust elapsed to reflect the speed change without losing position
    speed = s;
    for (const btn of speedBtns) {
      btn.classList.toggle(
        'cast-player__speed-btn--active',
        parseFloat(btn.dataset.speed) === s,
      );
    }
  }

  function resetPlayback() {
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
    playing = false;
    finished = false;
    elapsed = 0;
    eventIdx = 0;
    output.textContent = '';
    output.append(cursor);
    root.classList.remove('cast-player--paused', 'cast-player--finished');
    playBtn.textContent = '\u25b6';
    playBtn.setAttribute('aria-label', 'Play');
    terminal.scrollTop = 0;
  }

  function flushEvents(upToMs) {
    const visibleTerminal = terminal;

    while (eventIdx < timeline.length && timeline[eventIdx].time * 1000 <= upToMs) {
      const ev = timeline[eventIdx];
      eventIdx++;

      if (ev.type === 'o' || ev.type === 'i') {
        // Strip \r and split on \n for clean rendering
        const text = ev.data.replace(/\r/g, '');
        const lines = text.split('\n');

        for (let li = 0; li < lines.length; li++) {
          if (li > 0) {
            // Insert a new line element
            const lineEl = document.createElement('div');
            lineEl.className = 'cast-player__line';
            // Move cursor after the new line
            lineEl.append(cursor);
            output.append(lineEl);
          }
          if (lines[li]) {
            // Insert text before the cursor
            const textNode = document.createTextNode(lines[li]);
            output.insertBefore(textNode, cursor);
          }
        }
      } else if (ev.type === 'w') {
        // Window resize event — could update terminal width; skip for now
      }

      // Auto-scroll
      visibleTerminal.scrollTop = visibleTerminal.scrollHeight;
    }
  }

  function tick(timestamp) {
    if (!playing) return;

    if (startTime === 0) startTime = timestamp;
    const delta = (timestamp - startTime) * speed;
    elapsed += delta;
    startTime = timestamp;

    flushEvents(elapsed);

    if (eventIdx >= timeline.length) {
      // Playback finished
      finished = true;
      playing = false;
      root.classList.add('cast-player--finished');
      playBtn.textContent = '\u25b6';
      playBtn.setAttribute('aria-label', 'Play');
      return;
    }

    rafId = requestAnimationFrame(tick);
  }

  function play() {
    if (finished) resetPlayback();
    playing = true;
    startTime = 0;
    root.classList.remove('cast-player--paused');
    root.classList.remove('cast-player--finished');
    playBtn.textContent = '\u23f8';
    playBtn.setAttribute('aria-label', 'Pause');
    rafId = requestAnimationFrame(tick);
  }

  function pause() {
    playing = false;
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
    root.classList.add('cast-player--paused');
    playBtn.textContent = '\u25b6';
    playBtn.setAttribute('aria-label', 'Play');
  }

  function togglePlay() {
    if (playing) pause(); else play();
  }

  /* --- event wiring --- */

  playBtn.addEventListener('click', togglePlay);

  restartBtn.addEventListener('click', () => {
    resetPlayback();
    // Start playing immediately after restart
    play();
  });

  for (const btn of speedBtns) {
    btn.addEventListener('click', () => {
      applySpeed(parseFloat(btn.dataset.speed));
    });
  }

  /* --- load & parse --- */

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  fetch(src, { signal: controller.signal })
    .then(r => {
      clearTimeout(timeout);
      if (!r.ok) throw new Error(`Failed to load cast file: ${r.status}`);
      return r.text();
    })
    .then(text => {
      parsed = parseCast(text);
      timeline = buildTimeline(parsed.events);

      // Use header terminal width if no explicit width set
      if (parsed.header?.term?.cols && !container.style.width) {
        const charWidth = 0.6; // approximate em-width of a monospace char
        const cols = parsed.header.term.cols;
        const estimated = cols * charWidth;
        // Don't override if it would be too small or too large
        if (estimated > 30 && estimated < 90) {
          terminal.style.width = `${estimated}em`;
          terminal.style.maxWidth = '100%';
        }
      }
    })
    .catch(err => {
      console.error('[cast-player]', err);
      output.textContent = `Error loading recording: ${err.message}`;
    });

  return { el: root, play, pause, resetPlayback };
}

/* ---- Public API --------------------------------------------- */

/**
 * Auto-discover all .cast-player[data-src] elements and initialize
 * a player for each. Call once after DOM is ready.
 *
 * @param {Document|Element} [scope=document]  Search scope
 * @returns {Array<object>}  Array of player instances
 */
export function initCastPlayers(scope = document) {
  const containers = scope.querySelectorAll('.cast-player[data-src]');
  const players = [];
  for (const container of containers) {
    players.push(createPlayer(container));
  }
  return players;
}
