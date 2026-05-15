# Issue Backlog: Public Release

This list is intended as a template for GitHub issues.

## P0, Blockers Completed

### 1. Define License For Public Use, Completed

- **Type:** governance
- **Status:** completed
- **Implementation:** [LICENSE](../../../LICENSE), GPL-3.0
- **Acceptance criteria:**
  - license decision documented,
  - `LICENSE` in repository,
  - note in [README.md](../../../README.md).

### 2. Finalize Community Baseline Files, Completed

- **Type:** governance
- **Status:** completed
- **Implementation:** [CONTRIBUTING.md](../../../CONTRIBUTING.md),
  [CODE_OF_CONDUCT.md](../../../CODE_OF_CONDUCT.md),
  [SECURITY.md](../../../SECURITY.md)
- **Acceptance criteria:**
  - `CONTRIBUTING.md` present,
  - `CODE_OF_CONDUCT.md` present,
  - `SECURITY.md` present.

### 3. Provide BPMN 2.0 Reference Models, Completed

- **Type:** subject model
- **Status:** completed
- **Implementation:** [bpmn/invoice-process.bpmn](../../../bpmn/invoice-process.bpmn),
  [bpmn/bookkeeping-process.bpmn](../../../bpmn/bookkeeping-process.bpmn)
- **Acceptance criteria:**
  - at least invoice and bookkeeping BPMN models,
  - reference from documentation and Python engine documented.

### 4. Provide PDF Export For Organization Documentation, Completed

- **Type:** developer experience
- **Status:** completed as manual/generated artifact path
- **Acceptance criteria:**
  - Markdown-to-PDF path documented where needed,
  - PDFs remain generated artifacts,
  - no PDF export requirement for active development.

## P1, Important Improvements Open

### 5. CI Check For Technology Policy

- **Type:** compliance automation
- **Acceptance criteria:**
  - check blocks disallowed technology paths,
  - check verifies cross-IDE synchronization documents.

### 6. Release Checklist For Process Versions

- **Type:** release governance
- **Acceptance criteria:**
  - checklist for tag/release,
  - reference to audit/evidence artifacts.

### 7. Extend Domain Sets

- **Type:** subject content
- **Acceptance criteria:**
  - onboarding for software company,
  - example processes for notary office and tax office.
