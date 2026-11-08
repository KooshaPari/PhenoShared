/* Shared portfolio records. Metrics retain their evidence class. */
const FEATURED_PRESENTATIONS = {
  omniroute: {
    type: 'systems-sheet',
    alt: 'Structured routing sheet describing OmniRoute dispatch: provider selection, fallback cooldowns, and policy-aware routing under degradation.',
    annotations: {
      engineering: 'Fallback cooldowns, latency-optimized routing, and fallback-cache scoping by target URL hardened dispatch under provider degradation.',
      product: 'One hundred one merged pull requests across 21 upstream releases, with direct maintainer acknowledgement, during a focused 28-day contribution window.',
    },
    summary: 'Policy-aware routing sheet: provider health, cooldowns, and fallback chains make failure behavior explicit and inspectable.',
  },
  'gmk-arch': {
    type: 'physical-plate',
    alt: 'Transparent GMK Arch wordmark specimen with a pale ARCH letterform and teal Arch Linux and GMK marks.',
    annotations: {
      engineering: 'Kitting coverage, manufacturer constraints, and a 10-region distribution interface shaped one coordinated release system.',
      product: 'Community signal, launch economics, and supplier readiness converged in approximately 4,900 sold line items.',
    },
    media: { width: 354, height: 90 },
    assets: [{
      src: '/public/projects/gmk-arch/hero.png',
      alt: 'Transparent GMK Arch wordmark with a pale ARCH letterform and teal Arch Linux and GMK marks.',
      sha256: '73362047e4efa5f89a2d355f732425ab7afe3a206f3c4d421dade1cefc10a11a',
      width: 354,
      height: 90,
      retainedSource: {
        sha256: '73362047e4efa5f89a2d355f732425ab7afe3a206f3c4d421dade1cefc10a11a',
        width: 354,
        height: 90,
      },
      provenance: 'The deployed transparent PNG is byte-identical to the retained source; verified 2026-09-04. The retained source and custody record are private.',
      ownership: 'review-pending',
      licensing: 'review-pending',
    }],
  },
  witf: {
    type: 'physical-plate',
    alt: 'Black WITF Board keyboard shown from above on a warm concrete-colored surface, revealing its split Alice layout and left-side number pad.',
    annotations: {
      engineering: 'Constraint modeling linked supplier capacity, accessory scope, pricing, and outsourced fulfillment as volume moved from approximately 15 to 100 to 50 units.',
      product: 'Demand softened after the plan expanded; the viable core survived through a 100-to-50-unit reset, a price move, and an accessory refund.',
    },
    media: { width: 1600, height: 900 },
    assets: [
      {
        src: '/public/projects/witf/hero-01.webp',
        alt: 'Black WITF Board keyboard shown from above on a warm concrete-colored surface, revealing its split Alice layout and left-side number pad.',
        sha256: '48d335f2eb138833f715b4945073e47a3df1ab079fe6c505a42f893c3ae25370',
        width: 1600,
        height: 900,
        retainedSource: {
          sha256: 'a29ad788a00f32145e843facbf1bef24fcc03ff064a4934010b743799d33633a',
          width: 3840,
          height: 2160,
        },
        provenance: 'The deployed 1600x900 JPEG is an optimized derivative of the retained 3840x2160 PNG; source and derivative hashes are recorded separately; verified 2026-09-04. The retained source and custody record are private.',
        ownership: 'review-pending',
        licensing: 'review-pending',
      },
      {
        src: '/public/projects/witf/hero-02.webp',
        alt: 'Close view of the black WITF Board showing its left-side number pad, Alice key clusters, and dark green accent keys.',
        sha256: '57c0128902f6861a9fbb078742bf3f2f03070a0476180e2858ebcbd99033bac5',
        width: 1600,
        height: 900,
        retainedSource: {
          sha256: 'ccf455df447448159027834cd493a44a757ea4e12165346db3ccc1501e794d49',
          width: 3840,
          height: 2160,
        },
        provenance: 'The deployed 1600x900 JPEG is an optimized derivative of the retained 3840x2160 PNG; source and derivative hashes are recorded separately; verified 2026-09-04. The retained source and custody record are private.',
        ownership: 'review-pending',
        licensing: 'review-pending',
      },
    ],
  },
  sharecli: {
    type: 'systems-sheet',
    alt: 'Process topology drawing connecting concurrent coding agents to queues, coalesced events, shared runtime state, and host resources.',
    annotations: {
      engineering: 'Process observation, queueing, coalescing, and optional FUSE views make burst contention inspectable at the host boundary.',
      product: 'A legible shared-runtime boundary turns coding-agent concurrency from hidden machine pressure into an operable developer workflow.',
    },
    media: { width: 1600, height: 1000 },
  },
  substrate: {
    type: 'systems-sheet',
    alt: 'Provider-routing systems map linking HTTP, CLI, MCP, and A2A callers through policy, health, retry, and budget controls.',
    annotations: {
      engineering: 'One policy boundary coordinates provider health, rate limits, retries, fallbacks, budgets, and auditable execution across four interfaces.',
      product: 'Explicit failure and budget controls make a multi-provider execution surface governable instead of presenting one opaque adapter.',
    },
    media: { width: 1600, height: 1100 },
  },
  'phenotype-omlx': {
    type: 'experiment-note',
    alt: 'Experiment sheet separating the attributed upstream omlx runtime from phenotype-omlx fork additions for routing, Rust performance cores, and evaluation.',
    annotations: {
      engineering: 'The experiment boundary keeps upstream MLX functionality distinct from fork-added multi-backend routing, Rust performance cores, and evaluation paths.',
      product: 'A constrained research fork shortens the loop for comparing local-inference choices on Apple Silicon without overstating production readiness.',
    },
    media: { width: 1400, height: 980 },
  },
  netweave: {
    type: 'experiment-note',
    alt: 'Traffic-simulation study tracing points of interest through A-star routing, a directed road graph, per-road cellular automata, and a WebSocket browser view.',
    annotations: {
      engineering: 'Directed-graph routing handles strategic movement while disjoint cellular automata expose lane-level congestion, waves, and gridlock.',
      product: 'A one-week prototype made the system tradeoff visible: individually attractive routes can degrade aggregate network flow.',
    },
    media: { width: 1600, height: 1100 },
  },
};

