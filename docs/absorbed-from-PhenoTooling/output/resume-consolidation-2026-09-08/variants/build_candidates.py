"""Generate conservative local candidates from the resolved user-source facts."""
from pathlib import Path
import subprocess
out=Path(__file__).parent
identity='# Koosha Paridehpour\n\nSanta Monica, CA | kooshapari@kooshapari.com | kooshapari.com\n\n'
roles={
'swe':('Software Engineering','Software engineering, technical prototyping and systems design experience spanning AI-assisted workflows, traffic simulation and product delivery.'),
'pm':('Product Management','Product management and prototyping experience across hardware programs, software products and AI-assisted workflows.'),
'tpm':('Technical Program Management','Technical coordination, program management and prototyping experience across multidisciplinary software teams and hardware programs.'),
'universal':('Engineering, Product and Technical Programs','Experience spanning software engineering, product management, technical coordination and hardware programs.')}
cvs='''### CVS Health - Development Engineer, AI Innovation (DDAT)
Scottsdale, AZ | Internship | May-August 2025

- Delivered an AI workflow-transpilation project that converted a manual process into an agent workflow; completed the planned ten-week scope by week three, and the system was subsequently piloted.
- Won an innovation challenge with a separate electronic prior authorization proposal.

'''
atoms='''### Atoms.Tech - Technical Program Manager
Tempe, AZ | Capstone engagement | May 2025-January 2026

- Coordinated work across three teams (approximately 15 contributors) developing an AI-assisted requirements and systems-traceability platform amid changing sponsor priorities.
- Took on product and technical coordination, prototyping and engineering guidance as responsibilities expanded beyond initial engineering work.
- Built Discord-based bug and feature intake and deployment controls to simplify sponsor communication and manual deployment steps.

'''
akoma='''### Akoma - Lead Software Engineer
Remote / Ithaca, NY | Contract-style engagement | October 2023-January 2024

- Contributed to internal delivery of an offline-first React Native ERP/accounting application.
- Took on product management, prototyping and engineering guidance alongside software engineering responsibilities.

'''
phenotype='''### Phenotype - Hardware Product Programs

Independent projects | Variable, leisure-time commitment

- Led product and operational work across hardware development, manufacturing and international distribution.
- GMK Arch generated approximately $432K revenue across 4,900 line items; WITF generated approximately $40K across 150 line items.

'''
project='''## Selected Project

### NetWeave - Traffic Simulation

- Designed specifications, architecture and algorithms for a Go traffic simulator combining a directed road graph, per-road cellular automata and A* routing with WebSocket visualization.
- Directed heavily AI-assisted implementation; identified congestion-aware routing and dynamic rerouting as future extensions.

'''
end='''## Education

Arizona State University - B.S. Computer Science, December 2025, Cum Laude

## Technical Skills

Strongest languages: Go, TypeScript, Python, Java, C. Rust: reader-level familiarity and AI-assisted project exposure.
'''
for key,(title,summary) in roles.items():
    entries=(phenotype+atoms+cvs+akoma) if key=='pm' else (atoms+cvs+phenotype+akoma) if key=='tpm' else (cvs+atoms+akoma+phenotype)
    md=identity+'**'+title+'**\n\n'+summary+'\n\n## Experience\n\n'+entries+project+end
    (out/(key+'.md')).write_text(md)
    subprocess.run(['pandoc',str(out/(key+'.md')),'--standalone','--metadata','pagetitle=Koosha Paridehpour - '+title,'--css','resume.css','-o',str(out/(key+'.html'))],check=True)
