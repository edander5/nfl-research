# Collapsible navigation

The shared App sidebar supports expanded navigation or an 80px desktop icon rail.
The visible collapse/expand button persists preference in localStorage under
`nfl-research-sidebar-collapsed`; blocked storage falls back to in-memory operation.
Icon links retain accessible names and native title hints. The compact theme icon
is the existing native Theme selector, with its current preference in the title;
keyboard users can select Light, Dark or System as before. No theme logic changed.

At widths of 760px or less, Menu reveals navigation in document flow. It starts
closed, so it does not cover content. Escape or a navigation link closes it and
returns focus to Menu. Route or viewport changes also close the mobile disclosure.
The desktop collapse preference remains independent. Native buttons/selects/links
provide keyboard behavior, with explicit focus outlines and aria-expanded/control
relationships. Shared layout covers Schedule, Rankings, Game Preview and team
research; page routes, requests and calculations are unchanged.

Validation: focused sidebar/theme tests, full frontend suite, TypeScript and Vite
production build. Browser/device visual acceptance remains manual; DOM tests check
responsive state and CSS rules, not actual rendered media-query layout.

From the repository root in WSL:

```bash
npm --prefix frontend test -- src/test/sidebar.test.tsx src/test/theme.test.tsx
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

To preview locally, use `npm --prefix frontend run dev -- --host 127.0.0.1`.
Check each page, collapse/remount persistence, keyboard focus and theme selection,
then resize below 760px and confirm Menu/Escape/link behavior. No Docker rebuild
or deployment was performed for this task.
