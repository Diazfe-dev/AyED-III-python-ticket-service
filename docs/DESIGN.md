---
name: Mesa de ayuda
description: Austere, native-first support-ticket panel; the tool never competes with the task.
colors:
  ink: "#1f2933"
  ink-muted: "#3e4c59"
  paper: "#f5f7fa"
  rule: "#cbd2d9"
  focus-blue: "#1d4ed8"
  error-red: "#8a1c1c"
  success-green: "#14532d"
  disabled-ink: "#4b5563"
  disabled-fill: "#e5e7eb"
typography:
  body:
    fontFamily: "system-ui, -apple-system, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  brand:
    fontFamily: "system-ui, -apple-system, \"Segoe UI\", Roboto, sans-serif"
    fontSize: "1rem"
    fontWeight: 700
    lineHeight: 1.5
spacing:
  xs: "0.5rem"
  sm: "0.75rem"
  md: "1rem"
rounded: {}
components:
  shell:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    padding: "1rem"
  message-error:
    textColor: "{colors.error-red}"
    padding: "1rem"
  message-status:
    textColor: "{colors.success-green}"
    padding: "1rem"
  control-disabled:
    backgroundColor: "{colors.disabled-fill}"
    textColor: "{colors.disabled-ink}"
---

# Design System: Mesa de ayuda

## Overview

**Creative North Star: "The Service Counter"**

A service counter is plain on purpose: the person behind it is there to get something done, not to admire the furniture. This interface works the same way. It sets a calm cool-gray page, one system typeface, a hairline under the header, and leaves everything else (buttons, inputs, selects, tables) to the browser's native controls. The ticket data is the content; the chrome stays out of its way.

Today the system is deliberately thin: 94 lines of CSS, no component classes beyond layout and message states. Its strength is that every control behaves exactly as the platform user expects, for all three roles (Representative, Admin, Client). Its gap is that nothing is styled yet beyond focus, disabled and message states, so any new styling should extend this restraint rather than replace it.

**Key Characteristics:**
- Native controls, unstyled; the browser supplies buttons, inputs, selects and tables.
- One system font stack, no web fonts, no external origins (SPEC-UI-06).
- Cool-gray page, near-black text, one blue reserved for focus.
- Single centered column, 64rem maximum.
- Flat: no shadows, no radii, one hairline border.

## Colors

A restrained cool-gray palette with semantic colors used only for state.

### Primary
- **Focus Blue** (#1d4ed8): the only accent. Used exclusively for the 3px keyboard focus outline. It is never a fill or a link color.

### Neutral
- **Counter Ink** (#1f2933): body text on the page.
- **Quiet Ink** (#3e4c59): loading and empty-state text.
- **Cool Paper** (#f5f7fa): page background.
- **Hairline Gray** (#cbd2d9): the single border, under the header.
- **Disabled Ink** (#4b5563) on **Disabled Fill** (#e5e7eb): disabled buttons, inputs, selects, textareas and disabled links.

### Semantic
- **Error Red** (#8a1c1c): the `role="alert"` message, set bold.
- **Success Green** (#14532d): the `role="status"` message.

### Named Rules
**The Blue Is Focus Rule.** Focus Blue appears only as the focus outline. If it shows up as a fill, a link or a heading, it has been misused.
**The Text-Not-Tint Rule.** State messages are colored text, not colored panels. Error is bold; success is not.

## Typography

**Body Font:** system-ui (with -apple-system, "Segoe UI", Roboto, sans-serif)

**Character:** The platform's own voice. No pairing, no display face; hierarchy comes from weight and the browser's default heading scale.

### Hierarchy
- **Body** (400, 1rem, 1.5): everything, including forms and tables.
- **Brand** (700, 1rem, 1.5): the product name in the header.
- **Message-error** (600, 1rem, 1.5): alert text.

### Named Rules
**The No-Webfont Rule.** No font files and no external font requests. The stack must resolve locally.

## Layout

One centered column. `main`, the header shell and the message bars share `max-width: 64rem`, centered, with `1rem` padding. The header is a wrapping flex row (gap 1rem, vertically centered) so navigation folds onto a second line on narrow screens. Navigation itself is a wrapping flex row with a `0.5rem` row gap and `1rem` column gap. Wide tables scroll horizontally inside a `.table-scroll` wrapper instead of breaking the page. Form fields stack as block labels with a `0.75rem` bottom margin; inputs, selects and textareas never exceed their container.

## Elevation & Depth

Flat. There are no shadows and no layered surfaces. The only depth cue is a 1px Hairline Gray rule under the header. State is communicated by color and outline, never by lift.

### Named Rules
**The Flat-By-Default Rule.** Surfaces stay flat at rest. Introduce a shadow only if a future overlay (for example a confirm dialog) genuinely needs separation from the page.

## Shapes

No custom radii; corners are whatever the native controls draw. The only border in the system is the single 1px header rule. Focus uses a square 3px outline offset by 2px.

## Components

Only structure and state are styled; controls themselves are native.

### Shell (header)
- **Style:** wrapping flex row, 1rem padding, 1px Hairline Gray bottom border, same background as the page. Brand is bold.

### Messages
- **Error (`role="alert"`):** Error Red, weight 600.
- **Status (`role="status"`):** Success Green.
- **Empty:** a message with no content is hidden entirely so it takes no space.

### Loading and empty states
- **Style:** Quiet Ink text, no spinner or illustration.

### Navigation
- **Style:** wrapping flex row of native links, no custom hover, active or current-page treatment yet.

### Forms (`.field`)
- **Style:** block label above the control, native control, `0.75rem` bottom margin, capped at container width.
- **Disabled:** Disabled Ink on Disabled Fill with a `not-allowed` cursor; disabled links use Disabled Ink and the same cursor.
- **Focus:** 3px Focus Blue outline, 2px offset, on every `:focus-visible` element.

## Do's and Don'ts

### Do:
- **Do** keep native controls and add styling only where a state or layout need cannot be met without it.
- **Do** keep the Focus Blue outline on every focusable element (3px, 2px offset).
- **Do** use only the system font stack and same-origin assets.
- **Do** express disabled state with `disabled` or `aria-disabled="true"`, which the spec requires while a request is in flight (SPEC-UI-134).
- **Do** keep copy and labels in Spanish.

### Don't:
- **Don't** load web fonts, icon fonts, CDN scripts or external stylesheets (SPEC-UI-06).
- **Don't** use Focus Blue as a fill, link or decoration color.
- **Don't** add shadows, gradients or rounded decoration to a flat, counter-plain system without an explicit design decision.
- **Don't** put business rules in styling or markup; permissions and transitions belong to the API.
- **Don't** convey state with color alone; pair it with text.
