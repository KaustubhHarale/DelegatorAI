# DelegatorAI Design System

DelegatorAI is an AI project coordinator for college teams. It helps a project lead
understand what is moving, what is blocked, and what needs a human follow-up.
The interface should feel calm, capable, and trustworthy: a focused workspace for
making decisions, not a generic admin template.

This document is the source of truth for future UI work in this React 18 + Vite
application. It describes visual decisions and interaction contracts. It does not
change the current mock-data behavior, API contract, or existing views.

## Product principles

1. **Clarity before decoration.** Every screen answers what needs attention next.
2. **Progress is legible.** Status, ownership, due dates, and blockers are visible
   without opening a detail view.
3. **AI is accountable.** Coordinator actions are explained, timestamped, and
   distinguishable from human activity.
4. **Calm urgency.** Blockers are prominent without making the whole workspace feel
   alarming.
5. **Real density, generous grouping.** Show useful project information, but use
   spacing and hierarchy instead of borders everywhere.
6. **Demo-safe behavior.** UI states must work with the existing local mock data
   when the backend is unavailable.

## Current foundation and intended evolution

The current UI is a dark workspace with a fixed sidebar, sticky top bar, page
headers, task tables, KPI panels, activity feeds, drawers, and task creation
forms. It already uses DM Sans for body text, Manrope for display text, compact dashboard
surfaces, and semantic task accents. The visual direction is now a near-black
developer-tool workspace with restrained emerald interaction accents.

Keep the dark-first foundation because it suits an always-on coordination tool and
the existing product identity. Refine it in future work by:

- using flat charcoal surface steps instead of decorative gradients wherever possible;
- reserving emerald for primary interaction, selection, focus-adjacent emphasis, and AI intelligence;
- using teal, amber, red, and slate only for meaningful task states;
- reducing low-contrast micro-labels and excessive chrome;
- keeping cards as grouping surfaces, not nested containers inside every component;
- preserving the existing views, demo data, and API fallback behavior.

## Foundations

### Color tokens

Use CSS custom properties in `src/styles.css`. Components must reference semantic
tokens rather than hard-coded colors.

```css
:root {
  --color-canvas: #0B0D0C;
  --color-sidebar: #111512;
  --color-surface: #171C18;
  --color-surface-raised: #1D231E;
  --color-surface-hover: #252D26;
  --color-border: #2B342D;

  --color-ink: #F0F4F0;
  --color-ink-secondary: #A0AAA2;
  --color-ink-muted: #78837A;
  --color-ink-disabled: #59645B;

  --color-primary: #10B981;
  --color-primary-hover: #059669;
  --color-primary-pressed: #047857;
  --color-primary-soft: #123D2F;

  --color-pending: #A0AAA2;
  --color-progress: #10B981;
  --color-blocked: #F0A34A;
  --color-complete: #34D399;
  --color-danger: #F87171;
  --color-info: #7AA889;

  --color-focus: #6EE7B7;
  --color-selection: #164E3B;
  --color-success: #34D399;
  --color-warning: #F0A34A;
  --color-error: #F87171;
  --color-on-accent: #ffffff;
}
```

Color rules:

- Canvas is the deepest near-black green. Surfaces rise by charcoal tone, never by a heavy shadow.
- Primary emerald is for the main action, selected navigation, AI affordances, and
  focus-adjacent emphasis. Do not use it for every icon.
- The emerald accent is intentionally restrained; most text, surfaces, borders, and
  secondary controls remain neutral charcoal or slate-green.
- `--color-blocked` is amber because a blocker needs attention but is not always a
  failure. Use danger only for destructive actions or unrecoverable errors.
- Completed is mint-teal, not green used indiscriminately for every success message.
- Text in normal reading content must use `--color-ink` or `--color-ink-secondary`.
  Muted text is for metadata only.
- Do not introduce gradients, glow effects, or new accent colors without a product
  reason and a contrast check. Existing component-specific colors should migrate
  to these semantic roles during later view phases.

### Visual principles

- Near-black and charcoal surfaces replace the previous navy-heavy palette.
- Emerald accents provide a distinctive developer-tool signature without coloring
  every icon or status.
- Subtle borders and surface differentiation define grouping; resting panels do not
  need glowing outlines or decorative shadows.
