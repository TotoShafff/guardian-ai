# Guardian AI — Architecture Decision Records

This document records the main technical decisions made for the Guardian AI prototype.
Each record follows a concise ADR style: Decision, Context, Alternatives considered,
Why this option was selected, Trade-offs, and Status. See `docs/ARCHITECTURE.md` for the
full architecture that these decisions implement.

---

## ADR-001 — Implement only two challenge capabilities

**Decision**
Implement exactly two agentic capabilities: (1) review code changes and provide
actionable feedback, and (2) detect a problem, propose a correction, and validate it.

**Context**
The challenge requires demonstrating "at least two capabilities." A broader agentic
system (multi-repo support, autonomous refactoring, CI/CD integration, etc.) is feasible
in principle but not within the time and scope of a technical challenge.

**Alternatives considered**
- Implement three or more capabilities (e.g. add automated PR summarization or release
  notes generation) to look more ambitious.
- Implement only one capability, deeper.

**Why this option was selected**
Two capabilities satisfy the requirement while sharing the same evidence pipeline and
Decision Agent (see ADR-002), which keeps the system small, coherent, and fully
explainable in a short presentation. Adding more capabilities would dilute focus and
increase the surface area for bugs without adding evaluative value.

**Trade-offs**
Less breadth than a "full agentic SDLC assistant" pitch, in exchange for depth,
reliability, and a scope that can be fully explained and demoed.

**Status**
Accepted.

---

## ADR-002 — Combine deterministic evidence with semantic AI analysis

**Decision**
Evidence is gathered from both deterministic tools (Ruff, MyPy, Pytest, ESLint, tsc,
Vitest) and an LLM-based semantic review. The Decision Agent consolidates both instead of
relying on the LLM alone.

**Context**
LLMs are good at semantic reasoning (intent, design smells, missing edge cases) but are
non-deterministic and can hallucinate facts that a compiler or linter would catch
reliably. The challenge explicitly requires that the system must not rely only on the LLM.

**Alternatives considered**
- LLM-only review (send the diff to an LLM and return its opinion).
- Deterministic-tools-only review (no semantic reasoning at all).

**Why this option was selected**
Combining both sources gives objective, reproducible findings (from tools) plus
higher-level semantic insight (from the LLM), each labeled by source and severity in a
common evidence model. This directly satisfies the "not LLM-only" requirement and makes
the final decision auditable.

**Trade-offs**
More moving parts (subprocess orchestration, evidence normalization) than a single LLM
call, in exchange for reliability, reproducibility, and reduced hallucination risk.

**Status**
Accepted.

---

## ADR-003 — Use a Semantic Analysis Agent behind an AI provider abstraction

**Decision**
Semantic reasoning (review generation, fix proposals) is performed by a dedicated
Semantic Analysis Agent that calls an LLM only through a common `AIProvider` interface,
never through a vendor-specific SDK directly.

**Context**
The application must not depend directly on Gemini, OpenAI, or Anthropic, and the initial
concrete provider is still pending. The agent workflow (LangGraph) must be able to invoke
semantic analysis without knowing which vendor is behind it.

