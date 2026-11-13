---
version: 1
slug: "app-static-index-html"
primary_target: "app/static/index.html"
related_targets: ["app/static/css/app.css"]
---

# Surface brief: Mesa de ayuda web panel

Scope: the whole single-page panel (app/static: index.html, css/app.css), every route and role. Mode: Operate.

Audience and job: Representative, Admin and Client weigh equally (docs/PRODUCT.md). They read ticket and catalog listings, filter them, and work through forms and ticket actions. Constraints: no external origins (SPEC-UI-06), native controls (SPEC-UI-113), 4.5:1 text contrast (SPEC-UI-72), no horizontal scroll from 360px (SPEC-UI-70), Spanish copy, and no markup or behavior change beyond what the specs allow.

## Direction contract

THESIS: A Material UI admin dashboard rebuilt in plain CSS, with a permanent side drawer, Paper surfaces and dense data tables. It replaces the unstyled browser-default page; it does not imitate a React app's behavior.

OWN-WORLD: Roboto, self-hosted. Primary blue #1976d2 (dark #1565c0). Grey #f5f5f5 canvas, white Paper with MUI elevation 1 shadows and 4px corners. Uppercase 500-weight buttons: contained primary for submit, outlined for secondary. Outlined text fields. Material Symbols icons in the drawer. Selected nav item tinted with primary at 8%. Standard MUI Alerts for error and success.

STORY: Users always see where they are (drawer item selected, page title) and which actions they have, and can scan rows quickly.

FIRST VIEWPORT: A 240px white drawer on the left, holding a brand toolbar with a support_agent icon, the icon list nav and the user at the bottom. On the right, an h1 title (MUI h5) above Paper cards: filters, then the table with pagination. On mobile the drawer becomes a top bar with horizontally scrolling tabs. Login is a centered Paper card.

FORM: pinned by the user. seed: none (pinned): "quisiera que tenga una similitud a los dashboards generados con material ui".

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
