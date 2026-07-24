# Guardian AI — Implementation Tasks

This is the day-to-day execution checklist derived from `docs/ROADMAP.md`, following the
decisions in `docs/DECISIONS.md` and the design in `docs/ARCHITECTURE.md`. Tasks are
ordered by dependency within each stage — complete them top to bottom. Each task is sized
to fit in one focused work session and has a clear completion condition.

Priority tags: **[MUST]** required for the MVP · **[SHOULD]** improves quality, trim under
time pressure · **[COULD]** only if time remains.

---

## Stage 0 — Repository and planning

- [x] **[MUST]** Create the project directory structure (`apps/backend`, `apps/frontend`,
  `docker/`, `docs/`, `.cursor/rules`). *Done when all directories exist and match
  `docs/ARCHITECTURE.md` Section 10/11.*
- [x] **[MUST]** Initialize the Git repository with `main` as the default branch. *Done
  when `git branch` shows `main` and an initial commit exists.*
- [x] **[MUST]** Create the GitHub repository and connect it as `origin`. *Done when
  `git remote -v` shows the GitHub URL.*
- [x] **[MUST]** Write `docs/ARCHITECTURE.md`. *Done when all 21 required sections and
  both Mermaid diagrams are present.*
- [x] **[MUST]** Write `docs/DECISIONS.md`. *Done when ADR-001 through ADR-018 are
  recorded with Decision/Context/Alternatives/Why/Trade-offs/Status.*
- [x] **[MUST]** Write `docs/ROADMAP.md`. *Done when all phases, MVP definition, cut list,
  and risk register are present.*
- [x] **[MUST]** Write the root `.gitignore`. *Done when Python, Node, env, Docker, editor,
  and OS artifacts are excluded and `.env.example`/`.cursor/rules`/Markdown are preserved.*
- [ ] **[MUST]** Write `docs/TASKS.md` (this document). *Done when every stage below has
  ordered, checkbox-based tasks.*
- [ ] **[SHOULD]** Add a `.cursor/rules` entry capturing the "no provider-specific logic
  outside adapters" and "no frontend business logic" conventions. *Done when at least one
  rule file exists under `.cursor/rules` and is committed.*
- [ ] **[MUST]** Make the first Conventional Commit for this documentation set (if not
  already committed). *Done when `git log` shows a `docs:` commit covering these files.*

---

## Stage 1 — Backend foundation

- [ ] **[MUST]** Create `apps/backend/pyproject.toml` with project metadata, Python
  version, and dependencies (FastAPI, Uvicorn, LangGraph, SQLAlchemy/driver, Ruff, MyPy,
  Pytest). *Done when `pip install -e .` (or equivalent) resolves without errors.*
- [ ] **[MUST]** Create the backend package layout (`api/`, `orchestrator/`, `tools/`,
  `providers/`, `domain/`, `persistence/`) with empty `__init__.py` files. *Done when the
  layout matches `docs/ARCHITECTURE.md` Section 10.*
- [x] **[MUST]** Bootstrap the FastAPI application instance (`api/main.py` or equivalent).
  *Done when `uvicorn` starts the app locally and serves the OpenAPI docs page.*
- [x] **[MUST]** Implement the configuration/settings module reading environment variables
  (DB URL, AI provider selection, provider API key, tool timeouts). *Done when settings
  load from environment variables with sensible defaults and fail clearly if a required
  variable is missing.*
- [ ] **[SHOULD]** Add structured logging setup (JSON or key-value logs) for the backend
  process. *Done when a log line is emitted on startup and on each request.*

---

## Stage 2 — Database and persistence

- [x] **[MUST]** Implement the PostgreSQL connection (engine/session factory) using the
  configuration from Stage 1. *Done when a connection can be opened against a running
  PostgreSQL instance using settings from environment variables.*
- [x] **[MUST]** Define the SQLAlchemy ORM models (`ReviewModel`, `EvidenceModel`,
  `FindingModel`, `FindingEvidenceModel`, `FixAttemptModel`, `ValidationResultModel`,
  `DecisionModel`) mapping the tables in `docs/ARCHITECTURE.md` Section 12. *Done when
  table names, primary keys, foreign keys, and constraints are verified by metadata-only
  tests, with no live database required.*
