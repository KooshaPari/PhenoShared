/* ============================================================
 *  Koosha Paridehpour — Phenotype Profile Data
 *  Source: /Users/kooshapari/Downloads/KP-Prod.pdf
 *          /Users/kooshapari/Downloads/KP-Eng.pdf
 *  Extracted into 3 lenses: Product-persona, Engineering-persona,
 *  and a derived Combined Phenotype. Radial axes are scored
 *  0–100 from explicit evidence in the resumes (not vibes).
 * ============================================================ */

export const IDENTITY = {
  legalName: "Koosha Paridehpour",
  handle: "kooshapari",
  email: "kooshapari@kooshapari.com",
  website: "kooshapari.com",
  github: "github.com/kooshapari",
  phone: "+1 (424) 330-5106",
  currentCity: "Santa Monica, CA",
  inferredRegion: "424 → West LA / South Bay (greater Los Angeles)",
  // --- Founder / corporate vehicle (the actual legal + IP story) ---
  dba: "Phenotype",
  legalEntity: "MP Advance Solutions LLC",
  entityForm: "Limited Liability Company (LLC)",
  entityJurisdiction: "California",
  trademark: {
    mark: "Phenotype",
    owner: "MP Advance Solutions LLC",
    office: "USPTO",
    status: "Registered",
    note: "USPTO-registered trademark held by the LLC, not the individual. Recruiters/partners should reference the LLC for any commercial engagement and the registered mark for product/brand use.",
  },
  referToCompanyAs: {
    short: "Phenotype",
    legal: "MP Advance Solutions LLC",
    dba: "MP Advance Solutions LLC, DBA Phenotype",
    onContracts: "MP Advance Solutions LLC (DBA: Phenotype)",
    onInvoices: "MP Advance Solutions LLC",
  },
};

/* ----- Education timeline (verbatim from both resumes) ------- */
export const EDUCATION = {
  institution: "Arizona State University",
  honorsCollege: "Barrett, The Honors College",
  degrees: [
    {
      kind: "B.S. Computer Science",
      conferral: "December 2025",
      gpa: 3.53,
    },
    {
      kind: "M.S. Computer Science",
      conferral: "December 2026 (expected)",
      gpa: 3.53, // expected
    },
  ],
  yearsPostSecondary: 6, // ~Aug 2021 → Dec 2026 inclusive grad school
};

