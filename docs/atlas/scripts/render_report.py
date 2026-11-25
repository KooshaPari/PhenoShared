#!/usr/bin/env python3
"""Render a programmatic PDF reading edition from the package's planning records."""
from __future__ import annotations
import json,re
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,KeepTogether
ROOT=Path(__file__).resolve().parents[1]
products=json.loads((ROOT/'records/products.json').read_text())
support=json.loads((ROOT/'records/supporting-targets.json').read_text())
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='KickerA',fontName='Helvetica-Bold',fontSize=9,leading=12,textColor=colors.HexColor('#277A78'),spaceAfter=12))
styles.add(ParagraphStyle(name='TitleA',fontName='Helvetica-Bold',fontSize=28,leading=32,textColor=colors.HexColor('#142D42'),spaceAfter=18))
styles.add(ParagraphStyle(name='HeadA',fontName='Helvetica-Bold',fontSize=17,leading=21,textColor=colors.HexColor('#142D42'),spaceAfter=12))
styles.add(ParagraphStyle(name='SubA',fontName='Helvetica-Bold',fontSize=10.5,leading=14,textColor=colors.HexColor('#277A78'),spaceBefore=10,spaceAfter=4))
styles.add(ParagraphStyle(name='TextA',fontName='Helvetica',fontSize=10,leading=14,spaceAfter=7))
styles.add(ParagraphStyle(name='SmallA',fontName='Helvetica',fontSize=8,leading=11,spaceAfter=5,textColor=colors.HexColor('#4A5964')))
story=[]
def plain(s):return s.translate(str.maketrans({'—':'-','–':'-','→':'->','×':'x','’':"'",'“':'"','”':'"','≥':'>=','≤':'<='})).encode('ascii','replace').decode()
def p(text,style='TextA'):return Paragraph(escape(plain(text)),styles[style])
def add(text,style='TextA'):story.append(p(text,style))
def section(title,text):add(title,'SubA');add(text)
def page(kicker,title):
 if story:story.append(PageBreak())
 add(kicker.upper(),'KickerA');add(title,'HeadA')

def footer(canvas,doc):
 canvas.saveState();w,h=A4
 canvas.setStrokeColor(colors.HexColor('#D7E0E6'));canvas.line(44,39,w-44,39)
 canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#4A5964'))
 canvas.drawString(44,26,'Phenotype | Atlas and Assurance Program v1.1 | 2026-09-15')
 canvas.drawRightString(w-44,26,str(doc.page));canvas.restoreState()

add('PHENOTYPE / ENGINEERING PROGRAM','KickerA');story.append(Spacer(1,34))
add('Explain the product.\nQualify the evidence.\nReduce the burden.','TitleA')
add('Codebase atlas, independent QA, granular specifications, semantic compression, dependency adoption and comparative product proof.','HeadA')
story.append(Spacer(1,20))
add('Planning cohort: 23 product/lab candidates, four pooled foundation homes and three supporting surfaces. Ten Tracera workstreams; product/assurance pairs elsewhere. PhenoApps and the absorbed Agentora capability are conditional additional plans.')
section('Read this as a work program','This is not a fresh 52-repository audit or a product qualification. Source inspections and prior audit findings are inherited context. Product pilots are planned, not executed. No repository, deployment, engine state or lifecycle was mutated while generating the package.')
section('Use the complete source tree','The ZIP contains the editable Markdown plans, subject dossiers, proposed requirements, provisional specification bundles, task graph, schema examples, reference checks and preserved contextual archives. START-HERE.md is the controlling reading entrypoint.')
section('Revision 1.1: ecosystem-first evolution','Reuse includes our own work. Improve shared capabilities with current and credible future consumers in view, and judge aggregate effects rather than repository-local convenience. Details: architecture/ECOSYSTEM-FIRST-EVOLUTION.md.')
section('Outstanding terminology','SROC/CDP have not been authoritatively defined in the retrieved context. Their names are retained without invented expansions. Unambiguous atlas and assurance work continues.')