- [x] **[MUST]** Set up the migration tool (e.g. Alembic) and generate the initial
  migration for `reviews`, `evidence`, `findings`, `finding_evidence`, `fix_attempts`,
  `validation_results`, `decisions` tables per `docs/ARCHITECTURE.md` Section 12. *Done
  when the migration applies cleanly to an empty database.*
- [x] **[MUST]** Implement domain models: `Evidence`, `Finding`, `Review`, `Decision` as
  plain Python classes with no framework imports. *Done when each model can be
  instantiated and serialized without importing FastAPI or SQLAlchemy.*
- [x] **[MUST]** Implement `ReviewRepository` (`add`, `get_by_id`, `list_recent`, `update`),
  translating between the domain `Review` model and `ReviewModel` and receiving its
  `Session` from the caller. *Done when unit tests verify each method's session
  interaction (add/flush, lookup, descending pagination, update, not-found handling)
  using a mocked `Session`, with no live database required.*
- [ ] **[MUST]** Implement the remaining repository/persistence layer mapping domain models
  to the database tables (`EvidenceRepository`, `FindingRepository`, etc.). *Done when a
  review with its evidence, findings, and fix attempts can be saved and re-read from
  PostgreSQL via a repository call, verified by a script or test.*
- [ ] **[MUST]** Implement the `GET /health` endpoint checking both app liveness and DB
  connectivity. *Done when it returns 200 with the DB reachable and a non-200/degraded
  response with the DB unreachable.*

---

## Stage 3 — Deterministic evidence pipeline

- [ ] **[MUST]** Implement the common `Evidence` model fields (`source`, `severity`,
  `category`, `location`, `message`, `suggested_fix`, `confidence`) per
  `docs/ARCHITECTURE.md` Section 8, reusing/aligning with the Stage 2 domain model.
  *Done when the model matches the documented shape and has a unit test constructing one
  instance per field combination.*
- [ ] **[MUST]** Define the deterministic tool adapter interface (a base class/protocol
  with a `run(target) -> list[Evidence]` contract). *Done when at least one adapter can be
  implemented against it without ad-hoc changes to the interface.*
- [x] **[MUST]** Implement the Ruff adapter: run Ruff as a subprocess against a target
  path, parse its output. *Done when running it against a file with a known lint violation
  returns exactly the expected `Evidence` item(s).*
- [x] **[MUST]** Implement the Pytest adapter: run Pytest as a subprocess against the
  example codebase, parse pass/fail results. *Done when running it against a suite with
  one failing test returns an `Evidence` item marked blocking.*
- [ ] **[MUST]** Implement the ESLint adapter: run ESLint as a subprocess against the
  small React/TypeScript example component, parse its output. *Done when running it
  against the component with a known lint issue returns the expected `Evidence` item.*
- [ ] **[SHOULD]** Implement the MyPy adapter: run MyPy as a subprocess against the Python
  domain, parse its output. *Done when running it against a file with a known type error
  returns the expected `Evidence` item. Not required for the MVP.*
- [ ] **[MUST]** Implement evidence normalization: convert each tool's raw output
  (exit code, JSON/text report) into the common `Evidence` shape, including severity
  classification rules (e.g. "Pytest failure is always blocking"). *Done when normalization
  is a pure function/module independent of subprocess execution, testable with fixed
  sample input.*
- [ ] **[MUST]** Write unit tests for normalization and classification using fixed sample
  tool output (no live tool execution). *Done when tests cover at least one sample per
  adapter (Ruff, Pytest, ESLint) and assert correct severity/category.*
- [ ] **[COULD]** Implement the tsc adapter for the React/TypeScript example component.
  *Done when running it against the component returns an `Evidence` item for a known type
  error, if one is introduced.*
- [ ] **[COULD]** Implement the Vitest adapter, only if the example component gains a test
  file. *Done when running it returns an `Evidence` item for a known failing test.*

---

## Stage 4 — Example e-commerce codebase

