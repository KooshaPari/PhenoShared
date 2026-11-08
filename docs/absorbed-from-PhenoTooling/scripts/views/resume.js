import { el } from '../components/dom.js';
import { initScrollReveal } from '../scroll-reveal.js';
import {
  EDUCATION,
  ROLES,
  PERSONAS,
} from '../../data/phenotype.js';

/* ================================================================
   Resume data — sourced from phenotype profile.
   ================================================================ */

/** Format a YYYY-MM date string to a display year (or 'Present'). */
function formatYear(dateStr) {
  if (!dateStr || dateStr === 'present') return 'Present';
  return dateStr.split('-')[0];
}

/** Map ROLES (phenotype) into the timeline format resume expects. */
const EXPERIENCE = ROLES.map((r) => ({
  company: r.company,
  role: r.title,
  dates: `${formatYear(r.start)} \u2013 ${formatYear(r.end)}`,
  badge: r.framing[0] ?? 'Engineering',
  desc: r.highlights,
}));

/** Derive education entries from phenotype data. */
const RESUME_EDUCATION = [
  {
    school: EDUCATION.institution,
    degree: EDUCATION.degrees.map((d) => d.kind).join(' \u00b7 '),
    detail:
      `${EDUCATION.honorsCollege}. GPA: ${EDUCATION.degrees[0].gpa}.`,
  },
];

/** Derive skills from engineering persona competencies. */
const SKILLS = PERSONAS.engineering.competencies.map((c) => ({
  name: c.axis,
  level: c.score,
}));

const BADGE_CLASS = {
  Engineering: 'resume-badge--eng',
  Product:     'resume-badge--product',
  Leadership:  'resume-badge--leadership',
};

/* ================================================================
   Helper — build the resume <style> tag (injected once).
   ================================================================ */

const STYLE_ID = 'resume-timeline-css';

function ensureStyles() {
  if (document.getElementById(STYLE_ID)) return;

  const link = document.createElement('link');
  link.id = STYLE_ID;
  link.rel = 'stylesheet';
  link.href = '/styles/resume-timeline.css';
  document.head.appendChild(link);
}

/* ================================================================
   Component builders (return DOM elements).
   ================================================================ */

function buildNode(entry, index) {
  const side = index % 2 === 0 ? 'left' : 'right';
  const delay = index * 100;

  return el('div', {
    class: `resume-node resume-node--${side}`,
    'data-reveal': side,
    'data-reveal-delay': String(delay),
  },
    el('span', { class: 'resume-badge ' + (BADGE_CLASS[entry.badge] ?? '') }, entry.badge),
    el('div', { class: 'resume-node__date' }, entry.dates),
    el('div', { class: 'resume-node__company' }, entry.company),
    el('div', { class: 'resume-node__role' }, entry.role),
    el('ul', { class: 'resume-node__desc' },
      ...entry.desc.map(d => el('li', {}, d)),
    ),
  );
}

function buildTimeline(data) {
  return el('div', { class: 'resume-timeline', 'data-reveal': 'up' },
    ...data.map((entry, i) => buildNode(entry, i)),
  );
}

function buildSection(eyebrow, heading, children) {
  return el('section', { class: 'resume-section', 'data-reveal': 'up', 'data-reveal-delay': '0' },
    el('p', { class: 'eyebrow eyebrow--precision' }, eyebrow),
    el('h2', {}, heading),
    ...children,
  );
}

function buildSkills(data) {
  return el('div', { class: 'resume-skills' },
    ...data.map((skill, i) => el('div', {
      class: 'resume-skill',
      'data-reveal': 'scale',
      'data-reveal-delay': String(i * 80),
    },
      el('div', { class: 'resume-skill__name' }, skill.name),
      el('div', { class: 'resume-skill__bar-track' },
        el('div', {
          class: 'resume-skill__bar-fill',
          style: `width: ${skill.level}%`,
        }),
      ),
    )),
  );
}

function buildEducation(data) {
  return el('div', { class: 'resume-edu-list' },
    ...data.map((edu, i) => el('div', {
      class: 'resume-edu-card',
      'data-reveal': 'up',
      'data-reveal-delay': String(i * 100),
    },
      el('div', { class: 'resume-edu-card__school' }, edu.school),
      el('div', { class: 'resume-edu-card__degree' }, edu.degree),
      el('div', { class: 'resume-edu-card__detail' }, edu.detail),
    )),
  );
}

/* ================================================================
   Public API — called by app.js via import.
   ================================================================ */

export function renderResume(root) {
  ensureStyles();

  root.replaceChildren(
    el('section', { class: 'view active portfolio-view' },
      el('p', { class: 'eyebrow eyebrow--precision', 'data-reveal': 'fade' }, 'RESUME'),
      el('h1', { 'data-reveal': 'up', 'data-reveal-delay': '50' }, 'Experience'),
      el('p', {
        class: 'lede',
        'data-reveal': 'up',
        'data-reveal-delay': '100',
      }, `${ROLES.length} roles, one thread: building systems that let teams move faster and ship with confidence.`),
      el('p', {
        class: 'resume-download',
        'data-reveal': 'up',
        'data-reveal-delay': '150',
      },
        el('a', {
          href: '/koosha-paridehpour-resume.pdf',
          download: 'Koosha_Paridehpour_Resume.pdf',
          class: 'resume-download__link',
        }, 'Download PDF resume'),
      ),

      /* --- Experience Timeline --- */
      buildSection('Experience', 'Timeline', [
        buildTimeline(EXPERIENCE),
      ]),

      /* --- Education --- */
      buildSection('Education', 'Education', [
        buildEducation(RESUME_EDUCATION),
      ]),

      /* --- Skills --- */
      buildSection('Skills', 'Skills', [
        buildSkills(SKILLS),
      ]),
    ),
  );

  // Kick the scroll-reveal observer after DOM is painted (browser only).
  if (typeof requestAnimationFrame !== 'undefined') {
    requestAnimationFrame(() => initScrollReveal());
  }
}
