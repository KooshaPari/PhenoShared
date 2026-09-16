export type Link = {
  label: string;
  href: string;
  external?: boolean;
};

export type Project = {
  slug: string;
  title: string;
  summary: string;
  blurb: string;
  timeframe: string;
  kind: string;
  highlight: string;
  tags: string[];
  links: Link[];
};

export type Forward = {
  source: string;
  target: string;
  note: string;
};

export const site = {
  name: "Koosha Paridehpour",
  handle: "<REDACTED>",
  url: "https://<REDACTED>.com",
  location: "Santa Monica, California",
  headline: "Builder of Phenotype systems, developer tools, and product surfaces.",
  description:
    "Personal landing page for Koosha Paridehpour, with featured projects, contact routes, and legacy portfolio forwards.",
};

export const socials: Link[] = [
  { label: "GitHub", href: "https://github.com/<REDACTED>", external: true },
  { label: "LinkedIn", href: "https://www.linkedin.com/in/<REDACTED>", external: true },
  { label: "Devpost", href: "https://devpost.com/<REDACTED>", external: true },
  { label: "Email", href: "mailto:koosha@<REDACTED>.com", external: true },
];

export const profileFacts = [
  { label: "Current base", value: "Santa Monica, CA" },
  { label: "Study", value: "Arizona State University" },
  { label: "Track", value: "Computer Science, Spring 2026" },
  { label: "Skills", value: "Bash, Linux, systems, web" },
] as const;

export const projectPillars = [
  {
    title: "Portfolio and launch surfaces",
    copy: "I build the site layers that turn projects into something people can actually understand and access.",
  },
  {
    title: "Agent and infra systems",
    copy: "I like runtimes, orchestration, observability, and the control planes that keep them usable.",
  },
  {
    title: "Migration and consolidation",
    copy: "I clean up old surfaces, preserve useful content, and move legacy work into a durable shape.",
  },
] as const;

export const projects: Project[] = [
  {
    slug: "byteport",
    title: "BytePort",
    summary: "MicroVM deployment and portfolio integration.",
    blurb:
      "BytePort deploys projects from Git repositories, provisions isolated runtime environments, and registers project pages and access URLs into the portfolio layer.",
    timeframe: "2024 - present",
    kind: "Platform",
    highlight: "Portfolio-aware deployment for shipped projects.",
    tags: ["MicroVM", "portfolio", "infrastructure", "LLM-assisted metadata"],
    links: [
      { label: "Repo", href: "https://github.com/<REDACTED>/BytePort", external: true },
      { label: "Landing", href: "https://byteport.<REDACTED>.com", external: true },
    ],
  },
  {
    slug: "thegent",
    title: "theGent",
    summary: "Python agent runtime and orchestration system.",
    blurb:
      "theGent is the agent runtime I use for autonomous workflows, tool routing, and orchestration across the Phenotype ecosystem.",
    timeframe: "2025 - present",
    kind: "Runtime",
    highlight: "Agent-native runtime and workflow control.",
    tags: ["agents", "runtime", "tooling", "governance"],
    links: [
      { label: "Repo", href: "https://github.com/<REDACTED>/thegent", external: true },
      { label: "Landing", href: "https://thegent.<REDACTED>.com", external: true },
    ],
  },
  {
    slug: "crun",
    title: "CRun",
    summary: "Parallelized command runner for large agent workloads.",
    blurb:
      "CRun takes on large-scale code hygiene and analysis work by distributing commands and file-level tasks across agents, then coordinating the results.",
    timeframe: "2025",
    kind: "Tooling",
    highlight: "Scale-out execution for code maintenance.",
    tags: ["parallelism", "CLI", "analysis", "automation"],
    links: [
      { label: "Devpost", href: "https://devpost.com/<REDACTED>", external: true },
    ],
  },
  {
    slug: "healthsync",
    title: "HealthSync",
    summary: "Health journal that turns notes into narratives.",
    blurb:
      "HealthSync maps physical and mental health entries into weekly summaries, long-term overviews, and clearer explanations for practitioners.",
    timeframe: "Hackathon",
    kind: "Product",
    highlight: "A personal health layer with narrative summaries.",
    tags: ["Flutter", "Firebase", "GCP", "health"],
    links: [
      { label: "Devpost", href: "https://devpost.com/<REDACTED>", external: true },
    ],
  },
  {
    slug: "spyn",
    title: "Project Spyn",
    summary: "Lego EV3 maze navigation with control logic.",
    blurb:
      "Project Spyn turned a Lego EV3 unit into a pseudo-autonomous vehicle that could navigate a maze, detect color zones, and follow a PID-controlled path.",
    timeframe: "2023",
    kind: "Robotics",
    highlight: "Physical systems, control, and navigation.",
    tags: ["MATLAB", "EV3", "PID", "robotics"],
    links: [
      { label: "Devpost", href: "https://devpost.com/<REDACTED>", external: true },
    ],
  },
  {
    slug: "frostify",
    title: "Frostify",
    summary: "Spotify theme with a frosted-glass visual system.",
    blurb:
      "Frostify was an early theme project for the Spotify desktop client, focused on a translucent visual treatment and small UI refinements.",
    timeframe: "2020",
    kind: "Theme",
    highlight: "A visual customization project that aged into archive.",
    tags: ["theming", "visual design", "desktop", "Spotify"],
    links: [
      { label: "Devpost", href: "https://devpost.com/<REDACTED>", external: true },
    ],
  },
];

export const forwards: Forward[] = [
  { source: "/portfolio", target: "/", note: "Old portfolio home" },
  { source: "/work", target: "/projects", note: "Legacy work index" },
  { source: "/projects", target: "/projects", note: "Canonical project hub" },
  { source: "/about", target: "/about", note: "Personal bio" },
  { source: "/contact", target: "/contact", note: "Contact page" },
  { source: "/resume", target: "/resume", note: "Resume view" },
  { source: "/cv", target: "/resume", note: "Resume alias" },
  { source: "/byteport", target: "/projects/byteport", note: "Project forward" },
  { source: "/thegent", target: "/projects/thegent", note: "Project forward" },
  { source: "/crun", target: "/projects/crun", note: "Project forward" },
  { source: "/healthsync", target: "/projects/healthsync", note: "Project forward" },
  { source: "/spyn", target: "/projects/spyn", note: "Project forward" },
  { source: "/frostify", target: "/projects/frostify", note: "Project forward" },
];

export const resumeItems = [
  {
    title: "Computer Science graduate study",
    meta: "Arizona State University, Spring 2026",
    copy: "Graduate coursework across data visualization, mobile computing, applied cryptography, AI, and software verification.",
  },
  {
    title: "Phenotype",
    meta: "Current engineering work",
    copy: "Systems, tooling, docs, observability, and the control surfaces that hold the wider ecosystem together.",
  },
  {
    title: "Public portfolio",
    meta: "Devpost, GitHub, LinkedIn",
    copy: "Public-facing work, project notes, and the long tail of experiments that turned into durable products.",
  },
] as const;