- [ ] **[MUST]** Create the example Python e-commerce domain module (e.g. pricing/discount/
  cart logic) as a small, self-contained set of files. *Done when the module runs
  standalone and has no dependency on the backend framework code.*
- [ ] **[MUST]** Introduce one intentional deterministic defect (a Ruff lint violation or a
  failing Pytest test) in the domain module. *Done when running the Ruff or Pytest adapter
  against the module reproduces exactly this defect.*
- [ ] **[MUST]** Introduce one intentional semantic/design defect (e.g. a discount
  calculation that allows a negative total) that Ruff/Pytest do not catch. *Done when Ruff
  and Pytest both pass clean on this specific defect, confirming only semantic review can
  flag it.*
- [ ] **[MUST]** Introduce one intentional fixable defect with a simple, unambiguous
  correct patch (e.g. a failing test with an obvious one-line fix). *Done when a manually
  written patch makes the corresponding Pytest test pass.*
- [ ] **[MUST]** Create the single small React/TypeScript example component or module.
  *Done when it compiles/renders in isolation and contains no routing or state-management
  dependencies beyond the existing frontend project setup.*
- [ ] **[MUST]** Introduce one intentional ESLint-detectable issue in the example
  component. *Done when running the ESLint adapter against it reproduces exactly this
  issue.*
- [ ] **[MUST]** Define and freeze the stable demo scenario (the exact diff/change used for
  the presentation and the smoke test). *Done when the diff is saved as a fixture file (or
  equivalent) referenced by the smoke test in Stage 10.*

---

## Stage 5 — AI provider abstraction

- [x] **[MUST]** Define the `AIProvider` interface (`analyze_code()`, `propose_fix()`)
  per `docs/ARCHITECTURE.md` Section 9. *Done when the interface has type-annotated method
  signatures and no vendor-specific imports.*
- [x] **[MUST]** Implement `MockProvider`: deterministic, canned responses matching the
  `AIProvider` interface, with no network calls. *Done when it returns a fixed, valid
  review/fix response usable by the agent workflow without any API key configured.*
- [x] **[MUST]** Select the concrete real provider and implement its adapter behind
  `AIProvider`. *Done when it successfully returns a real semantic review for a sample
  diff using a configured API key.*
- [ ] **[MUST]** Wire provider selection to configuration (Stage 1 settings), defaulting to
  `MockProvider` when no API key is present. *Done when switching the configured provider
  requires no code change to the orchestrator.*
- [ ] **[SHOULD]** Add a timeout and error-handling wrapper around provider calls so a
  provider failure degrades to an "unavailable" evidence item instead of crashing the
  review. *Done when a simulated provider timeout/error still produces a completed review
  response.*

---

## Stage 6 — LangGraph agent workflow

- [x] **[MUST]** Define the `ReviewWorkflowState` (`TypedDict`) and implement the
  `collect_deterministic_evidence` node calling `RuffTool.analyze()` and
  `PytestTool.analyze()` and merging their results (Ruff first, then Pytest) per
  `docs/ARCHITECTURE.md` Section 7. *Done when it returns `{"evidence": ...}` without
  mutating the incoming state, covered by unit tests with mocked tools.*
- [x] **[MUST]** Implement the Semantic Analysis Agent as the `analyze_semantically`
  LangGraph node calling `AIProvider.analyze_code()` and returning `Finding` items in the
  common shape. *Done when running it standalone against a mocked `AIProvider` returns
  valid `Finding` items without mutating the incoming state.*
- [ ] **[MUST]** Implement the evidence-merge node combining deterministic adapter output
  (Stage 3) and Semantic Analysis Agent output into one evidence list. *Done when the
  merged list contains items from both sources with no shape mismatches.*
- [ ] **[MUST]** Implement the classification step assigning blocking/non-blocking
  severity per the documented rules. *Done when a fixed sample evidence list produces the
  expected classification, covered by a unit test.*
- [ ] **[MUST]** Implement the "auto-fixable finding" conditional branch. *Done when a
  finding flagged as fixable routes to the fix-proposal path and a non-fixable finding
  routes directly to the Decision Agent.*