page('01 / Operating decision','One connected understanding of each product')
section('Explain, do not merely enumerate','A directory tree and API index are useful but insufficient. Connect exact source and artifact identity to user jobs, capabilities, interfaces, state, constraints, tests, evidence and dissatisfaction. Unknown purpose remains unknown; an agent must not invent historical rationale.')
section('Account for every relevant artifact','Code, tests, native shells, scripts, configuration, data migrations, assets, prompts, generated files, vendor source and distribution inputs are all in scope. Use semantic units and source spans. Generated boilerplate inherits its producer contract; a critical three-line permission check may need several invariants.')
section('Preserve authority','Tracera owns the persistent reconciled product model. Subject files retain their accepted source contracts. Actual work engines own transitions. Native runners produce test evidence. PhenoDocs renders views. A generated index or topic set cannot become a second mutable authority.')
section('Reduce custom maintenance','Evaluate mature facilities and dependencies first, then narrow adapters or patches, then custom implementation where justified. Preserve ordering, errors, state, recovery, cancellation, compatibility, numerical properties and resource budgets. Fewer lines alone is not a win.')
section('Keep product work moving','Use portable repo-local records before Tracera is complete. Close real useful slices while expanding the atlas. Do not wait for perfect documentation to fix a known defect, and do not call one useful repair the completion of the product.')
section('Measure outcomes','Track verified/released/adopted capabilities, installed-CVP lead time, defects discovered after install, stale evidence, safe duplicate removal, maintenance burden and recovery interventions. Commits, tags and document volume are not substitutes.')

page('02 / Assurance','Independent floors and credible failure detection')
section('Coverage cells','Required unit, integration and E2E each retain at least 85% coverage in approved component/platform/profile/metric cells. Existing stricter policies remain. Lines, branches, functions and behavioral obligations are not interchangeable. Supplemental combined coverage cannot hide a weak required cell.')
section('Denominators before numerators','Inventory eligible zero-hit units and freeze reviewed support/critical sets. Missing instruments, unsupported metrics and zero denominators are explicit limits, not 100%. Do not exclude difficult files, platforms or cases simply to pass.')
section('Coverage is not a failure quota','All selected mandatory checks actually run and pass. Critical obligations are completely satisfied. Skips, empty selections, unavailable backends, malformed reports, timeouts and quarantined flakes do not count as passes. A known required defect cannot hide in the uncovered 15%.')
section('Test the gate','Seed missing families, wrong revisions, changed denominator/critical sets, failed checks, mixed accumulators, broken links and malformed judge responses. Prove they propagate to non-acceptance. A schema and checksum establish only limited structure/integrity, not producer authenticity or domain truth.')
section('Preserve qualitative evidence','Game/UI/audio quality needs explicit qualitative review alongside automation. Actual journeys must show the real artifact and backend. Branding can be rich and authored; it cannot impersonate implemented UI or performance evidence.')
section('Reference tooling only','The package checker is intentionally limited. It always refuses to grant lifecycle approval. Its synthetic fixtures and measured test coverage concern the checker itself, not Civis, AgilePlus, Tracera or any other product.')

page('03 / Reuse and composition','Simplify without deleting the useful semantics')
section('A useful refactor contract','Before changing a custom subsystem, record the outputs, errors, ordering, side effects, compatibility, permissions, persistence, timing and resources that must survive. Characterize actual useful behavior separately from bugs. Validate the actual consumers after replacement.')
section('A dependency decision is broader than features','Compare functional and semantic fit, resource costs, testability, debugger behavior, supply chain, licensing, update/patch effort, operational burden and exit. Avoid wrappers that simply rename the full native API and become a second maintenance surface.')
section('Patch discipline','Record upstream revision, owned delta, tests, owner, upstream issue where applicable, supported range and removal condition. A clean patch apply does not prove correct integration. Qualify upgrades and state compatibility.')
section('Applet boundaries','An applet declares capabilities, ports, state, permissions, lifecycle, resources, surfaces and children. Composites can be applets. An applet is not automatically a repo, daemon or microservice. Use direct calls for suitable same-process paths and justify isolation/network overhead.')
section('Dead paths','Accepted current behavior should be reconnected or implemented. Future experiments may retain specs without misleading executable stubs. Superseded/duplicate code needs consumer/provenance review. Optional/dynamic/external usage requires investigation. Unknown is not permission to delete.')
section('Foundation consolidation','A future Pheno workspace can reduce repo overhead if packages keep precise ownership, interfaces, tests and release contracts. Do not replace a wide portfolio with one context-hostile universal product.')

