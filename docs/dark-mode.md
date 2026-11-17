# Dark mode

Owner-approved frontend-only task: add Light / Dark / System to the workspace
navigation, default to system preference on first visit, save the choice across
reloads and theme existing pages without changing data, calculations or behavior.
No new library, API, backend, database, ingestion or deployment changes.

## Implementation

The labeled native select in `src/theme/ThemeToggle.tsx` is available throughout
the app, including mobile navigation. It stores only `light`, `dark` or `system`
under `nfl-research-theme` in browser localStorage. Invalid/missing values default
to System. System follows `prefers-color-scheme` changes; explicit choices override
it. Storage events synchronize preferences between tabs. Media/storage listeners
are cleaned up on unmount. Blocked storage leaves the session control usable,
although the browser cannot persist the choice. Without matchMedia, System uses
light; explicit dark still works.

`public/theme.js` is a small blocking script in the document head. It applies the
saved/system preference to the root `.dark` class and native `color-scheme` before
styles and React paint. Vite copies this public asset to the built site. React
handles subsequent changes. The script must remain in the head without async or
defer so it can select the first-frame theme. As with other app assets, a failed
or blocked script load prevents its first-paint behavior.

The existing shadcn card component now consumes CSS variable tokens through
Tailwind v4 `@theme inline`; the `.dark` variant follows the shadcn convention.
Shared dark variables and scoped custom-style rules cover the schedule, preview,
rankings, team research, betting references, game logs, tables, cards, buttons,
borders, selects, loading states, errors, warnings and keyboard focus. Existing
light colors/layout are retained, with navigation wrapping only as needed to fit
the added control. The sidebar retains its existing dark appearance in either
mode. Rank green/red/gray tokens adapt to each palette, with unchanged rank
boundaries and missing-data handling. No theme filter or chart/data transformation
is used.

Local source references: `frontend/components.json`,
`frontend/src/components/ui/card.tsx`, `frontend/src/styles.css`,
`frontend/src/App.tsx` and the existing page components. No new external source
or dependency was needed.

## Changed files

- `frontend/public/theme.js`, `frontend/index.html`: pre-paint theme initialization.
- `frontend/src/theme/ThemeToggle.tsx`, `frontend/src/App.tsx`: persistent navigation
  control and system/cross-tab updates.
- `frontend/src/styles.css`: Tailwind/shadcn variables and dark page styling.
- `frontend/src/test/theme.test.tsx`: synthetic theme and contrast tests.
- `AGENTS.md`, `README.md`, `docs/decisions.md`, this guide: approved scope, behavior
  and validation.

## Validation

- `npm --prefix frontend test`: **142 passed across eight files**, including all
  existing schedule, preview, rankings, market and game-log tests. New tests cover
  initial system light/dark, persisted choices/remount/startup, explicit dark over
  system light, OS changes, storage failures/invalid values, storage events,
  listener cleanup, missing matchMedia and main-navigation accessibility.
- First-paint tests execute the actual public script and verify its head ordering.
  The built `dist/index.html` retains the blocking script before bundled styles,
  and `dist/theme.js` is present.
- Rank green/red/gray text tokens pass a 4.5:1 contrast calculation against both
  card and muted surfaces in both themes. The text still conveys rank numbers.
- `npm --prefix frontend run build`: TypeScript and Vite production build passed.
- `git diff --check`: passed.

No browser executable/automation is available in this environment. Unit tests do
not establish actual rendered layout or first-paint timing. Desktop/mobile visual
acceptance, native select rendering and slow-reload flash checks remain local
browser checks. No real data or backend was modified. No commit, merge, push or
deployment was performed.

## Verify locally in WSL

With existing dependencies installed and the existing development API running:

```bash
cd /home/edander5/nfl-research-planning
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run dev
```

Open `http://127.0.0.1:5173`; use the existing server if that port is occupied.

1. Clear only `nfl-research-theme` in browser storage, reload and confirm System
   follows the OS/browser color preference. Change OS preference while viewing.
2. Choose Light and Dark, reload each time and confirm persistence and no incorrect
   first-frame theme (also check a throttled reload). Explicit choices should
   ignore later OS changes. Switch back to System and verify it follows again.
3. Visit League Schedule, Game Preview, rankings and team research in both themes.
   Inspect cards/tables, green/red rank text, market cells and expanded grading,
   logs/pagination, warnings, unavailable values, loading/error states and dropdowns.
4. Check keyboard focus and theme selection at desktop, 390px and 320px widths.
   Verify the navigation wraps without obscuring links or the control.
5. Open a second tab and change the preference; confirm synchronization.

Next proposed task, for owner approval: local browser visual acceptance of both
palettes and first-paint behavior against the existing development app.