- Typography and practical information hierarchy take priority over ornament.
- Statuses remain distinguishable through labels, icons, and text as well as color.

### Typography

Use the existing families to avoid a dependency change:

- **Display and headings:** Manrope, 600-800.
- **Body and controls:** DM Sans, 400-700.
- **Code or API payloads:** system monospace only inside an actual code block.

Type scale:

| Token | Size | Line height | Use |
| --- | ---: | ---: | --- |
| `--text-xs` | 11px | 16px | Metadata, timestamps, table secondary text |
| `--text-sm` | 13px | 19px | Controls, body supporting text |
| `--text-md` | 15px | 22px | Default readable body copy |
| `--text-lg` | 18px | 25px | Card headings, important values |
| `--text-xl` | 24px | 29px | Page title |
| `--text-2xl` | 30px | 35px | Workspace or project hero title |

Rules:

- Page titles are left aligned and fit on one or two lines.
- Use sentence case for labels and headings. Avoid tiny, widely tracked uppercase
  eyebrows as a primary information carrier.
- Use tabular numerals for KPI values, percentages, and dates where alignment helps.
- Body copy should target 45-75 characters per line on wide layouts.

### Spacing

Use a 4px base scale:

`--space-1: 4px`, `--space-2: 8px`, `--space-3: 12px`,
`--space-4: 16px`, `--space-5: 20px`, `--space-6: 24px`,
`--space-8: 32px`, `--space-10: 40px`, `--space-12: 48px`,
`--space-16: 64px`.

Use 24-32px page gutters on desktop, 20px on tablet, and 14-16px on mobile.
The gap between sections should be larger than the gap inside a card. Prefer
padding and surface changes over divider lines.

The compact dashboard structure remains intact: the fixed 248px desktop sidebar
becomes an off-canvas drawer below the tablet breakpoint, page content keeps a
minimum width of 320px, and dense tables use contained horizontal scrolling
instead of expanding the page viewport.

### Shape, borders, and elevation

- Small controls: 8px radius.
- Cards and panels: 12px radius.
- Large project surfaces and dialogs: 14px radius.
- Avatars and status dots: fully round where appropriate.
- Default border: 1px solid `--color-border`, used to define a surface boundary.
- Resting surfaces have no shadow. Floating menus, dialogs, and drawers may use
  `0 16px 40px rgba(0, 0, 0, 0.28)`.
- Do not combine a strong border, strong shadow, and gradient on the same surface.

### Interaction and state tokens

- Primary actions use `--color-primary`, shift to `--color-primary-hover` on hover,
  and use `--color-primary-pressed` while active.
- Focus indicators use a visible 2px `--color-focus` outline with an offset; focus
  must not depend on hover or color changes alone.
- Selection uses `--color-selection` as a calm surface tint behind readable text.
- Disabled controls use `--color-ink-disabled`, reduced emphasis, and a clear
  non-interactive cursor without becoming unreadable.
- Success and completed states use `--color-success`/`--color-complete`; warnings
  and blockers use `--color-warning`/`--color-blocked`; destructive errors use
  `--color-error`/`--color-danger`.
- Every status includes a text label or icon in addition to its color treatment.

## Application shell

### Sidebar navigation

The sidebar is the persistent workspace anchor.

- Desktop: fixed left rail, 248px wide, full viewport height.
- Tablet: collapses to an off-canvas drawer opened by the menu button.
- Mobile: off-canvas drawer with a visible close button and scrim.
- Brand mark and `delegatorai` wordmark sit at the top.
- Workspace switcher appears below the brand and identifies CampusConnect.
- Navigation is grouped into **Workspace** and **Intelligence**.
- Active navigation uses a subtle surface step, an emerald leading accent, and
  readable text; it must not depend on color alone.
- The AI Coordinator may use a small `LIVE` label only when the coordinator is
  enabled. The label must have text, not just a colored dot.
- Settings and the current user stay at the bottom.

Navigation labels remain the current product views:
Overview, Projects, My Tasks, Team Members, AI Coordinator, Activity Log, and
Settings. Do not add routes or backend-backed views without a product requirement.

### Top bar

- Sticky within the main content column.
- Contains breadcrumb context, connection state, search, notifications, and user
  controls.