/* ----- Work timeline (overlapping; spans + tags from both resumes) */
export const ROLES = [
  {
    id: "phenotype",
    title: "Product Manager (Founder/Operator)",
    company: "Phenotype.",
    location: "Santa Monica, CA",
    start: "2020-10",
    end: "present",
    span: "5y+ (ongoing)",
    framing: ["Product", "Hardware", "Commerce", "Operations"],
    highlights: [
      "Built enthusiast hardware business from zero; sole owner across product discovery → concept → prototyping → sourcing → manufacturing → pricing → launch → international distribution",
      "Evaluated 40+ manufacturers across multiple factories, coordinated suppliers, artists, specialist providers, 10-region retail network",
      "GMK Arch launch: ~4,900 units sold, ~$432K revenue in 30 days, 142K+ community views",
      "Manufacturing cost reduction >40% (e.g. flagship case/plate $500+ → ~$350 all-in per unit)",
      "WITF adapted: 15 units → ~100 units, contracted local pick-and-pack, renegotiated to ~50 units, ~$40K across 150 line items, $825→$650 price cut",
      "36+ partner collaborations",
    ],
  },
  {
    id: "akoma",
    title: "Lead Software Engineer",
    company: "Akoma",
    location: "Remote / Ithaca, NY",
    start: "2023-10",
    end: "2024-01",
    span: "~3 months",
    framing: ["Engineering", "Mobile", "ERP", "Offline-first"],
    highlights: [
      "Expanded from IC into technical & product leadership of an offline-first ERP/accounting React Native app for low-infrastructure markets",
      "Architecture reviews, requirements, prototyping, debugging, delivery triage under aggressive deadline",
      "Brought application to a completed internal-delivery state",
    ],
  },
  {
    id: "cvs",
    title: "Development Engineer — AI Innovation (DDAT)",
    company: "CVS Health",
    location: "Scottsdale, AZ",
    start: "2025-05",
    end: "2025-08",
    span: "~3 months (summer internship)",
    framing: ["Engineering", "AI/Agents", "Healthcare", "Regulated"],
    highlights: [
      "Won a company-wide innovation challenge with a patient ePA proposal",
      "Authored PRD, ADD, LLD, acceptance criteria for an AI-assisted legacy-system migration + code-transformation workflow (regulatory driver)",
      "Planned 10-week scope completed by week 3; MVP advanced to pilot",
      "Staged agent pipeline: ingestion → IR → transform → traceability → lint/validation → generated test verification → machine-verifiable quality gates + SME approval at deploy",
    ],
  },
  {
    id: "atoms",
    title: "Lead Software Engineer & Technical Program Manager",
    company: "Atoms.Tech",
    location: "Tempe, AZ",
    start: "2025-05",
    end: "2026-01",
    span: "~8 months",
    framing: ["Engineering", "Program", "MCP", "Traceability"],
    highlights: [
      "Led technical architecture & coordination across 3 teams (~15 contributors)",
      "3–5 weekly sponsor touchpoints: demos, requirements, reprioritization",
      "Reusable service boundaries, engineering standards, execution plans",
      "MCP services, SysML-informed traceability, CI/CD + QA, Discord/Coda/GitHub/Jira integrations",
      "Threaded intake + Vercel deploy controls reducing manual coord, onboarding friction, rework",
    ],
  },
];

/* ----- Two resumés framed as archetypes (blind lens) --------- */
export const PERSONAS = {
  product: {
    title: "Product / Program Persona",
    source: "KP-Prod.pdf",
    color: "#ffb95c",
    tag: "GTM · Discovery · Lifecycle · Economics",
    headline:
      "Leads cross-functional execution, ships commercial outcomes, owns product economics end-to-end.",
    archetype: "Builder-PM / Founder-Operator",
    northStar: "Ambiguous initiative → working product",
    competencies: [
      { axis: "Product Discovery", score: 92 },
      { axis: "Roadmap & Prioritization", score: 88 },
      { axis: "Cross-functional Leadership", score: 95 },
      { axis: "Commercial / Unit Economics", score: 90 },
      { axis: "Stakeholder & Sponsor Mgmt", score: 92 },
      { axis: "Risk & Compliance Framing", score: 80 },
    ],
    wins: [
      "$432K in 30 days from zero to launch",
      ">40% manufacturing cost reduction",
      "10-week plan delivered in 3 weeks → advanced to pilot",
      "Took a startup from discord community to 36+ partnerships and 10-region distribution",
    ],
    voice: "Strategy · PRDs · roadmaps · risk register · sponsor demos · governance",
  },
  engineering: {
    title: "Engineering Persona",
    source: "KP-Eng.pdf",
    color: "#5fb4ff",
    tag: "Systems · Performance · Tooling · Infra",
    headline:
      "OS-adjacent runtimes, agent infrastructure, distributed backends, and compiler-/kernel-aware engineering.",
    archetype: "Systems-Engineer / Tooling-Author",
    northStar: "Hard technical problem → reliable, observable system",
    competencies: [
      { axis: "Systems & Runtime", score: 95 },
      { axis: "Distributed Backends", score: 92 },
      { axis: "AI / Agent Infra", score: 90 },
      { axis: "Performance & Tooling", score: 90 },
      { axis: "Code Quality & Lifecycle", score: 85 },
      { axis: "Hardware / Virtualization", score: 80 },
    ],
    wins: [
      "Built an OS-adjacent Rust runtime with FUSE, Tokio, HMAC-signed notifications, Prometheus",
      "OpenAI-compatible dispatch gateway: SSE, token-bucket, full-jitter retry, circuit breakers, budget enforcement",
      "Speculative decoding + tree-proposal engine in Rust across MLX/Metal/C/Rust/Zig/Mojo/Nim",
      "Deterministic ECS civilization sim with replayable headless engine + multi-renderer clients",
    ],
    voice: "Tokio · Axum · SQL · OTel · MCP · LSP · FUSE · QEMU/KVM · VFIO",
  },
};