page('03A / Ecosystem-first evolution','Our own work is upstream too')
section('Reuse across both boundaries','Prefer use, modification, adaptation or a narrow wrapper over parallel handrolling, for external AND owned capabilities. Search our real packages, source owners, consumer contracts and prior extractions. Do not preserve a weak owned mechanism just because we wrote it.')
section('Optimize the whole system','A repository assignment limits writes, not reasoning. Compare user value and total maintenance, dependency coupling, upgrade/patch work, build/runtime resources, migration and coordination. A local win that shifts greater burden or regressions downstream is not an ecosystem win.')
section('Current and future consumers','Supported current consumers need preserved contracts and actual tests. Committed planned consumers need explicit requirements and appropriate contract spikes. Plausible future uses guide inexpensive seams and optionality, not speculative universal frameworks. Unknown consumers are not zero consumers.')
section('One owner, bounded adapters','Improve the authoritative shared capability where appropriate. Keep product-specific policy at the proper boundary. Intentional separate implementations can be justified by different semantics or constraints. A future Pheno workspace is not one mandatory runtime, database or release train.')
section('Every meaningful change carries impact','Record owned/external options, affected consumers, preserved behavior and resources, expected versus measured effects, tests, migration, rollback and review ownership in the existing work/PR/ADR. Keep purely local changes lightweight. A valid record is not an approval or parity proof.')
section('Continue, do not perpetually rewrite','Reassess on new consumers, repeated workarounds, upstream changes and new constraints. Keep increments useful and scoped. Coordinate other owners through linked tasks and exclusive worktrees. Local PR closure does not erase remaining adoption or duplicate retirement.')

page('04 / Ten seats','Tracera: one product, bounded workstreams')
rows=[('1','Product/schema/integration','Accepted model and thin witness'),('2','Source inventory/indexing','Actual anchors and supported extraction'),('3','Intent/spec ingestion','Provenance and supersession'),('4','Persistence/reconciliation','Durable model and recovery'),('5','Impact/dissatisfaction','Genuine gaps and uncertainty'),('6','Assurance ingestion','Native evidence and freshness'),('7','Product exploration UI','Bounded readable graph/search'),('8','CLI/MCP/API','Same semantics and permissions'),('9','Packaging/runtime','Actual install and operational proof'),('10','Independent evaluator','Baseline and adversarial verification')]
t=Table([[p('Seat','SmallA'),p('Scope','SmallA'),p('Outcome','SmallA')]]+[[p(a,'SmallA'),p(b,'SmallA'),p(c,'SmallA')] for a,b,c in rows],colWidths=[32,210,250],hAlign='LEFT')
t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E9F0F3')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,0),0.7,colors.HexColor('#AEBCC6'))]));story.append(t)
section('Integrate before multiplying abstractions','Agree a minimal entity/source/evidence contract first. The existing ALM-oriented atlas crate can be reused where useful, but it must not redefine the product as work bookkeeping. One integration owner and independent verifier accept the combined result.')
section('First witness','Import a real product, trace a capability into source and obligations, expose a real discrepancy, update from accepted evidence and survive restart. A hardcoded graph demo does not establish this outcome.')
section('Capacity is not execution concurrency','Ten plus two for each other 22 products means 54 potential product sessions. Build, GPU, browser/native capture, external quota and review capacity need separate limits. Protect foreground games and live audio.')