- The connection indicator clearly distinguishes **Backend connected** from
  **Demo mode**.
- Menus anchor to their trigger, close with Escape, and do not cover the trigger
  label when opened.
- Search should have a visible input on wide screens and remain reachable from a
  labeled icon control on small screens.

### Page header

Each view starts with:

1. current workspace context;
2. a concise page title;
3. one supporting sentence;
4. only the actions relevant to that view.

Keep the current refresh and new-task actions, but avoid adding a button to every
heading. The primary action is emerald and singular; secondary actions are neutral.

## Core components

### KPI cards

KPI cards summarize decisions, not decoration. The Overview set is:
Total tasks, In progress, Blocked tasks, and Completed.

- Four columns on wide desktop; two columns on tablet; one column on narrow mobile.
- Show a label, a large value, a short explanation, and optional trend/context.
- The value is the strongest element. Icon treatment is secondary.
- Cards must still communicate meaning when color is unavailable.
- Do not place an unrelated icon above every feature card.

### Task cards and tables

Use the table for scanning many tasks and a task card for narrow screens or focused
detail.

Required task fields where available:

- task title and stable task ID;
- assignee and avatar;
- status;
- priority;
- due date;
- progress;
- blocker or latest update.

Desktop table rules:

- Keep columns aligned and use a minimum 44px row height.
- Make the task title the primary click target and provide a clear hover/focus
  state for the entire row.
- Keep overflow actions in a labeled button with a minimum 44x44px hit area.
- Do not hide task status or due date on the first scan.

Mobile card rules:

- Stack title, status, assignee, due date, and progress in that order.
- Move secondary description and activity into an expandable detail view.
- Never require horizontal scrolling to discover status or ownership.

### Task status

The canonical display names and tokens are:

| Status | Token | Meaning |
| --- | --- | --- |
| Pending | `--color-pending` | Accepted work that has not started |
| In Progress | `--color-progress` | Work currently being executed |
| Blocked | `--color-blocked` | Work cannot continue without attention |
| Completed | `--color-complete` | Work is finished |

Status pills include text and an optional icon. Never communicate status through
color alone. Backend values may remain `PENDING`, `IN_PROGRESS`, `BLOCKED`, and
`COMPLETED` internally; the UI uses the display names above.

### Progress indicators

- Use a track with a clear filled portion and an accessible text percentage.
- Clamp display values to 0-100%.
- Use the progress color for work state, not a rainbow scale.
- A zero-progress task still needs a visible track and `0%` text.
- If progress is unavailable, show `Not reported` rather than implying zero.

### Avatars and people

- Initials are the reliable fallback for the current demo data.
- Use 34px avatars in people lists, 27px in tables, and 23px for compact stacks.
- Keep initials to two characters and provide the person's full name as accessible
  text or a tooltip when the name is not adjacent.
- Avatar color is decorative and must not encode role, permission, or task status.
- Do not introduce remote profile images unless the backend provides them.

### Forms and filters

- Every input has a visible label. Placeholder text is not a label.
- Task creation keeps the existing fields: title, description, assignee, priority,
  and due date.
- Required fields are identified before submission and errors appear beside the
  relevant field.
- Preserve entered values after a failed request.
- Filters use explicit labels and show the active result count when useful.
- Search and status filters must have a clear reset path.
- Submit buttons expose a pending state and cannot be double-submitted.

### Activity feeds

Activity entries show what happened, who or what caused it, and when.

- Human activity and AI activity use distinct icons and text labels.
- Blocker events use amber; completion events use teal.
- Timestamp text is secondary but readable.
- New entries appear at the top without disrupting keyboard focus.
- Empty activity state explains that updates will appear after task activity.

### AI conversation and coordinator elements

The AI Coordinator is an accountable assistant, not a fictional chat backend.

- Use a distinct AI icon and the label “AI coordinator”.
- Explain the reason for every suggested follow-up or blocker flag.
- Separate AI-generated suggestions from confirmed actions.
- Show action state: ready, sending, sent, failed, or paused.
- Preserve the existing “preview only” messaging for Google Chat where no real
  messaging capability exists.
- Conversation elements use readable message width, timestamps, and a clear
  composer state. Do not imply an answer was sent when the request failed.