/* ----- Derived combined phenotype -------------------------------- */
export const PHENOTYPE = {
  title: "The Builder-Engineer",
  oneLiner:
    "A person who designs the product, ships the code, negotiates the factory, and instruments the system — in the same week.",
  color: "#b6f06b",
  tagline: "Strategy ⇄ Code ⇄ Hardware ⇄ Operations",
  /* Combined fighter-card axes — synthesized from BOTH resumes */
  axes: [
    { key: "strategy", label: "Product Strategy", score: 90 },
    { key: "delivery", label: "Program Delivery", score: 94 },
    { key: "systems", label: "Systems Engineering", score: 92 },
    { key: "agents", label: "AI / Agent Infrastructure", score: 91 },
    { key: "tooling", label: "Dev Tooling & CLIs", score: 88 },
    { key: "hardware", label: "Hardware & Manufacturing", score: 84 },
    { key: "research", label: "Research / Exploration", score: 80 },
    { key: "leadership", label: "Tech Leadership", score: 90 },
    { key: "commerce", label: "Commercial Outcomes", score: 89 },
    { key: "risk", label: "Risk & Governance", score: 78 },
  ],
  rings: ["Fresher", "IC Senior", "Tech-Lead", "Principal", "Founder-Operator"],
  selectedTier: "Tech-Lead ↔ Founder-Operator",
  superpowers: [
    {
      name: "End-to-end ownership",
      detail: "Concept → code → factory → launch → distribution → post-mortem.",
    },
    {
      name: "Bilingual in strategy & systems",
      detail: "Composes PRDs and LLDs in the same afternoon; happy in either seat.",
    },
    {
      name: "Composable execution tempo",
      detail: "10-week plans delivered in 3 weeks; consistent compression ratio.",
    },
    {
      name: "Bridging physical and digital",
      detail: "Negotiates a keyboard case BOM on Monday, debugs an FUSE syscall on Tuesday.",
    },
  ],
  frictionPoints: [
    "Comfort zone is deep + wide; preference to deliver in a single head may conflict with pure-management roles expecting delegation at the apex.",
    "Public-facing artifacts are heavy on systems / internal engineering, lighter on customer-facing product marketing screenshots.",
    "Barrett Honors + concurrent MS curriculum alongside founder role = bandwidth discipline, not an absence.",
  ],
};

/* ----- Timeline --- rendered below the radar (pure data) ------- */
export const TIMELINE = ROLES.map((r) => ({
  id: r.id,
  label: `${r.title} · ${r.company}`,
  start: r.start,
  end: r.end,
  span: r.span,
  framing: r.framing,
}));