- [x] **[MUST]** Implement the fix-proposal flow calling `AIProvider.propose_fix()` for an
  auto-fixable finding. *Done when it returns a patch candidate for the Stage 4 fixable
  defect using `MockProvider`.*
- [ ] **[MUST]** Implement the Validation Agent: apply the proposed patch in an isolated
  copy and re-run the relevant deterministic adapter(s) against it. *Done when applying the
  correct patch to the Stage 4 fixable defect results in a passing validation, and an
  incorrect patch results in a failing validation.*
- [x] **[MUST]** Implement the bounded fix-and-validate loop with a fixed attempt limit
  (per ADR-014). *Done when the loop stops after the configured number of attempts even if
  validation keeps failing, without hanging or erroring.*
- [x] **[MUST]** Implement the Decision Agent consolidating all evidence into status,
  blocking/non-blocking findings, suggested fixes, validation results, and rationale.
  *Done when it produces a single structured decision object from a fixed sample evidence
  set, covered by a unit test.*
- [x] **[MUST]** Implement the initial LangGraph graph wiring (`build_review_graph`)
  connecting the four existing nodes in a fixed linear order:
  `collect_evidence -> semantic_analysis -> propose_fixes -> make_decision`. *Done when
  the compiled graph runs end-to-end with mocked dependencies and produces a complete
  `Decision`, covered by unit tests.*
- [ ] **[MUST]** Wire the full LangGraph graph (start → parallel static/semantic evidence →
  merge → classify → conditional fix/validate → decide → persist) per
  `docs/ARCHITECTURE.md` Section 7. *Done when invoking the graph end-to-end with
  `MockProvider` returns a complete decision and persists it via Stage 2's repositories.*

---

## Stage 7 — API endpoints

- [x] **[MUST]** Implement `POST /reviews` accepting a target/diff reference and
  triggering the LangGraph workflow synchronously. *Done when calling it with the Stage 4
  demo scenario returns a completed decision in the response body.*
- [x] **[MUST]** Implement `GET /reviews/{id}` returning a previously persisted review's
  full result. *Done when it returns the same decision structure for a review created via
  `POST /reviews`.*
- [ ] **[MUST]** Define request/response schemas (Pydantic models) matching the Decision
  Agent's output shape. *Done when FastAPI's generated OpenAPI docs show accurate,
  non-generic schemas for both endpoints.*
- [ ] **[SHOULD]** Add basic input validation and error responses (e.g. invalid/missing
  target) with clear HTTP status codes. *Done when an invalid request returns a 4xx with a
  descriptive error message instead of a 500.*

---

## Stage 8 — Frontend

- [x] **[MUST]** Bootstrap the React + Vite + TypeScript + Tailwind CSS project in
  `apps/frontend`. *Done when `npm run dev` serves a blank page without errors.*
- [x] **[MUST]** Implement the typed API client wrapping `POST /reviews` and
  `GET /reviews/{id}`. *Done when it can be called from a component and returns
  correctly typed data matching the backend schemas.*
- [x] **[MUST]** Implement the review submission screen (trigger the fixed demo scenario).
  *Done when clicking "Run review" calls the API client and stores the result in
  component state.*
- [x] **[SHOULD]** Implement the review progress/loading state shown while the request is
  in flight. *Done when a loading indicator is visible between submission and response.*
- [x] **[MUST]** Implement the findings display (blocking and non-blocking findings list,
  with evidence source per item). *Done when a sample API response renders each finding
  with its severity and source visibly distinguished.*
- [x] **[MUST]** Implement the final decision summary view (status + rationale). *Done
  when the overall status and rationale text render above the findings list.*
- [x] **[MUST]** Implement the suggested fix and validation result display (patch preview +
  pass/fail badge). *Done when a fixable finding's proposed patch and validation outcome
  render clearly for the user.*
- [x] **[SHOULD]** Apply a minimal responsive layout usable on a laptop screen. *Done when
  the page is readable and usable at common laptop widths without horizontal scrolling.*
