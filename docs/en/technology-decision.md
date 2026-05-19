# Technology Decision For The Pattern Repository

## Result In One Sentence

The binding standard is:

- documentation in Markdown as the source, with PDF export only as a generated
  artifact,
- process execution in Python, while the subject-matter process remains
  BPMN 2.0 first,
- BPMN 2.0 as the canonical subject-matter model, `bpmn-js` as the planned
  visual editing layer, with Mermaid only for overviews.

## Assessment Of The Current State

The current state is useful as a start, but not yet the best final form for
scalable enterprise documentation. The reasons are:

- strong collaborative Markdown documentation,
- strong Python reference logic,
- but BPMN 2.0 had not yet been defined as the binding source norm.

This policy closes that gap.

## a) Documentation: Markdown vs AsciiDoc vs Superdoc

### Assessment

- `Markdown`: best readability, broadest tool support, ideal for LLM, Copilot
  and Cursor collaboration.
- `AsciiDoc`: stronger for complex publication layouts and classic manual
  structures.
- `Superdoc`: no resilient de facto standard for long-term, audit-proof
  enterprise documentation.

### Decision

- The source remains `Markdown`.
- PDF is generated from Markdown only as an export artifact.
- AsciiDoc is not maintained as a second manual source to avoid double
  maintenance.

This combines collaboration and export capability.

## b) Python Code-First For Business Processes Under BPMN 2.0

### Assessment

Pure code-first is not optimal for business departments in the long run,
because:

- subject-matter logic in code becomes difficult for non-IT reviewers,
- deviations between target process and implementation become visible late.

### Decision

- `BPMN 2.0 first` for subject-matter process models.
- `Python` as the execution and integration layer.
- Python must follow the BPMN model, not the other way around.

This improves readability, auditability and maintainability for both IT and
business departments.

## c) BPMN 2.0 Visualization: bpmn-js, Mermaid Or Alternatives

### Assessment

- `bpmn-js`: suitable as an embeddable BPMN 2.0 web modeler because
  subject-matter users can edit processes visually.
- `Mermaid`: very good for simple overview diagrams, but not a full BPMN 2.0
  source format.
- `PlantUML`: useful for technical diagrams, but also not a full BPMN 2.0
  replacement.
- `BPMN 2.0 XML` with suitable BPMN tooling: the best choice for binding
  subject-matter process models and exports.

### Decision

- Binding subject-matter source: BPMN 2.0 XML.
- Planned editing layer: `bpmn-js` with a restricted palette,
  [bpmn/nac-moddle.json](../../bpmn/nac-moddle.json) and Python validation.
- Mermaid only as an additional view for management and quick overviews.
- PlantUML optional for technical architecture, not for the subject-matter BPMN
  source.

## Benefit For Business Departments

- The organization can understand processes primarily through visual BPMN
  models.
- IT and business departments work from the same process truth.
- Documentation is versioned, exportable and audit-ready.
- [docs/en/bpmn-js-business-layer.md](bpmn-js-business-layer.md) describes the
  NaC path from visual editor to checked pull request.