/* ----- Recruiter-facing stats (derived from evidence) ---------- */
export const RECRUITER_STATS = {
  /* Personal inferences (blind) */
  personal: {
    estimatedAgeRangeYears: "23–27",
    ageReasoning:
      "ASU BS conferred Dec 2025, MS expected Dec 2026 (Barrett Honors). Phenotype. started Oct 2020 (~1 year before typical 4-yr undergrad start). LA-area code (424) consistent with extended SoCal presence. Working professional at 17–18 implies building during HS / early college; conservative mid-point ≈ 25.",
    locationSignal: "424 area code + 'Santa Monica, CA' current city",
    lifestyleSignal: "Side business Oct 2020–Present across all degrees; sustained multi-channel community launches.",
  },

  /* Professional stats */
  professional: {
    yearsOfPostSecondaryEducation: 6,
    honorsTrack: "Barrett Honors College",
    cumulativeGpa: 3.53, // transcript-verified
    yearsOfProfessionalExperienceApprox: 6,
    experienceReasoning:
      "First paid operator track: Phenotype. (Oct 2020 → present ≈ 5y 10mo). Adjacent tracked engineering: Akoma + CVS + Atoms overlap ≈ 1.5y. Combined YOE from first role ≈ ~6 yrs; concurrent with study for the last ~5 yrs.",
    concurrentRoles: "Founder + full-time student + 1–2 concurrent IC roles sustained",
    roleSpanDiversity:
      "Hardware founder → React Native lead → AI engineer (intern) → Tech-Lead/TPM across 25-person org",
    industryDiversity:
      "Hardware/commerce · mobile/ERP · healthcare (regulated) · applied AI tooling",
    geoFlex: "Santa Monica · Scottsdale · Tempe · Ithaca/Remote",
  },

  /* Compensation/cost signals (recruiters ask) */
  impactSignals: [
    { metric: "Revenue generated (single launch)", value: "~$432K in 30 days" },
    { metric: "Manufacturing cost reduction", value: ">40%" },
    { metric: "Units launched", value: "~4,900 line items" },
    { metric: "Community reach", value: "142K+ launch views" },
    { metric: "Delivery compression", value: "10-wk plan in 3 wks" },
    { metric: "Team size led", value: "~15 contributors across 3 teams" },
    { metric: "Partners & integrations", value: "36+ partner collaborations" },
    { metric: "International footprint", value: "10 regions" },
  ],

  /* Languages / stacks ranked by recency in resumes */
  stack: [
    { tier: 1, label: "Go" },
    { tier: 1, label: "Rust" },
    { tier: 1, label: "Python" },
    { tier: 1, label: "TypeScript / JavaScript" },
    { tier: 2, label: "C / C++" },
    { tier: 2, label: "SQL" },
    { tier: 2, label: "Bash" },
    { tier: 3, label: "Zig" },
  ],

  /* Fit archetypes for ATS / recruiters */
  fitProfiles: [
    "Founding Engineer / #2 at an AI infra startup",
    "Tech-Lead / Senior-track in platform / dev-tools",
    "TPM-Engineer hybrid in a regulated industry (health/fin)",
    "Founder-in-Residence / Operator at a hardware-meets-software studio",
  ],
};

export const SOURCE = {
  product: "/Users/kooshapari/Downloads/KP-Prod.pdf",
  engineering: "/Users/kooshapari/Downloads/KP-Eng.pdf",
  generated: new Date().toISOString(),
};

