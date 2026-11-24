# Domain model

This is a proposed interchange vocabulary, not a claim that Tracera currently implements each type. Local native schemas can map into it without losing provenance.

## Entities

### intent

human-source, intent, interpretation, decision, assumption, conflict.

### product

product, user-job, persona, journey, capability, applet, surface.

### implementation

repository, package, source-unit, symbol, build-profile, interface, state-machine, data-entity, migration, config-key, dependency, asset.

### assurance

obligation, test, fixture, oracle, measurement, run, evidence, exception.

### delivery

artifact, release, installation, deployment, consumer.

### analysis

claim, dissatisfaction, hypothesis, experiment, work-package, task, observation, actor, permission, resource-lease.

## Relationships

| Relation | Source | Target |
|---|---|---|
| defines | human-source | intent |
| interprets | interpretation | intent |
| supersedes | decision | decision |
| constrains | intent | capability |
| contains | product | capability |
| realizes | capability | user-job |
| exposes | applet | interface |
| owns-state | applet | data-entity |
| composes | applet | applet |
| implements | source-unit | capability |
| located-in | source-unit | repository |
| member-of | package | repository |
| calls | symbol | symbol |
| requires | capability | dependency |
| produces | build-profile | artifact |
| supports | build-profile | surface |
| uses-config | source-unit | config-key |
| migrates | migration | data-entity |
| derives-from | asset | asset |
| generated-by | source-unit | artifact |
| obligates | capability | obligation |
| verifies | test | obligation |
| uses-fixture | test | fixture |
| interpreted-by | measurement | oracle |
| executes | run | test |
| reports | run | measurement |
| retains | run | evidence |
| measures | measurement | obligation |
| qualifies | evidence | artifact |
| publishes | release | artifact |
| installs | installation | artifact |
| deploys | deployment | artifact |
| consumes | consumer | interface |
| evidences | observation | claim |
| challenges | evidence | claim |
| affects | dissatisfaction | capability |
| supported-by | dissatisfaction | evidence |
| tests-hypothesis | experiment | hypothesis |
| compares | experiment | product |
| addresses | work-package | dissatisfaction |
| decomposes | work-package | task |
| depends-on | task | task |
| permitted-by | task | permission |
| claimed-by | task | actor |
| leases | task | resource-lease |
| covered-by | obligation | exception |
| equivalence-candidate | source-unit | source-unit |
| moved-from | source-unit | source-unit |
| stales | observation | evidence |
| visible-as | product | surface |

Every edge records applicability and evidence/interpretation origin. `equivalence-candidate` is not a migration approval. `qualifies` needs actual supporting proof. Observed, reported and proposed graph layers are separately queryable. Unknown edges remain visible rather than inferred as absent. Stable identities do not imply immutable meaning; meanings evolve through versioned decisions and contracts.