**Alternatives considered**
- Call a vendor SDK (e.g. OpenAI's client) directly from the orchestrator nodes.
- Skip the abstraction and hardcode one provider "for now," refactor later.

**Why this option was selected**
An explicit interface (e.g. `generate_review()`, `propose_fix()`) keeps all
vendor-specific logic (auth, request/response shape, prompt formatting) inside isolated
provider adapters. The orchestrator and Decision Agent depend only on the interface,
so selecting or swapping a provider becomes a configuration change, not a code change.

**Trade-offs**
One extra abstraction layer to design and maintain up front, in exchange for zero vendor
lock-in and the ability to defer the provider choice without blocking other work.

**Status**
Accepted.

---

## ADR-004 — Use LangGraph for orchestration

**Decision**
The agent workflow (deterministic checks, semantic review, evidence merging,
classification, fix/validate loop, final decision) is modeled as a LangGraph graph.

**Context**
The workflow has multiple steps with conditional branching (e.g. "is there an
auto-fixable finding?") and needs to run some steps in parallel (tools vs. LLM). It needs
to be explicit and inspectable rather than a hidden chain of prompts.

**Alternatives considered**
- Hand-rolled orchestration (plain Python functions/conditionals).
- A general-purpose agent framework without an explicit graph model (e.g. free-form
  ReAct-style agent loop).
- Other graph-based orchestration frameworks.

**Why this option was selected**
LangGraph provides an explicit graph of nodes and edges that maps directly onto the
architecture's "one responsibility per component" principle, integrates naturally with
Python/FastAPI, and makes the workflow easy to reason about and present.

**Trade-offs**
Adds a framework dependency and a learning curve, in exchange for a workflow that is
explicit, debuggable, and easy to extend with new nodes (e.g. SonarQube evidence) later.

**Status**
Accepted.

---

## ADR-005 — Use FastAPI and Python for the backend

**Decision**
The backend is implemented in Python using FastAPI.

**Context**
The backend must expose a REST API, orchestrate LangGraph, run Python-based deterministic
tools (Ruff, MyPy, Pytest) as subprocesses, and integrate with an LLM provider.

**Alternatives considered**
- Node.js/TypeScript backend (would unify language with the frontend, but LangGraph's
  Python ecosystem and Python-native tools like Ruff/MyPy/Pytest are a more natural fit).
- Django or Flask instead of FastAPI.

**Why this option was selected**
FastAPI offers async support, automatic request/response validation, and OpenAPI docs
with minimal boilerplate. Python is also the natural runtime for LangGraph and for
running Ruff/MyPy/Pytest without cross-process/language friction.

**Trade-offs**
The backend and frontend use different languages, in exchange for the best possible fit
between the backend stack and the deterministic Python tools plus LangGraph.

**Status**
Accepted.

---

## ADR-006 — Use React, Vite, TypeScript, and Tailwind CSS instead of Next.js

**Decision**
The frontend is a single-page application built with React, Vite, TypeScript, and
Tailwind CSS, not a Next.js application.

**Context**
The frontend only needs to trigger a review and render a report returned by the backend
API — there is no requirement for server-side rendering, file-based routing, or backend
API routes on the frontend side.

**Alternatives considered**
- Next.js (adds SSR, API routes, and a more opinionated project structure).
- Plain React with Create React App (unmaintained, slower dev loop than Vite).

**Why this option was selected**
Vite gives a fast dev/build loop for a pure client-side SPA. Next.js's main
strengths (SSR, API routes, file-based routing) are not needed here — the backend already
owns the API — so adopting it would add complexity without benefit, contradicting the
"no unnecessary complexity" principle.

**Trade-offs**
No SSR or built-in routing conventions, which is irrelevant for a small, single-view
review dashboard.

**Status**
Accepted.

---

## ADR-007 — Use PostgreSQL instead of SQLite

**Decision**
Persistence is implemented with PostgreSQL, run as a Docker Compose service.

**Context**
The system needs to persist reviews, evidence, findings, and fix attempts for audit and
inspection. The technology decisions already fix PostgreSQL as the database.

**Alternatives considered**
- SQLite (simpler, file-based, zero extra container).
- No persistence at all (in-memory only).

**Why this option was selected**
PostgreSQL is a production-representative relational database that demonstrates a
realistic setup (connection pooling, migrations, containerized service) and fits the
Docker Compose infrastructure decision already made for the project. It also better
represents how such a system would be deployed in a real e-commerce team's environment.

**Trade-offs**
Slightly more setup than SQLite (an extra container, connection configuration), in
exchange for a more realistic, production-representative persistence layer.

**Status**
Accepted.

---

## ADR-008 — Use Docker and Docker Compose for reproducible local execution

**Decision**
Frontend, backend, and database run as separate services defined in a single Docker
Compose configuration, launched with one command.

**Context**
Reviewers of the technical challenge need to run the whole system reliably without
manually installing Python, Node.js, PostgreSQL, and every deterministic tool.

**Alternatives considered**
- Manual local setup instructions (install Python, Node, Postgres, tool CLIs separately).
- A single monolithic container running everything.

**Why this option was selected**
Docker Compose gives full reproducibility (`docker compose up`) while keeping each
concern (frontend, backend, database) as a separate, inspectable service, matching the
"everything must be reproducible with Docker" principle without introducing
orchestration complexity like Kubernetes.

**Trade-offs**
Requires Docker to be installed locally, in exchange for guaranteed, one-command
reproducibility across environments.

**Status**
Accepted.

---

## ADR-009 — Use environment variables and a committed `.env.example` file

**Decision**
All configuration that varies by environment (database connection, AI provider
selection, provider API key, tool settings) is supplied via environment variables. A
`.env.example` file documenting all expected variables is committed to the repository;
the actual `.env` file is not.

**Context**
The system needs configurable, secret-bearing settings (e.g. LLM API keys) without
hardcoding them, and reviewers need to know which variables to set to run the project.

**Alternatives considered**
- Hardcoded configuration values in source code.
- A secrets manager or vault (e.g. HashiCorp Vault, cloud secret managers).

**Why this option was selected**
Environment variables are the simplest mechanism compatible with Docker Compose and
are sufficient for a local technical challenge. `.env.example` documents the required
configuration surface without exposing real secrets.

**Trade-offs**
Less robust than a dedicated secrets manager for production use, which is unnecessary at
this scope.

**Status**
Accepted.

---

## ADR-010 — Keep the AI provider configurable and vendor-agnostic

**Decision**
The concrete LLM provider used at runtime is selected via environment variable/
configuration, resolved to a specific adapter behind the `AIProvider` interface
(ADR-003). No provider is hardcoded into the orchestrator or Decision Agent.

**Context**
The initial concrete provider is still pending a decision, and the project must not
depend directly on any single vendor (Gemini, OpenAI, Anthropic).

**Alternatives considered**
- Pick one provider now and hardcode it, deferring abstraction to "later."
- Support all three providers with equal depth from day one.

**Why this option was selected**
Deferring the concrete provider choice to configuration unblocks architecture and
implementation work without waiting on a vendor decision, and ensures switching providers
never requires touching orchestrator or Decision Agent code.

**Trade-offs**
The system may initially ship with only one working adapter implemented in depth, but the
seam for adding others is already in place at no extra cost later.

**Status**
Accepted.

---

## ADR-011 — Keep SonarQube outside the MVP

**Decision**
SonarQube is explicitly excluded from the MVP evidence sources. It is documented only as
a possible future evidence source.

**Context**
SonarQube could provide additional static analysis and security-hotspot evidence, but
requires its own server/service and setup effort disproportionate to a short challenge.

**Alternatives considered**
- Integrate SonarQube now as a seventh evidence source.
- Omit any mention of SonarQube entirely.

**Why this option was selected**
The evidence model (ADR-002) is designed to accept new sources without structural
changes, so SonarQube can be documented as a natural extension point without needing to
implement or run it now, respecting the project's "small and explainable scope"
principle.

**Trade-offs**
The MVP evidence set is narrower than it could be, in exchange for a scope that fits the
challenge's time budget.

**Status**
Accepted.

---

## ADR-012 — Exclude Redis, Kubernetes, microservices, RAG, vector databases, PyTorch, model training, and an async job queue from the MVP

**Decision**
The MVP does not use Redis, Kubernetes, a microservices split, RAG, vector databases,
PyTorch, model training/fine-tuning, or an asynchronous job queue.

**Context**
Each of these technologies solves a real problem at a certain scale (caching, container
orchestration, service isolation, knowledge retrieval, custom ML, background processing),
but none of those problems currently exist in this prototype's scope: a single small
example repository reviewed synchronously by one user at a time.

**Alternatives considered**
- Pre-emptively add these technologies to "look more sophisticated" for the challenge.
- Add a subset (e.g. just an async job queue) speculatively.

**Why this option was selected**
Introducing infrastructure to solve problems that do not yet exist would contradict the
"no unnecessary complexity" and "no unnecessary microservices" principles, increase setup
friction for reviewers, and dilute focus from the two required capabilities.

**Trade-offs**
The system does not yet handle high concurrency, long-running background jobs, or
retrieval-augmented context — none of which are required to demonstrate the two target
capabilities at this scale.

**Status**
Accepted.

---

## ADR-013 — Use synchronous review processing for the prototype

**Decision**
A review request is processed end-to-end synchronously within a single HTTP request
lifecycle (or a simple request/poll pattern), without a background job queue.

**Context**
The example repository and diffs used for the demo are small, so total review latency
(tools + LLM calls) is expected to remain within a reasonable request timeout.

**Alternatives considered**
- Asynchronous processing with a job queue and a "pending/running/done" status model.
- WebSocket-based streaming of intermediate progress.

**Why this option was selected**
Synchronous processing is simpler to implement, test, and demo, and is sufficient given
the small, fixed size of the example repository. It avoids introducing a job queue
(ADR-012) before a real scaling need exists.

**Trade-offs**
Would not scale well to large repositories or many concurrent reviews; acceptable given
the prototype's fixed, small demo scope. Noted as a future extension if needed.

**Status**
Accepted.

---

## ADR-014 — Use bounded fix-and-validation attempts

**Decision**
The fix-and-validate loop (propose a correction, then re-run deterministic tools to
validate it) is limited to a small, fixed number of attempts (e.g. one retry) per finding.

**Context**
An unbounded "keep trying until it passes" loop could lead to unpredictable latency, cost,
and behavior, which conflicts with the goal of a transparent, explainable system.

**Alternatives considered**
- Unbounded retries until validation passes or a global timeout is hit.
- No retries at all — propose one fix and report whether it validated, with no second
  attempt.

**Why this option was selected**
A small fixed bound keeps latency and LLM cost predictable while still demonstrating a
genuine propose → validate loop, which is exactly what capability #2 requires. It also
avoids the risk of an "autonomous unbounded fixing agent," which is an explicit non-goal.

**Trade-offs**
May fail to resolve findings that would have succeeded with more attempts, in exchange
for predictable cost, latency, and behavior.

**Status**
Accepted.

---

## ADR-015 — Keep business logic out of the frontend

**Decision**
The frontend only renders data returned by the backend API (review status, findings,
suggested fixes, validation results). Classification, severity assignment, and the final
decision are always computed server-side.

**Context**
Duplicating decision logic on both frontend and backend would create two sources of truth
and risk inconsistent behavior between what is decided and what is displayed.

**Alternatives considered**
- Compute or adjust severity/status on the frontend for a "snappier" UI.
- Allow the frontend to merge/filter evidence client-side using its own rules.

**Why this option was selected**
Keeping all decision logic in the backend guarantees a single source of truth, matches
the "no frontend business logic" principle, and keeps the frontend simple and purely
presentational.

**Trade-offs**
The frontend cannot compute or preview a decision without a round trip to the backend,
which is an acceptable cost for correctness and consistency.

**Status**
Accepted.

---

## ADR-016 — Use `main` as the default Git branch

**Decision**
The repository's default branch is named `main`.

**Context**
A default branch name must be chosen for the repository; there is no project-specific
reason to deviate from current common practice.

**Alternatives considered**
- `master` (legacy default).
- `trunk` or another custom name.

**Why this option was selected**
`main` is the current industry-standard default, requires no special tooling
configuration, and avoids legacy naming with no benefit to this project.

**Trade-offs**
None of significance.

**Status**
Accepted.

---

## ADR-017 — Use Conventional Commits

**Decision**
All commits follow the Conventional Commits format (e.g. `feat:`, `fix:`, `docs:`,
`chore:`).

**Context**
The project benefits from a readable, consistent commit history that clearly
communicates intent, especially important for a challenge where reviewers may inspect
commit history to understand the build-out process.

**Alternatives considered**
- Free-form commit messages.
- A custom commit convention specific to this project.

**Why this option was selected**
Conventional Commits is a well-known, low-overhead standard that produces a
self-documenting history and can support future automation (e.g. changelog generation)
without requiring custom tooling to be built.

**Trade-offs**
Adds a small amount of discipline overhead per commit, in exchange for a clearer,
standardized history.

**Status**
Accepted.

---

## ADR-018 — Create a small example e-commerce repository with intentional defects

**Decision**
A small, purpose-built example e-commerce repository (or fixed set of example diffs)
containing deliberately introduced defects is used as the subject of Guardian AI's
analysis, instead of a large public open-source repository.

**Context**
The system needs a concrete codebase to review and needs to reliably demonstrate both
target capabilities (feedback on a change, and detect/fix/validate a problem) during a
short presentation.

**Alternatives considered**
- Use a large, real public e-commerce repository (e.g. an open-source storefront project).
- Use a randomly selected third-party repository at demo time.

**Why this option was selected**
A small, controlled repository with intentionally introduced defects (style violations,
type errors, a failing test, a fixable bug) guarantees that every capability can be
demonstrated deterministically and quickly, without depending on unpredictable real-world
code or long tool run times. It keeps the demo focused and reproducible.

**Trade-offs**
Less "realistic" than a full production codebase, in exchange for a fast, reliable,
fully controlled demonstration of both required capabilities.

**Status**
Accepted.