page('05 / Comparison','Prove a reason to keep the custom implementation')
section('Three claim levels','A design can have a plausible advantage; a measured implementation can outperform a defined baseline; a product recommendation additionally needs reliable installation, UX, recovery and maintenance. Do not promote these levels silently.')
section('Fair experiment','Use competent direct, upstream and composed baselines. Separate controlled replay, matched live runs and idiomatic whole-stack comparisons. Record exact models, versions, tasks, hardware, caches, budgets, failures and interventions. Predeclare critical invariants and meaningful margins.')
section('Writing ergonomics','Measure concepts learned, undocumented behavior, glue, errors, debugging, testing and change amplification. Add approval, a new tool, persistence, provider replacement, cancellation and a framework upgrade after the first version works. LOC is supporting context, not the answer.')
section('Agentora','First recover the actual surviving framework API; Cmdra and historical templates using agentkit are not sufficient. Compare direct SDK, OpenAI Agents SDK, LangGraph, CrewAI, Mastra, PydanticAI and a relevant Rust baseline such as Rig. No framework is predeclared the winner.')
section('Accept negative results','A maintained dependency, small wrapper or narrow patch set may be the best outcome. A legitimate internal/fork contract can justify retained code without invented public novelty. The study must retain failed, inconclusive and disadvantageous results.')
section('Research scope','The reference URLs and subject comparators are seeds, not a fresh SOTA review. Expand relevant longlists before architecture decisions and run a justified smaller executable shortlist. Do not pad to a count or claim globally exhaustive search.')

for i,prod in enumerate(products,1):
 page(f'Product {i:02d} / 23',prod['name'])
 add(prod['role'],'SmallA')
 section('Atlas boundary','; '.join(prod['atlas_questions'][:4])+'.')
 section('Current question, not a fresh verdict','; '.join(prod['carry_forward_risks'][:2])+'. Revalidate the inherited baseline at the current subject revision.')
 section('Pilot',prod['scenario'])
 section('Negative cases','; '.join(prod['failure_cases'][:4])+'.')
 section('Measure','; '.join(prod['metrics'][:5])+'.')
 section('Advantage to prove',prod['advantage_hypothesis'])
 section('CVP evidence',prod['cvp_acceptance'])
 add('Full editable plan: '+prod['dossier']+' | Comparative execution is planned, not completed.','SmallA')

for subset,title in [(support[:4],'Pooled foundations'),(support[4:],'Supporting and conditional targets')]:
 page('Supporting work',title)
 for rec in subset:
  section(rec['name']+' / '+rec['role_class'],rec['atlas']+' '+rec['acceptance'])
 add('These are capability/consumer obligations, not automatically separate product seats. Source/target migrations require accepted scope and authority.','SmallA')

page('Finish / Limits','Use the package without overstating it')
section('What has been created','Editable project-specific dossiers, pilot plans, proposed program contracts, provisional feature bundles, schemas, task graph, agent assignments, synthetic examples, reference checkers and tests. Original contextual archives and exact visible human requests are preserved with hashes.')
section('What has not been performed','No fresh complete GitHub audit, native product suite, installed product inspection, SOTA benchmark, migration, release, DNS/provider change or actual work-engine transition. No product superiority or completion is certified.')
section('SROC/CDP','The exact terms are unresolved. Recover their original definitions and map them deliberately. Do not invent an acronym expansion or let that block unambiguous atlas and assurance progress.')
section('Validation scope','See VALIDATION_REPORT.md and validation/ for actual executed results. Schema and linkage checks do not prove semantic completeness. The evidence checker is a reference integrity layer, not an authenticated approval engine.')
section('Next action','Give each current pair its relevant dossier and prompt. Bind source, scope, actual artifact, critical obligations and first useful target. Keep normal work moving; choose mature reuse when evidence favors it; close a real current viable product instead of generating another unbounded planning corpus.')

out=ROOT/'report/ATLAS-ASSURANCE-PROGRAM.pdf'
SimpleDocTemplate(str(out),pagesize=A4,rightMargin=44,leftMargin=44,topMargin=44,bottomMargin=53,title='Phenotype Atlas, Assurance and Semantic Compression Program',author='Phenotype planning package',subject='Proposed portfolio work program; not product certification').build(story,onFirstPage=footer,onLaterPages=footer)
print(out)
