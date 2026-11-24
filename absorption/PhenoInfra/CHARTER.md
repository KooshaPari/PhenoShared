# phenodocs Charter

## 1. Mission Statement

**phenodocs** is a documentation platform and knowledge management system designed to provide unified, searchable, and versioned documentation for the entire Phenotype ecosystem. The mission is to create a single source of truth for all Phenotype documentation—combining API references, guides, tutorials, and architectural documentation into a cohesive, discoverable knowledge base that evolves with the codebase.

The project exists to eliminate documentation fragmentation—ensuring that developers can find accurate, up-to-date information about any Phenotype component from a single, well-organized location.

---

## 2. Tenets (Unless You Know Better Ones)

### Tenet 1: Documentation as Code

Docs live with code. Version controlled. Reviewed in PRs. Tested in CI. Docs and code in sync. No separate documentation process.

### Tenet 2. Search-First Design

Information found through search. Fast search. Relevant results. Searchable code. Searchable prose. Find what you need quickly.

### Tenet 3. Versioned Documentation

Docs versioned with releases. Read docs for your version. Migration guides between versions. No confusing version mismatch.

### Tenet 4. Generated and Curated

API docs generated from code. Guides written by humans. Tutorials maintained. Both valuable. Both supported.

### Tenet 5. Multi-Format Output

Web documentation. PDF exports. IDE-integrated docs. Offline docs. Multiple consumption formats.

### Tenet 6. Contribution Ease

Easy to contribute docs. Clear contribution guide. Quick edit workflow. Review process. Credit contributors.

### Tenet 7. Quality Standards

Vale linting. Style guide enforced. Broken link checking. Out-of-date detection. Quality gates for docs.

---

## 3. Scope & Boundaries

### In Scope

**Documentation Generation:**
- API reference generation
- Type documentation
- Configuration documentation
- Changelog generation
- Diagram generation

**Documentation Platform:**
- Web documentation site
- Search functionality
- Version management
- Navigation and organization
- Cross-linking

**Content Management:**
- Markdown processing
- MDX support
- Asset management
- Code embedding
- Live code examples

**Quality Tools:**
- Vale linting integration
- Link checking
- Spell checking
- Out-of-date detection
- Coverage reporting

**Distribution:**
- Static site generation
- PDF export
- IDE plugins
- Offline packages

### Out of Scope

- Source code hosting (use Git)
- Wiki functionality (use wikis)
- Community forums (use forums)
- Video hosting (use video platforms)

### Boundaries

- Documentation platform, not content creation
- Organization, not authorship
- Publishing, not editing
- Aggregation, not original storage

---

## 4. Target Users & Personas

### Primary Persona: Developer Drew

**Role:** Developer using Phenotype
**Goals:** Find answers quickly, understand APIs
**Pain Points:** Outdated docs, scattered information
**Needs:** Accurate search, current docs, clear examples
**Tech Comfort:** High, documentation user

### Secondary Persona: Tech Writer Tina

**Role:** Documentation contributor
**Goals:** Easy contribution, clear workflow
**Pain Points:** Complex contribution process
**Needs:** Simple editing, preview, review process
**Tech Comfort:** Medium, documentation specialist

### Tertiary Persona: API Designer Alex

**Role:** API maintainer
**Goals:** API docs generated correctly
**Pain Points:** Poor generation, missing docs
**Needs:** Accurate generation, customization, examples
**Tech Comfort:** Very high, API expert

---

## 5. Success Criteria (Measurable)

### Coverage

- **API Coverage:** 100% of public APIs documented
- **Guide Coverage:** Core workflows documented
- **Example Coverage:** 80%+ of features have examples
- **Freshness:** 90%+ of docs updated within 6 months

### Quality

- **Vale Pass Rate:** 95%+ of docs pass linting
- **Link Health:** 99%+ of links valid
- **Search Relevance:** 80%+ first result relevant
- **User Satisfaction:** 4.0/5+ satisfaction

### Performance

- **Build Time:** <5 minutes for full site
- **Search Speed:** <1 second results
- **Page Load:** <2 seconds
- **Availability:** 99.9%+

---

## 6. Governance Model

### Component Organization

```
phenodocs/
├── generator/       # Documentation generation
├── platform/        # Web platform
├── search/          # Search engine
├── quality/         # Quality tools
├── renderer/        # Rendering engine
└── cli/             # CLI tools
```

### Development Process

**New Features:**
- UX review
- Performance testing
- Accessibility review

**Content Standards:**
- Style guide compliance
- Review process
- Quality gates

---

## 7. Charter Compliance Checklist

### For New Documentation

- [ ] Generated or curated appropriately
- [ ] Cross-linked
- [ ] Search indexed
- [ ] Quality checked

### For Platform Changes

- [ ] Performance tested
- [ ] Accessibility reviewed
- [ ] Mobile tested

---

## 8. Decision Authority Levels

### Level 1: Maintainer Authority

**Scope:** Bug fixes, content updates
**Process:** Maintainer approval

### Level 2: Docs Team Authority

**Scope:** New sections, features
**Process:** Team review

### Level 3: Technical Steering Authority

**Scope:** Breaking changes, architecture
**Process:** Steering approval

### Level 4: Executive Authority

**Scope:** Strategic direction
**Process:** Executive approval

---

*This charter governs phenodocs, the documentation platform. Great docs enable great development.*

*Last Updated: April 2026*
*Next Review: July 2026*
