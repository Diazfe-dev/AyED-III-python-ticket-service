# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Three roles weigh equally in design decisions (confirmed):

- **Representative** (phone agent): creates tickets for customers and works the tickets assigned to them.
- **Admin**: manages users, categories, product types and products; reads all tickets in read-only mode.
- **Client**: reads their own tickets and follows their progress.

## Product Purpose

Support-ticket management system (final project for Algoritmos III). A ticket moves through a lifecycle (New → In Progress → Closed, with reopening), accumulates immutable chronological milestones, and triggers notifications. The web panel is a thin client over the same-origin JSON API.

## Positioning

Not established beyond the course context. Undecided; do not invent.

## Operating Context

- Single-page app with hash routes (`#/tickets`, `#/users`, `#/categories`, `#/product-types`, `#/products`, `#/account`, `#/login`), screens per role.
- Served by Flask from `app/static/` (HTML, CSS, ES modules). No build step, no runtime dependencies, no external scripts, styles or fonts (SPEC-UI-06).
- Source of truth for behavior: `specs/07-ui/spec.md` and `docs/REQUERIMIENTOS.md`.

## Capabilities and Constraints

- The UI holds no business rules; permissions, ownership and transitions belong to the API. The UI translates API responses into Spanish messages.
- All UI copy is in Spanish (status labels: Nuevo, En curso, Cerrado; roles: Cliente, Representante, Administrador; Activo/Inactivo).
- Same-origin relative API calls only.
- UI tests: Node `node --test` and Playwright (dev/CI only).
- Adding dependencies requires prior agreement (AGENTS.md).

## Evidence on Hand

No testimonials, customers, metrics or brand assets exist; none may be fabricated.

## Product Principles

1. The API decides; the UI only reflects and never duplicates business rules.
2. Every role gets a clear home screen and only sees what it may do.
3. Stay self-contained: no build step, no external origins.
4. Feedback is explicit and in Spanish: states, errors, loading and empty cases are never silent.

## Accessibility & Inclusion

No product-specific standard established. Open decision.
