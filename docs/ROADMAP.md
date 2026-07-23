# Guardian AI — Roadmap

This roadmap sequences the work needed to deliver a working, explainable MVP of Guardian
AI within a short technical-challenge timeframe. It follows the architecture in
`docs/ARCHITECTURE.md` and the decisions in `docs/DECISIONS.md`. Priorities use
**Must / Should / Could**: *Must* items are required for the MVP to be demoable and to
satisfy the challenge; *Should* items materially improve quality but can be trimmed under
time pressure; *Could* items are nice-to-haves, only attempted if time remains.

---

## Phase 0 — Planning and repository foundation

**Goal**
Establish the documented architecture, decisions, and repository conventions before any
implementation code is written.

**Deliverables**
- `docs/ARCHITECTURE.md` (architecture, diagrams, evidence model, non-goals).
- `docs/DECISIONS.md` (ADR-001…ADR-018).
- Git repository initialized with `main` as default branch, Conventional Commits in use.
- Project structure in place (`apps/backend`, `apps/frontend`, `docker/`, `docs/`,
  `.cursor/rules`).
- Cursor project rules committed (`.cursor/rules`).

**Acceptance criteria**
- Both architecture documents exist, are internally consistent, and are readable
  standalone.
- Repository has a clean initial commit history following Conventional Commits.
- Directory structure matches the one referenced by later phases (no ad-hoc folders).

**Priority:** Must

**Dependencies:** None (this is the starting point).

**Risks / scope-control notes**
- Risk: over-polishing documentation at the expense of implementation time. Mitigation:
  treat Phase 0 docs as "good enough to guide the build," not final — `README.md` and the
  demo script (Phase 7) are where the final narrative is polished.

---

## Phase 1 — Backend foundation

**Goal**
Stand up a running, containerized FastAPI backend with database connectivity and no
business logic yet.

**Deliverables**
- Python project setup (dependency manifest, project layout matching
  `docs/ARCHITECTURE.md` Section 10: `api/`, `orchestrator/`, `tools/`, `providers/`,
  `domain/`, `persistence/`).
- FastAPI application bootstrap.
- Configuration module reading environment variables (see Phase 6 for `.env.example`).
- PostgreSQL connection (engine/session setup).
- Database migrations for the core tables (`reviews`, `evidence`, `findings`,
  `fix_attempts` — see `docs/ARCHITECTURE.md` Section 12).
- Domain models (`Evidence`, `Finding`, `Review`, `Decision`) as framework-independent
  Python classes.
- `GET /health` endpoint (or equivalent) verifying app + DB connectivity.
- Backend `Dockerfile`.

**Acceptance criteria**
- Backend container builds and starts via Docker.
- Health-check endpoint returns success once the database is reachable.
- Migrations run cleanly against a fresh PostgreSQL instance.
- Domain models have no framework or infrastructure imports.

**Priority:** Must

**Dependencies:** Phase 0 (structure, conventions).

**Risks / scope-control notes**
- Risk: over-designing the ORM/migration layer. Mitigation: one migration tool, minimal
  schema, no speculative columns beyond what Section 12 already defines.

---

## Phase 2 — Evidence pipeline

**Goal**
Produce normalized, testable evidence from deterministic tools, independent of the LLM
and the orchestration graph.

**Deliverables**
- Common `Evidence` model implementation (matches `docs/ARCHITECTURE.md` Section 8:
  `source`, `severity`, `category`, `location`, `message`, `suggested_fix`, `confidence`).
- Deterministic tool adapter interface (a single contract every adapter implements: run
  against a target path/diff, return a list of `Evidence`).