- [ ] **[COULD]** Add visual polish (icons/badges per evidence source, improved loading
  animation). *Done when added without introducing any client-side severity/status logic.*

---

## Stage 9 — Docker Compose and reproducibility

- [ ] **[MUST]** Write the backend `Dockerfile` (installs dependencies, deterministic
  tools, runs Uvicorn). *Done when `docker build` succeeds and the resulting container
  serves `GET /health`.*
- [ ] **[MUST]** Write the frontend `Dockerfile` (build + serve the Vite production
  bundle). *Done when `docker build` succeeds and the resulting container serves the app
  on its configured port.*
- [ ] **[MUST]** Write `docker-compose.yml` defining `frontend`, `backend`, and `db`
  (PostgreSQL) services with correct networking. *Done when `docker compose config`
  validates without errors.*
- [ ] **[MUST]** Write `.env.example` documenting every environment variable read by the
  backend (DB connection, AI provider selection, provider API key, tool settings). *Done
  when every variable used in Stage 1 configuration appears here with a placeholder
  value.*
- [ ] **[MUST]** Verify one-command local startup (`docker compose up`) brings up all
  three services successfully. *Done when `GET /health` responds successfully after
  startup with no manual intervention beyond copying `.env.example` to `.env`.*
- [ ] **[MUST]** Verify database initialization runs migrations automatically on startup
  (or document the one-time manual step). *Done when a fresh `db` volume ends up with all
  Stage 2 tables present after `docker compose up`.*
- [ ] **[MUST]** Perform a clean-clone verification: clone the repository into a new empty
  directory, copy `.env.example` to `.env`, fill required values, and run
  `docker compose up`. *Done when the full system works from this clean clone with no
  undocumented steps.*

---

## Stage 10 — Testing, documentation, and delivery

- [ ] **[MUST]** Write backend unit tests for domain models, evidence normalization, and
  classification rules (extends Stage 3 tests). *Done when `pytest` passes for all
  domain-logic tests with adapters/providers mocked.*
- [ ] **[MUST]** Write an integration test running the full LangGraph graph against
  `MockProvider` and the Stage 4 example codebase. *Done when it asserts a complete,
  correctly structured decision without calling any real external API.*
- [ ] **[SHOULD]** Write frontend component tests for the findings list and decision
  summary using a fixed API response fixture. *Done when `vitest` (or equivalent) passes
  for these two components.*
- [ ] **[MUST]** Write the end-to-end smoke test running the frozen Stage 4 demo scenario
  through the full stack (API to Decision Agent). *Done when it passes twice in a row
  with consistent finding categories.*
- [ ] **[MUST]** Write `README.md` (project overview, setup instructions, how to run the
  demo). *Done when a person unfamiliar with the project can follow it to a working local
  instance.*
- [ ] **[MUST]** Review `docs/DECISIONS.md` for completeness against the final
  implementation (the decision document required by the challenge). *Done when every ADR
  still matches what was actually built, with any deviation noted.*
- [ ] **[MUST]** Write the demo script (step-by-step walkthrough: trigger scenario, show
  each evidence source, show fix/validate loop, show final decision). *Done when it can be
  followed live within a target time budget without improvisation.*
- [ ] **[SHOULD]** Perform a final architecture/code review pass comparing the
  implementation against `docs/ARCHITECTURE.md`. *Done when discrepancies are either fixed
  or explicitly documented as known deviations.*
- [ ] **[MUST]** Complete the final delivery checklist (see `docs/ROADMAP.md` Section 4).
  *Done when every item on that checklist is checked off.*

---

## Current progress

- [x] Project structure created (`apps/backend`, `apps/frontend`, `docker/`, `docs/`,
  `.cursor/rules`).
- [x] Git repository initialized (`main` branch, initial commit).
- [x] GitHub repository created and connected as `origin`.
- [x] `docs/ARCHITECTURE.md` completed.
- [x] `docs/DECISIONS.md` completed.
- [x] `docs/ROADMAP.md` completed.
- [x] `.gitignore` completed.
- [ ] `docs/TASKS.md` completed (this document).
- [ ] Everything in Stages 1–10 above: not started.