- Pausing the coordinator is reversible and states what will stop.

## Responsive behavior

### Desktop: 1280px and above

- Persistent 248px sidebar.
- Main content max width around 1580px with 32px horizontal padding.
- Use multi-column KPI, overview, team, and activity compositions.
- Tables remain the primary task scanning surface.

### Tablet: 768px-1279px

- Sidebar becomes an off-canvas drawer.
- Main content uses 20-24px padding.
- KPI cards use two columns.
- Two-column panels collapse when content becomes cramped.
- Keep page title actions visible; group them only when necessary.

### Mobile: 320px-767px

- Off-canvas sidebar opens from a labeled menu button.
- Main content uses 14-16px padding.
- Stack page title actions or make the primary action full width.
- KPI cards, panels, forms, and people rows use one column.
- Replace wide tables with task cards; do not add horizontal scrolling for primary
  task information.
- Keep tap targets at least 44x44px.
- Preserve readable line height and never reduce body text below 14px.
- Dialogs become near-full-screen sheets with a clear close action.

## Accessibility and interaction

- Use semantic `button`, `a`, `nav`, `main`, `aside`, `header`, `form`, `table`,
  and heading elements.
- Maintain one logical heading hierarchy per view.
- Every icon-only control has an accessible name.
- Visible focus uses `--color-focus` with at least a 2px outline and 2px offset.
- Do not remove focus outlines for mouse users unless an equivalent visible
  `:focus-visible` treatment remains.
- Normal text must meet WCAG AA contrast: 4.5:1 minimum; large text 3:1.
- Status, progress, connection, and validation states require text or an announced
  label in addition to color.
- Keyboard order follows visual order. Menus, drawers, and dialogs support Escape.
- Dialogs trap focus while open and return focus to their trigger when closed.
- Respect `prefers-reduced-motion: reduce`; remove travel and nonessential motion,
  but keep state changes understandable.
- Do not use emoji as functional status or navigation icons.

## State design

Every data-bearing surface must define these states:

### Loading

Use a compact, content-shaped placeholder or progress message. Do not show a
completed-looking empty table while data is loading. Keep the existing demo data
available as the documented fallback only when the API request fails, not as a
silent replacement for a successful empty response.

### Empty

Explain what is empty and provide the next useful action. Examples:

- “No tasks match these filters.” with a clear filter reset.
- “No tasks yet.” with the existing New task action.
- “No activity yet.” with a short explanation.

### Error

Explain what failed in plain language, preserve local form state, and offer a
retry. Keep the connection indicator honest. Do not show success-shaped UI after
an API failure.

### Success

Confirm the completed action with a short toast or inline message, update the
relevant list, and preserve the user's place and focus.

## Implementation rules for this repository

- Keep UI changes in `src/App.jsx` and `src/styles.css` unless a reusable
  component extraction is justified.
- Reuse `lucide-react`, which is already installed. Do not add an icon dependency
  for ordinary UI controls.
- Keep API calls in `src/api.js`; do not move fetch logic into visual components.
- Preserve `initialTasks`, `initialActivity`, `people`, and the existing
  demo-mode fallback behavior unless a future task explicitly changes the data
  model.
- Normalize backend task statuses through the existing adapter rather than
  changing display components to understand every backend spelling.
- Do not invent backend endpoints, server capabilities, Google Chat delivery, or
  AI responses. UI copy must clearly distinguish preview/demo behavior.
- Prefer CSS custom properties and existing responsive breakpoints over inline
  style proliferation.
- Test all seven existing views at desktop, tablet, and mobile widths after a
  visual change.

## Review checklist

Before accepting a future redesign:

- The page still supports Overview, Projects, My Tasks, Team Members, AI
  Coordinator, Activity Log, and Settings.
- Mock data renders when the backend is unavailable.
- Backend-connected and demo states are visually distinct and truthful.
- Status and progress remain understandable without color.
- Keyboard focus, Escape handling, labels, and contrast have been checked.
- Loading, empty, error, and success states are implemented for changed flows.
- No new package was added without a concrete requirement.
- `npm run build` passes.
- The result feels like a focused college-team coordination workspace, not a
  generic dashboard template.