export const PROJECTS = [
  { id:'gmk-arch', slug:'gmk-arch', title:'GMK Arch', status:'historical', category:'physical-product', lens:['product','engineering'], featured:true, summary:'Designed and shipped an Arch Linux keyboard keycap set that sold 4,900 units across 10 countries in 30 days, generating ~$432K in revenue.', metrics:[['~4,900','sold line items','canonical user fact'],['~$432K','revenue in 30 days','canonical user fact'],['142K+','community views','canonical user fact; Geekhack corroboration'],['10-region','international retail network','canonical user fact']], technologies:['Product design','Manufacturing','GTM'], gallery:['/public/projects/gmk-arch/hero.png'], links:[['Source page','https://kooshapari.myportfolio.com/'],['Geekhack group buy','https://geekhack.org/index.php?topic=112566.0']], evidence:'EVIDENCE_LEDGER.md', caseStudy:{sections:[['Context','GMK Arch translated Arch Linux visual language and principles into a manufacturable keycap set with a community-led launch path.'],['Discovery','The work connected a clear enthusiast identity to a practical group-buy, retail, and collaboration strategy.'],['Design','Typography, palette, and iconography were developed as a coherent system rather than isolated novelty keys.'],['Prototyping','Render and kitting iterations were used to validate coverage, compatibility, and presentation before production.'],['Manufacturing','Supplier coordination and production constraints shaped the final set, packaging, and fulfillment plan.'],['Economics','Approximately 4,900 sold line items and approximately $432K in 30-day revenue are canonical user facts, not independently verified revenue claims.'],['Distribution','The launch combined community visibility with an approximately 10-region international retail network; the 2021 group-buy thread lists vendors across US, Canada, South America, EU, Oceania, Southeast Asia, UK, Korea, China, and Norway.'],['Outcomes','The canonical 142K+ community-view figure is corroborated by the Geekhack thread’s displayed 142,992 reads; line items are not customers.'],['Retrospective','The durable lesson was treating design, supplier readiness, and community GTM as one operating system.']]} },
  { id:'witf', slug:'witf', title:'WITF Board', status:'historical', category:'physical-product', lens:['product','engineering'], featured:true, summary:'A limited-run mechanical keyboard where I managed the full lifecycle: supplier negotiation, demand forecasting across volume swings, pricing, and fulfillment logistics.', metrics:[['~15 -> ~100 -> ~50','unit planning sequence','canonical user fact'],['$825 -> $650','price change','canonical user fact'],['~$40K','across ~150 line items','canonical user fact']], technologies:['Product operations','Supplier coordination','Fulfillment'], gallery:['/public/projects/witf/hero-01.webp','/public/projects/witf/hero-02.webp'], links:[['Source page','https://ramdesigns.xyz/witf-board'],['Geekhack group buy','https://geekhack.org/index.php?topic=118282.0']], evidence:'EVIDENCE_LEDGER.md', caseStudy:{sections:[['Context','WITF was a full-size Southpaw XT Alice-style board whose plan changed as demand, fulfillment, and timing changed.'],['Discovery','The working expectation moved from ~15 units toward 100, forcing a re-evaluation of production and fulfillment assumptions.'],['Design','The core product was preserved while accessory scope and launch packaging were reconsidered.'],['Prototyping','Supplier and operational feedback informed what could be produced and supported at each volume.'],['Manufacturing','The final negotiation settled around ~50 units after demand softened and timing effects accumulated.'],['Economics','The public group-buy thread lists an $825 price; the historical account records a later move to $650 and an accessory cancellation/refund.'],['Distribution','An external pick/pack change became part of the fulfillment model rather than an afterthought.'],['Outcomes','The historical account describes approximately $40K across approximately 150 line items; line items are not customers.'],['Retrospective','The project demonstrates how preserving a viable core can be better than forcing the original volume plan.']]} },
  { id:'sharecli', slug:'sharecli', title:'ShareCLI', status:'current', category:'systems', lens:['engineering'], featured:true, summary:'A Rust runtime that observes and coordinates hundreds of concurrent AI coding agents — managing process bursts, resource contention, and filesystem behavior.', technologies:['Rust','Linux','FUSE','Observability'], repo:'https://github.com/KooshaPari/sharecli', evidence:'github-pass1-after.md', caseStudy:{sections:[['Problem','Coding-agent workloads create many concurrent processes and resource events; the runtime needs to observe and coordinate them without hiding contention.'],['Context','ShareCLI sits close to the OS/runtime boundary, where process state, filesystem behavior, and thermal pressure affect user-visible performance.'],['Architecture','Rust coordinates process/resource observation, queueing, coalescing, and optional FUSE-backed views for shared execution state.'],['Constraints','The design must remain installable, buildable, and demonstrable on real developer machines while handling bursts instead of assuming a quiet workload.'],['Key decisions','Coalescing, debounce, and queue policies reduce duplicate work; observability makes contention and thermal behavior inspectable.'],['Verification','The current repository evidence includes install/build/demo paths and documents the runtime boundary.'],['Current limitations','No adoption or scale claim is made; hardware-specific contention and FUSE behavior remain important operational variables.'],['Retrospective','The project treats coding-agent concurrency as a systems problem, not merely a CLI feature.']]} },
  { id:'substrate', slug:'substrate', title:'Substrate', status:'current', category:'ai-infrastructure', lens:['engineering'], featured:true, summary:'Multi-provider AI routing layer that handles provider failures, budget constraints, and rate limits across four different interfaces.', technologies:['Rust','Axum','Routing','Observability'], repo:'https://github.com/KooshaPari/substrate', evidence:'github-pass1-after.md', caseStudy:{sections:[['Problem','AI execution becomes operationally difficult when providers fail differently, expose different interfaces, and carry different cost or budget constraints.'],['Context','Substrate provides a policy boundary between callers and model/provider execution.'],['Architecture','The current surface spans HTTP, CLI, MCP, and A2A interfaces with shared routing, provider state, and audit/observability concerns.'],['Constraints','Provider health, quotas, retries, and budgets must remain explicit rather than hidden inside one adapter.'],['Key decisions','Rate limiting, retry/fallback chains, and policy-aware routing make failure behavior deliberate and inspectable.'],['Verification','Repository evidence supports the interface and control-plane scope; no unsupported performance or scale number is presented.'],['Current limitations','Provider behavior and operational policy still depend on deployment configuration and live upstream availability.'],['Retrospective','The useful abstraction is a controllable execution substrate, not a single-provider wrapper.']]} },
  { id:'phenotype-omlx', slug:'phenotype-omlx', title:'phenotype-omlx', status:'research', category:'ai-ml', lens:['engineering'], featured:true, summary:'Apple Silicon inference research fork with Rust performance cores, multi-backend routing, and evaluation tooling for comparing local model variants.', technologies:['Rust','MLX','Apple Silicon','Evaluation'], repo:'https://github.com/KooshaPari/phenotype-omlx', provenance:'Fork/extension of jundot/omlx; upstream attribution retained.', evidence:'github-pass1-after.md', caseStudy:{sections:[['Problem','Local inference research needs a fast iteration loop across model variants, backends, and evaluation workloads on Apple Silicon.'],['Context','phenotype-omlx extends upstream `jundot/omlx`; upstream functionality remains attributed to that project.'],['Architecture','The fork boundary adds multi-backend routing, Rust performance cores, and evaluation paths around an MLX-focused runtime.'],['Constraints','Memory bandwidth, quantization choices, concurrency, and backend differences shape what can be measured locally.'],['Key decisions','Rust isolates performance-sensitive paths while routing and evaluation keep experiments comparable across backends.'],['Verification','Current repository evidence supports the fork/extension boundary and research tooling; no generalized production-scale claim is made.'],['Current limitations','Speculative decoding, quantization, and concurrency work remain research dimensions whose support varies by backend and model.'],['Retrospective','The project keeps upstream credit explicit while using a focused fork to explore Apple-Silicon inference performance.']]} },
  { id:'omniroute', slug:'omniroute', title:'OmniRoute', status:'upstream-contribution', category:'ai-infrastructure', lens:['engineering'], featured:true, summary:'Built routing intelligence, provider integrations, and reliability hardening for a 60K-star AI routing platform — 101 merged PRs in 28 days.', metrics:[['101','merged pull requests','upstream PR history'],['21','upstream releases naming contributions','release notes audit'],['#5','external contributor rank in published upstream census','upstream contributor table']], technologies:['TypeScript','Rust','Routing','OpenAPI','MCP','Provider integration','Reliability'], provenance:'External contribution to `diegosouzapw/OmniRoute`. Not an owned or maintained project.', repo:'https://github.com/diegosouzapw/OmniRoute', evidence:'omniroute-evidence-ledger.md', caseStudy:{sections:[['Classification','PROMINENT COMPACT OSS CONTRIBUTION — earns a prominent portfolio entry but not a full case study. The contribution window is a focused 28-day burst (June 20 – July 18, 2026) and KooshaPari does not own or maintain OmniRoute.'],['Routing intelligence','Built the Bifrost auto-fallback cooldown and introduced latency/speed-optimized routing modes, improving how OmniRoute dispatches requests under provider degradation. Added the `omniroute_pick_fastest_model` MCP tool for downstream tooling.'],['Provider and model integration','Added or extended support for Factory.ai, MiniMax M3 reasoning-content extraction, xAI, Bailian, and OpenAI-compatible MCP Responses; introduced provider manifest infrastructure enabling smarter manifest-gated routing decisions.'],['Reliability and degraded-provider handling','Hardened OmniRoute behavior under production failure: retained cooldowns, circuit-breaking patterns, stream lifetime bounds, DB probe-loop avoidance, and fallback-cache scoping by target URL.'],['API and protocol compatibility','Authored the complete OpenAPI 3.0 specification with Redoc-rendered `/api/docs`; added live WebSocket support for non-loopback clients and cross-client compatibility fixes for Claude, Cline, and shell-tool envelopes.'],['UI and dashboard performance','Asset optimization, health-polling fixes, and onboarding-wizard stability work shipped to upstream.'],['Operational and security documentation','Added a STRIDE-based threat model, per-endpoint latency/cost budgets, a canonical incident response runbook (sev1–sev5), and structured incident-response templates.'],['Verification','Upstream PR history is the authoritative evidence source (`https://github.com/diegosouzapw/OmniRoute/pulls?q=author%3AKooshaPari`). The personal fork (`KooshaPari/OmniRoute`) is NOT a clean staging ground for the 101 upstream PRs — see `fork-state-reconciliation.md`.'],['Claims excluded','No claim of ownership or maintainership. No "125K lines authored" hero metric. No claim that the ~59.9k stars belong to KooshaPari. No claim of current live rank without the "as recorded" qualifier.'],['Retrospective','The lesson is that concentrated, evidence-led contributions to a maintained upstream can be integrated quickly and recognized by maintainers — but the contribution does not become the contributor\'s project.']]} },
  { id:'netweave', slug:'netweave', title:'NetWeave', status:'historical prototype', category:'simulation', lens:['engineering'], featured:true, summary:'A traffic simulation where independently optimal routes created network-wide congestion — demonstrating how local decisions can degrade global flow.', technologies:['Go','A*','Cellular automata','WebSockets','Algorithms'], evidence:'Canonical user brief (2026-08-30); timestamped artifacts to be attached before publication.', caseStudy:{
    overview:'A research-oriented browser simulation of road networks, vehicle flow, and routing decisions. A Go backend streamed state to an HTML/CSS/JavaScript visualization over WebSockets.',
    diagram:'POIs -> A* route cost (road type, speed, turn penalty)\n              |\n              v\n     directed road graph\n       intersections = nodes\n       roads = edges\n              |\n              v\n per-road 2D cellular automata\n acceleration / gaps / lanes / merges\n              |\n              v\n       WebSocket browser view',
    sections:[
      ['Why this simulation architecture','The model separated strategic movement through a directed road graph from local traffic physics. Intersections became graph nodes and road segments became edges, while each road carried a disjoint 2D cellular automaton for vehicles, lanes, and gaps.'],
      ['Directed graph + cellular automata split','A* routed vehicles between points of interest using road type, speed limit, and turn penalties. The Nagel–Schreckenberg-inspired automata handled acceleration, gap-based slowing, randomized driver variability, lane/merge/intersection behavior, and progression into the next segment.'],
      ['Routing model','Vehicles spawned at residential POIs, travelled to commercial POIs, then received a new assignment of the opposite type. Congestion-aware weighting and in-route recalculation were documented as future work, not completed functionality.'],
      ['Emergent traffic behavior','The simulation produced congestion, stop-and-go waves, and gridlock from local rules running on ordinary consumer hardware. Those behaviors made the network-level consequences of routing policy visible rather than theoretical.'],
      ['The system-level routing problem','Within roughly a week, the prototype exposed a mismatch between individually optimal routes and network-wide flow: independently minimizing route cost can concentrate agents on the same attractive segments. The next correction was identified as congestion-aware weighting, dynamic rerouting, and—at the broader system level—occasionally accepting a slower route to reduce aggregate bottleneck pressure.'],
      ['Experimental authoring workflow','An unsubmitted Stable Diffusion + ControlNet workflow translated hand-drawn road sketches into an OSM-like visual normalization and then into backend network geometry. The proof of concept worked at baseline, but limited data, compute, and iteration time kept accuracy below reliable-ingestion quality.'],
      ['What was not finished','Congestion-aware A*, dynamic in-route recalculation, and production-grade sketch ingestion were future or experimental directions. This entry does not claim they shipped.'],
      ['Retrospective / later external comparison','Any comparison to later mapping or routing experiments belongs in a separately sourced retrospective. No claim of prediction, copying, or causal influence is made here.'],
    ],
    disclosure:'AI-assisted implementation reduced the cost and time required to turn the simulation design into an executable environment. The requirements, architecture, simulation model, algorithm selection, routing design, system interpretation, future direction, and identification of the routing failure mode remained user-owned.',
    evidenceRefs:['Canonical user brief supplied 2026-08-30','Repository history, submitted Google Doc, MP4 presentation, screenshots, simulation output, and ControlNet experiment artifacts: locate and attach before public publication.']
  } },
  { id:'byteport', slug:'byteport', title:'BytePort', status:'current', category:'cloud', lens:['engineering','product'], summary:'Declarative Go/AWS deployment platform that separates current delivery from planned features.', technologies:['Go','AWS','Deployment'], repo:'https://github.com/KooshaPari/BytePort', evidence:'github-pass1-after.md' },
  { id:'tracera', slug:'tracera', title:'Tracera', status:'current', category:'developer-tools', lens:['engineering'], summary:'Rust traceability infrastructure for auditing software and agent workflows end-to-end.', technologies:['Rust','Traceability','Audit'], repo:'https://github.com/KooshaPari/Tracera', evidence:'github-pass1-after.md' },
  { id:'dss-cipher', slug:'dss-cipher', title:'DSS Cipher', status:'historical', category:'physical-product', lens:['product'], summary:'Keycap set concept with documented renders, kitting, and community interest on Geekhack.', gallery:['/public/projects/dss-cipher/hero.webp'], links:[['Source page','https://kooshapari2cb9.myportfolio.com/'],['Geekhack interest check','https://geekhack.org/index.php?topic=114490.0']], evidence:'EVIDENCE_LEDGER.md' },
  { id:'cliproxyapi-plusplus', slug:'cliproxyapi-plusplus', title:'CLIProxyAPI++', status:'current', category:'developer-tools', lens:['engineering'], summary:'Multi-provider AI proxy with routing, auth, quotas, and operational controls.', provenance:'Fork of router-for-me/CLIProxyAPI.', repo:'https://github.com/KooshaPari/cliproxyapi-plusplus', evidence:'github-pass1-after.md' },
  { id:'agentapi-plusplus', slug:'agentapi-plusplus', title:'AgentAPI++', status:'current', category:'developer-tools', lens:['engineering'], summary:'Agent API extension with upstream attribution and scope preservation.', provenance:'Fork of coder/agentapi.', repo:'https://github.com/KooshaPari/agentapi-plusplus', evidence:'github-pass1-after.md' },
  { id:'mcpforge', slug:'mcpforge', title:'MCPForge', status:'historical', category:'developer-tools', lens:['engineering'], summary:'MCP tooling with upstream attribution to isaacphi/mcp-language-server.', provenance:'Attribution to isaacphi/mcp-language-server.', repo:'https://github.com/KooshaPari/MCPForge', evidence:'github-pass1-after.md' },
  { id:'forgecode', slug:'forgecode', title:'ForgeCode', status:'historical', category:'developer-tools', lens:['engineering'], summary:'Agent tooling with upstream provenance to tailcallhq/forgecode.', provenance:'Attribution to tailcallhq/forgecode.', repo:'https://github.com/KooshaPari/forgecode', evidence:'github-pass1-after.md' },
  { id:'frostify', slug:'frostify', title:'Frostify', status:'historical', category:'design', lens:['product','engineering'], summary:'Spicetify theme fork with 3,350+ downloads across transparent/frosted styling.', metrics:[['3,350+','GitHub release-asset downloads','GitHub verified']], provenance:'Fork of gwennlbh/Frostify.', repo:'https://github.com/KooshaPari/Frostify', evidence:'github-pass1-after.md' },
].map((project) => ({
  ...project,
  ...(FEATURED_PRESENTATIONS[project.slug]
    ? { presentation: FEATURED_PRESENTATIONS[project.slug] }
    : {}),
}));

export const PROOF_POINTS = [
  ['~$432K','keyboard launch revenue in 30 days'],
  ['10-week plan -> week 3','regulated AI MVP advanced to pilot'],
  ['3 teams / ~15 contributors','cross-functional technical coordination'],
  ['Go + Rust','systems, agent, ML, and infrastructure work'],
];