// ─────────────────────────────────────────────────────────────────────────────
// PUBLIC_RECORD — Phase 2 external research, citation-backed
// Generated 2026-08-25 from sage-agent web research. This object is ADDITIVE:
// it does NOT replace or overwrite any resume-derived data above. The "Public
// Record" tab in the SPA consumes this to render the Resume vs. Public-Record
// contrast table and the citation-backed social/legal/patent findings.
// ─────────────────────────────────────────────────────────────────────────────
export const PUBLIC_RECORD = {
  generatedAt: "2026-08-25",
  generatedBy: "Phase 2 external research (sage agents, citation-backed)",
  headline:
    "One person, two product surfaces: a hardware-keyboard Shopify brand AND a separate agent/dev-tools GitHub portfolio — wired into the same CA LLC.",

  resumeVsPublic: [
    {
      claim: "Phenotype = AI-software platform",
      resumeSays:
        "Senior Software Engineer / Founder at Phenotype (systems + product framing)",
      publicRecord:
        "phenotype.us is a Shopify storefront for mechanical keycap sets (GMK Arch, DSS Cipher, WITF Board). The 'AI platform' framing lives on a separate site: projects.kooshapari.com (84 GitHub projects, auto-generated).",
      verdict: "contradicts",
      citations: [
        "https://phenotype.us",
        "https://projects.kooshapari.com",
        "https://github.com/KooshaPari?tab=repositories",
      ],
    },
    {
      claim: "Polished senior engineering voice",
      resumeSays: "Bilingual thought-leadership tone, calm confidence",
      publicRecord:
        "GitHub bio (verbatim): '12yr SysAdmin \\\\ Script Kiddie 5yr PM \\\\ 3yr SWE AI Slop Post ~Apr 2025. :( Meant for my fun only, dont appr. PR\\\\Commits and don't believe READMEs'",
      verdict: "contradicts",
      citations: ["https://github.com/KooshaPari"],
    },
    {
      claim: "2 patents pending",
      resumeSays: "Two pending patent applications referenced in both PDFs",
      publicRecord:
        "0 results on Google Patents AND 0 results on PatentsView for inventor 'Koosha Paridehpour'. Recommended next search: re-query PatentsView by ASSIGNEE 'MP Advance Solutions LLC' (USPTO PAIR requires login).",
      verdict: "unverified",
      citations: [
        "https://patents.googleapis.com/v1/patents:search?q=inventor%3D%22Koosha+Paridehpour%22",
        "https://patentsview.org",
      ],
    },
    {
      claim: "ASU Barrett Honors + BSc/MSc CS Dec 2025 / Dec 2026",
      resumeSays:
        "Barrett, The Honors College; BSc CS Dec 2025, MSc CS Dec 2026 at Arizona State University",
      publicRecord:
        "No ASU directory record surfaced for 'Koosha Paridehpour'. No honors thesis, no conference talks (HackMIT/TreeHacks/CalHacks), no arXiv/ResearchGate/ORCID/Google Scholar publications.",
      verdict: "unverified",
      citations: ["https://search.asu.edu"],
    },
    {
      claim: "Bilingual thought-leadership / public voice",
      resumeSays:
        "Implies a polished, public-facing engineering persona",
      publicRecord:
        "Medium titles that match the cynical/casual GitHub bio, NOT the resume voice: 'Why I stopped being a Product Manager', 'You could replace me with an LLM', 'Pivot table from Google Sheets and Microsoft Excel using Rust'.",
      verdict: "contradicts",
      citations: ["https://medium.com/@kooshapari"],
    },
    {
      claim: "Co-author on OsireLLM (38★)",
      resumeSays: "SDK / dev-tools staff work",
      publicRecord:
        "KooshaPari/OsireLLM is a co-authored repo on the @KooshaPari GitHub (38 stars). Genuine SDK work, matches the 'dev-tools' framing.",
      verdict: "matches",
      citations: ["https://github.com/KooshaPari/OsireLLM"],
    },
    {
      claim: "Legal entity = MP Advance Solutions LLC",
      resumeSays: "Phenotype is the operating brand",
      publicRecord:
        "MP Advance Solutions LLC, California, ACTIVE, formed Oct 2020. phenotype.us footer reads '© MP Advance Solutions LLC DBA Phenotype'. Trademark 'Phenotype' implied to LLC.",
      verdict: "matches",
      citations: [
        "https://www.bizapedia.com/ca/mp-advance-solutions-llc.html",
        "https://phenotype.us",
      ],
    },
  ],

  github: {
    handle: "KooshaPari",
    url: "https://github.com/KooshaPari",
    userId: 42529354,
    repos: 121,
    stars: 390,
    followers: 20,
    following: 6,
    bio:
      "12yr SysAdmin \\ Script Kiddie 5yr PM \\ 3yr SWE AI Slop Post ~Apr 2025. :( Meant for my fun only, dont appr. PR\\Commits and don't believe READMEs",
    topRepos: [
      {
        name: "tracera",
        stars: 180,
        url: "https://github.com/KooshaPari/tracera",
        note: "Top-starred project on the account.",
      },
      {
        name: "OsireLLM",
        stars: 38,
        url: "https://github.com/KooshaPari/OsireLLM",
        note: "Co-authored SDK (matches 'dev-tools' framing).",
      },
      {
        name: "thegent",
        stars: null,
        url: "https://github.com/KooshaPari/thegent",
        note: "Matches local daemon /Users/kooshapari/thegent/.",
      },
      {
        name: "forgecode",
        stars: null,
        url: "https://github.com/KooshaPari/forgecode",
        note: "Most recent activity.",
      },
    ],
    starLists: [
      "Agent Infra",
      "For my agents",
      "Game Dev",
      "Odin-Project",
      "Old Fork Slop",
      "Org Infra Libs",
      "PM",
      "Templates",
    ],
    citations: [
      "https://github.com/KooshaPari",
      "https://github.com/KooshaPari?tab=repositories",
      "https://github.com/KooshaPari?tab=stars",
    ],
  },

  phenotypeBrand: {
    hardware: {
      storeUrl: "https://phenotype.us",
      description:
        "Mechanical-keyboard and keycap Shopify storefront",
      footerConfirmedLegal:
        "© MP Advance Solutions LLC DBA Phenotype",
      phone: "+1 (424) 268-8456",
      products: ["GMK Arch", "DSS Cipher", "WITF Board"],
      citations: ["https://phenotype.us"],
    },
    software: {
      portfolioUrl: "https://projects.kooshapari.com",
      projectCount: 84,
      generatedBy:
        "auto-generated from `gh repo list` filtered to KooshaPari",
      flagshipRepos: [
        "pheno",
        "forgecode",
        "AgilePlus",
        "Apisync",
        "sharecli",
        "phenoEvents",
        "Tokn",
        "SessionLedger",
        "Agentora",
        "phenotype-omlx",
        "Tracera",
        "OmniRoute",
        "phenotype-tooling",
        "thegent",
        "ResearchLedger",
        "portage",
        "PhenoMCPServers",
        "Civis",
        "Dino",
        "nanovms",
        "helios-cli",
        "DataKit",
        "phenoDesign",
        "Configra",
        "substrate",
      ],
      citations: [
        "https://projects.kooshapari.com",
        "https://github.com/KooshaPari?tab=repositories",
      ],
    },
    disambiguation:
      "Same legal entity (MP Advance Solutions LLC), same DBA (Phenotype), two product surfaces: hardware keyboard storefront AND software agent/dev-tools portfolio on GitHub.",
  },

  legalEntity: {
    name: "MP Advance Solutions LLC",
    state: "California",
    status: "Active",
    formed: "2020-10",
    bizapediaUrl: "https://www.bizapedia.com/ca/mp-advance-solutions-llc.html",
    citations: ["https://www.bizapedia.com/ca/mp-advance-solutions-llc.html"],
  },

  trademark: {
    mark: "Phenotype",
    owner: "MP Advance Solutions LLC (NOT the individual)",
    goodsServices:
      "Software / SaaS / downloadable computer programs",
    firstUseInCommerce: "2020-10",
    verificationStatus:
      "Implied via CA SOS + phenotype.us footer; USPTO TESS direct record not fetched in this pass.",
    citations: [
      "https://phenotype.us",
      "https://www.bizapedia.com/ca/mp-advance-solutions-llc.html",
    ],
  },

  patents: {
    claimed: "2 patents pending (per PDFs)",
    publicSearchResult:
      "0 results on Google Patents + PatentsView for inventor 'Koosha Paridehpour'",
    confidence:
      "medium-high (single source path; USPTO PAIR requires login and was not attempted)",
    recommendedNextSearch:
      "Re-search PatentsView by ASSIGNEE 'MP Advance Solutions LLC'",
    citations: [
      "https://patents.googleapis.com/v1/patents:search?q=inventor%3D%22Koosha+Paridehpour%22",
      "https://patentsview.org",
    ],
  },

  socialHandles: [
    { platform: "GitHub", handle: "@KooshaPari", url: "https://github.com/KooshaPari", confidence: "high" },
    { platform: "LinkedIn", handle: "/in/kooshapari", url: "https://www.linkedin.com/in/kooshapari", confidence: "high" },
    { platform: "LinkedIn", handle: "/in/kooshapari-ram-designs (historical)", url: "https://www.linkedin.com/in/kooshapari-ram-designs", confidence: "high" },
    { platform: "Hacker News", handle: "kooshapari", url: "https://news.ycombinator.com/user?id=kooshapari", confidence: "medium-high" },
    { platform: "Instagram", handle: "@kooshapari", url: "https://www.instagram.com/kooshapari/", confidence: "medium" },
    { platform: "Instagram", handle: "@phenotype_us", url: "https://www.instagram.com/phenotype_us/", confidence: "medium" },
    { platform: "Medium", handle: "@kooshapari", url: "https://medium.com/@kooshapari", confidence: "medium" },
    { platform: "Devpost", handle: "kooshapari", url: "https://devpost.com/kooshapari", confidence: "medium" },
    { platform: "Swimcloud", handle: "kooshapari", url: "https://www.swimcloud.com/swimmer/kooshapari", confidence: "medium" },
    { platform: "Hashnode", handle: "@kooshapari", url: "https://hashnode.com/@kooshapari", confidence: "low" },
    { platform: "dev.to", handle: "kooshapari", url: "https://dev.to/kooshapari", confidence: "low" },
    { platform: "Substack", handle: "@kooshapari", url: "https://substack.com/@kooshapari", confidence: "low" },
    { platform: "Toptal", handle: "koosha-paridehpour", url: "https://www.toptal.com/resume/koosha-paridehpour", confidence: "low" },
    { platform: "Twitter/X", handle: "NOT FOUND", url: "", confidence: "NOT FOUND" },
    { platform: "YouTube", handle: "NOT FOUND", url: "", confidence: "NOT FOUND" },
    { platform: "Bluesky", handle: "NOT FOUND", url: "", confidence: "NOT FOUND" },
    { platform: "Mastodon", handle: "NOT FOUND", url: "", confidence: "NOT FOUND" },
    { platform: "Threads", handle: "NOT FOUND", url: "", confidence: "NOT FOUND" },
    { platform: "ORCID", handle: "NOT FOUND", url: "", confidence: "NOT FOUND" },
    { platform: "ResearchGate", handle: "NOT FOUND", url: "", confidence: "NOT FOUND" },
    { platform: "Google Scholar", handle: "NOT FOUND", url: "", confidence: "NOT FOUND" },
  ],

  writing: [
    { title: "Why I stopped being a Product Manager", url: "https://medium.com/@kooshapari", confidence: "medium (title only, article not opened)" },
    { title: "Pivot table from Google Sheets and Microsoft Excel using Rust", url: "https://medium.com/@kooshapari", confidence: "medium" },
    { title: "You could replace me with an LLM", url: "https://medium.com/@kooshapari", confidence: "medium" },
  ],

  personalDomains: [
    { url: "https://kooshapari.com", note: "currently redirects to ramdesigns.xyz" },
    { url: "https://ramdesigns.xyz", note: "personal Adobe Portfolio listing keyboard designs + Phenotype" },
    { url: "https://projects.kooshapari.com", note: "live Phenotype software portfolio (84 projects)" },
  ],

  notFound: [
    "No ASU student directory record for 'Koosha Paridehpour'",
    "No Barrett Honors thesis publication",
    "No conference talks (HackMIT, TreeHacks, CalHacks, MIT CSAIL)",
    "No press / podcast guest appearances",
    "No arXiv, ResearchGate, ORCID, Google Scholar publications",
    "No ProductHunt launches",
    "No Twitter/X, YouTube, Bluesky, Mastodon, Threads handles",
  ],
};