- Adapters for **the minimum tools required for the demo**: **Ruff** (static analysis)
  and **Pytest** (test execution) for the Python business-logic domain, plus **ESLint**
  for the single small React/TypeScript example component (Phase 4). **MyPy** is optional
  and not required for the MVP; **tsc**/**Vitest** are deferred (see Should/Could below).
- Normalization logic converting each tool's native output (exit code, JSON/text report)
  into `Evidence` items.
- Unit tests for normalization (raw tool output → `Evidence`) and for severity
  classification (e.g. "a Pytest failure is always blocking").

**Acceptance criteria**
- Running each adapter against a known-bad sample file produces the expected `Evidence`
  items with correct severity/category.
- The ESLint adapter, run against the single small React/TypeScript example component
  (Phase 4), produces the expected `Evidence` item(s) using the same normalized shape as
  the Python adapters.
- Normalization and classification are covered by unit tests using fixed sample tool
  output (no live tool execution required for these tests).
- Adding a new adapter requires no changes to the `Evidence` model or to consumers of it.

**Priority:** Must (Ruff + Pytest for the Python domain, ESLint for the React/TypeScript
example component); **Should** (MyPy, as additional Python type-checking evidence, not
required for the MVP); **Could** (tsc and Vitest adapters, only if the example component
grows to justify them).

**Dependencies:** Phase 1 (domain models, project layout).

**Risks / scope-control notes**
- Risk: trying to integrate all six tools listed in the architecture doc. Mitigation:
  per the scope decision, ship the three tools that matter for the demo reliably
  (Ruff, Pytest, ESLint) rather than six unreliable ones; MyPy, tsc, and Vitest remain
  optional/future work (already reflected in `docs/ARCHITECTURE.md` Section 20).

---

## Phase 3 — AI provider and agent workflow

**Goal**
Implement the provider-agnostic AI abstraction and the LangGraph orchestration that ties
deterministic evidence and semantic evidence together into a final decision.

**Deliverables**
- `AIProvider` interface (`generate_review()`, `propose_fix()`, per
  `docs/ARCHITECTURE.md` Section 9).
- `MockProvider` implementation: deterministic, canned responses for tests and for local
  runs without a real API key.
- One real provider adapter implementing `AIProvider` (concrete vendor selected via
  configuration; see ADR-010 — the choice itself does not block this phase).
- Semantic Analysis Agent (LangGraph node calling `AIProvider.generate_review()`).
- Fix proposal flow (LangGraph node calling `AIProvider.propose_fix()` for auto-fixable
  findings).
- Validation Agent (re-runs the relevant deterministic adapters against the proposed
  patch and reports pass/fail).
- Decision Agent (consolidates all evidence into status, blocking/non-blocking findings,
  suggested fixes, validation results — the only node producing the final decision).
- LangGraph graph wiring all nodes per `docs/ARCHITECTURE.md` Section 7 (parallel
  static/semantic evidence gathering, merge, classify, conditional fix/validate, decide).
- Bounded fix-and-validation attempts (fixed retry limit, per ADR-014).

**Acceptance criteria**
- The full graph runs end-to-end against `MockProvider` with no real API key, producing a
  structured decision — this is the primary integration test path.
- The full graph also runs end-to-end against the one real provider adapter, using a real
  or sandbox API key from `.env`.
- The fix/validate loop terminates within the configured attempt limit in all cases
  (never loops indefinitely).
- Decision Agent output includes: status, blocking findings, non-blocking findings,
  suggested fixes, validation results, and a human-readable rationale.

**Priority:** Must (interface, `MockProvider`, one real adapter, Semantic Analysis Agent,
Decision Agent, basic LangGraph wiring); **Should** (fully bounded, robust fix/validate
loop with clear failure handling).

**Dependencies:** Phase 1 (domain models), Phase 2 (deterministic evidence to merge
with LLM evidence).

**Risks / scope-control notes**
- Risk: spending too much time evaluating multiple real providers. Mitigation: per scope
  decision, only one real provider is required — pick early (see open decision in
  `docs/ARCHITECTURE.md` Section 9) and move on; `MockProvider` covers the rest of
  development and testing.
- Risk: unbounded or flaky fix/validate loops. Mitigation: hard attempt limit enforced in
  code, not just documented.

---

## Phase 4 — Example e-commerce codebase

**Goal**
Provide a small, controlled example repository that reliably demonstrates both target
capabilities.

**Deliverables**
- A small example e-commerce module (e.g. pricing/discount/cart logic in Python) as the
  **main domain**, used as the subject of analysis — not a full application, just enough
  realistic domain code. This module carries the important business defects.
- Intentionally introduced defects in the Python domain, at minimum:
  - One **deterministic defect** (a Ruff style/lint violation, or a failing Pytest test).
  - One **semantic/design defect** that only an LLM-based review would flag (e.g. a
    discount calculation that silently allows negative totals, missing edge-case
    handling, or a misleading function name/contract).
  - One **fixable defect with validation** (a defect simple enough for the LLM to propose
    a correct patch, that a deterministic tool/test can confirm as resolved — e.g. a
    failing Pytest test with an obvious one-line fix).
- One single small **React/TypeScript component or module**, added alongside the Python
  domain to demonstrate that the evidence architecture also supports frontend analysis.
  It is **not** a second application: no routing, no state management, no additional
  build tooling beyond what the Phase 5 frontend project already provides. It contains
  at least one ESLint-detectable issue so the ESLint adapter (Phase 2) has a concrete,
  reliable target.
- A stable, fixed demo scenario: a specific diff/change against this example codebase used
  consistently for the presentation and for the end-to-end smoke test (Phase 7).

**Acceptance criteria**
- Running the deterministic adapters (Phase 2) against the Python domain reproduces the
  intended defects consistently.
- The semantic defect is not caught by Ruff/Pytest alone (proving the value of the
  Semantic Analysis Agent).
- The fixable defect, once patched by the fix-proposal flow (Phase 3), passes validation.
- Running the ESLint adapter against the small React/TypeScript component reproduces its
  intended issue consistently, proving the evidence model generalizes across stacks. This
  component is not required to participate in the semantic review or the fix/validate
  loop — its role is limited to demonstrating cross-stack deterministic evidence.
- The same fixed diff produces the same categories of findings on repeated runs (allowing
  for LLM wording variance).

**Priority:** Must (Python domain module with the three defect types, stable demo
scenario, and the single small React/TypeScript component with its ESLint-detectable
issue — kept intentionally minimal to avoid growing the MVP scope).

**Dependencies:** Phase 2 (to verify deterministic and ESLint defects are caught), Phase 3
(to verify the semantic defect and the fixable/validated defect).

**Risks / scope-control notes**
- Risk: an example codebase that's too large or too subtle, making the demo unpredictable.
  Mitigation: keep it to a handful of files, and pick defects that are almost guaranteed
  to be caught deterministically or semantically — don't rely on LLM creativity for the
  demo's core narrative.
- Risk: the React/TypeScript example growing into a second, more complete application.
  Mitigation: cap it at one component/module with one ESLint-detectable issue; it exists
  only to prove the evidence architecture generalizes, not to add a second demo scenario.

---

## Phase 5 — Frontend

**Goal**
Provide a minimal, purely presentational UI to trigger a review and inspect its result.

**Deliverables**
- React + Vite + TypeScript + Tailwind CSS project bootstrap.
- Typed API client wrapping the backend REST endpoints.
- Review submission screen (select/trigger the fixed demo scenario or a diff).
- Review progress/loading state (since processing is synchronous, a simple loading
  indicator while the request is in flight).
- Final decision summary view (status, rationale).
- Blocking and non-blocking findings list.
- Evidence source display (which tool or the LLM produced each finding).
- Suggested fix and validation result display (patch preview + pass/fail).
- Minimal responsive layout (usable on a laptop screen at minimum; not a design-system
  effort).

**Acceptance criteria**
- A user can trigger a review from the UI and see the final decision without touching the
  API directly.
- All displayed data (status, severity, source, fix, validation) comes verbatim from the
  backend response — no client-side computation of severity/status (per ADR-015).
- The UI renders correctly for both a "clean" review (no blocking findings) and a review
  with blocking findings, fixes, and validation results.

**Priority:** Must (submission screen, findings list, decision summary); **Should**
(evidence source display, suggested fix/validation display, polished loading state);
**Could** (visual polish beyond a minimal responsive layout).

**Dependencies:** Phase 3 (backend must return a stable response shape to build against).

**Risks / scope-control notes**
- Risk: scope creep into a full dashboard (history, filters, multi-repo selection).
  Mitigation: one screen, one scenario, per the architecture's explicit non-goals.

---

## Phase 6 — Docker and reproducibility

**Goal**
Make the entire system runnable on a clean machine with a single command.

**Deliverables**
- `docker-compose.yml` defining `frontend`, `backend`, and `db` (PostgreSQL) services.
- `.env.example` documenting every required environment variable (DB connection, AI
  provider selection, provider API key, tool settings).
- One-command local startup (`docker compose up`).
- Database initialization (migrations run automatically on startup, or documented as a
  one-time setup step).
- Verified clean-machine setup instructions (a fresh clone + `.env` from `.env.example` +
  `docker compose up` results in a working system).

**Acceptance criteria**
- `docker compose up` from a clean clone (with a filled-in `.env`) brings up all three
  services and the health-check endpoint responds successfully.
- The frontend can reach the backend, and the backend can reach PostgreSQL, purely through
  Compose service networking (no manual host configuration).
- `.env.example` has no missing variables (every variable read by the backend is listed).

**Priority:** Must

**Dependencies:** Phase 1 (backend Dockerfile), Phase 5 (frontend to containerize).

**Risks / scope-control notes**
- Risk: environment drift between the developer's machine and a reviewer's clean machine.
  Mitigation: actually test the clean-machine flow before delivery (see Phase 7 checklist),
  don't assume it works.

---

## Phase 7 — Quality and delivery

**Goal**
Confirm the system is correct, explainable, and ready to present within the deadline.

**Deliverables**
- Backend tests (unit tests from Phase 2/3, covering domain logic, normalization,
  classification, and the Decision Agent's rules).
- Frontend component tests only where valuable (e.g. rendering of the findings list and
  decision summary given a fixed API response fixture) — not exhaustive coverage.
- End-to-end smoke test: the fixed demo scenario (Phase 4) run through the full stack,
  asserting a final decision with the expected structure.
- `README.md` (setup instructions, project overview, how to run the demo).
- Decision document required by the challenge (`docs/DECISIONS.md` — already produced in
  Phase 0, reviewed for completeness here).
- Demo script (a short, rehearsed walkthrough: trigger the fixed scenario, show evidence
  from each source, show the fix/validate loop, show the final decision).
- Final architecture/code review pass (confirm implementation matches
  `docs/ARCHITECTURE.md`; note and document any deviations).
- Delivery checklist (see below) completed.

**Acceptance criteria**
- All Must-priority deliverables from Phases 0–6 are done and demonstrable.
- The end-to-end smoke test passes reliably (re-run at least twice to confirm stability).
- A reviewer unfamiliar with the project can follow `README.md` to run the system and
  reproduce the demo scenario.
- The demo script can be executed live within a few minutes.

**Priority:** Must (backend tests, smoke test, README, demo script); **Should** (frontend
component tests, final architecture review pass).

**Dependencies:** All previous phases.

**Risks / scope-control notes**
- Risk: running out of time for polish. Mitigation: this phase's Must items are testing
  and documentation of what already exists — not new features. If time is short, cut
  frontend component tests before cutting the smoke test or the README.

---

## 1. MVP definition

The MVP is the smallest system that satisfies the challenge and is fully explainable:

- Backend (FastAPI) orchestrating a LangGraph workflow.
- Deterministic evidence from **Ruff and Pytest** for the Python business-logic domain,
  plus **ESLint** for the single small React/TypeScript example component. **MyPy** is
  optional and not required for the MVP.
- Semantic evidence from **one real LLM provider**, plus a **`MockProvider`** for tests
  and fallback.
- A Decision Agent producing status, blocking/non-blocking findings, suggested fixes, and
  validation results.
- A bounded fix-and-validate loop demonstrating capability #2.
- A small example e-commerce codebase: a Python domain module with the three defect types
  described in Phase 4, plus one small React/TypeScript component demonstrating that the
  evidence architecture also supports frontend analysis (not a second application).
- A minimal React frontend to trigger the fixed demo scenario and display the result.
- PostgreSQL persistence of reviews, evidence, findings, and fix attempts.
- Full reproducibility via Docker Compose + `.env.example`.
- `README.md`, `docs/DECISIONS.md`, a passing end-to-end smoke test, and a demo script.

## 2. Optional enhancements (only if time remains)

In priority order, attempted only after the MVP above is fully working and demoed:

1. MyPy adapter for the Python domain, adding stricter type-checking evidence (already
   Should-priority in Phase 2; promote if time allows).
2. TypeScript compiler (tsc) adapter for the small React/TypeScript example component.
3. Vitest adapter, if the example component gains a test file.
4. Additional frontend polish (better loading states, evidence source icons/badges).
5. A second real AI provider adapter, purely to demonstrate the abstraction is genuinely
   swappable (not required by the challenge).
6. Additional example defects/scenarios beyond the one stable demo scenario.
7. Structured logging enhancements (correlation IDs surfaced in the UI for traceability).

## 3. Explicit cut list

The following are deliberately **not** built, regardless of remaining time, per
`docs/ARCHITECTURE.md` Section 19 and `docs/DECISIONS.md`:

- SonarQube integration.
- Authentication / authorization of any kind.
- CI/CD pipeline integration (e.g. GitHub Actions triggering reviews).
- Redis, Kubernetes, a microservices split, RAG, vector databases.
- PyTorch or any model training/fine-tuning.
- An asynchronous job queue or WebSocket streaming (processing stays synchronous).
- Support for multiple repositories or arbitrary user-supplied codebases.
- Multiple real AI provider implementations as an MVP requirement (only one is required;
  a second is optional per Section 2 above).
- Unbounded/autonomous self-fixing agents.

## 4. Delivery readiness checklist

- [ ] `docker compose up` works on a clean machine/clone with a filled `.env`.
- [ ] Health-check endpoint responds successfully after startup.
- [ ] The fixed demo scenario produces: at least one deterministic finding, at least one
      semantic finding, and one successfully validated fix.
- [ ] Decision Agent output includes status, blocking/non-blocking findings, suggested
      fixes, validation results, and rationale.
- [ ] Frontend displays the above without any client-side severity/status computation.
- [ ] Backend unit tests pass; end-to-end smoke test passes at least twice in a row.
- [ ] `README.md` setup instructions independently verified (fresh clone walkthrough).
- [ ] `docs/ARCHITECTURE.md` and `docs/DECISIONS.md` reviewed for consistency with the
      final implementation; deviations documented.
- [ ] Demo script rehearsed end-to-end within a target time budget.
- [ ] No secrets committed; `.env.example` up to date with every variable actually used.

## 5. Recommended implementation order

1. Phase 0 (already complete: architecture, decisions, structure, conventions).
2. Phase 1 — backend foundation (needed by everything else).
3. Phase 2 — evidence pipeline (Ruff and Pytest adapters first, then ESLint once the
   example component from Phase 4 exists; normalization + tests throughout; MyPy only if
   time allows).
4. Phase 4 (start early, in parallel with Phase 2) — draft the Python domain module and
   its defects, plus the single small React/TypeScript component, so Phase 2/3 have a
   real target to validate against instead of synthetic fixtures.
5. Phase 3 — AI provider abstraction, `MockProvider` first (unblocks agent workflow
   development without waiting on a real API key), then the real provider adapter and the
   full LangGraph graph.
6. Phase 6 — Docker Compose wiring, done as soon as backend + DB exist, refined again once
   frontend exists (don't leave containerization until the very end).
7. Phase 5 — frontend, built against the stabilized backend response shape from Phase 3.
8. Phase 7 — testing, README, demo script, final review, delivery checklist.

Rationale: containerization (Phase 6) and the example codebase (Phase 4) are pulled
earlier than their numbering suggests, because verifying "it runs in Docker" and "the
defects are real" early avoids late, hard-to-fix surprises.

## 6. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Real LLM provider API key/access delayed or rate-limited | Medium | High | Build and test against `MockProvider` first; the real provider is only needed for the final demo rehearsal. |
| Deterministic tool output format changes/differs across environments (version drift) | Low | Medium | Pin tool versions in the backend Docker image; test normalization against fixed sample output, not live version-dependent output. |
| Fix/validate loop produces flaky or non-reproducible results in the demo | Medium | High | Use a small, well-understood fixable defect (Phase 4); bound attempts (ADR-014); rehearse the exact scenario multiple times. |
| Docker Compose setup fails on the evaluator's machine | Medium | High | Verify the clean-machine flow explicitly as a Phase 7/6 acceptance criterion before delivery, not assumed. |
| Scope creep (adding MyPy/tsc/Vitest, extra providers, extra findings, or growing the React/TypeScript example into a second application) consumes time needed for polish/testing | High | Medium | Enforce the cut list and optional-enhancements ordering; Must-priority items in each phase take precedence; the example component stays capped at one file. |
| Time runs out before the frontend is fully wired to the backend | Medium | High | Stabilize the backend response shape early (end of Phase 3) so frontend work is not blocked on backend changes late in the schedule. |
| LLM output format inconsistent, breaking Evidence normalization on the semantic side | Medium | Medium | Use structured prompting (schema-constrained output) and defensive parsing with a fallback "unavailable" evidence item rather than a crash. |
