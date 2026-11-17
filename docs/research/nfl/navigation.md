# Navigation and shared layout

**Observed.** At the homepage, open the navigation drawer and expand NFL. REA found desktop and drawer instances of the NFL label at 1440 px. Clicking the drawer-scoped label expanded seven links in this order.

| Label | Published href |
|---|---|
| Standings | /nfl/standings |
| Schedule | /nfl/schedule |
| Lineups | /nfl/lineups |
| Moneyline / Spread | /nfl/moneyline |
| Game Total | /nfl/game-total |
| Team Total | /nfl/team-total |
| Player Props | /nfl/player-props |

Injury Impact was marked Coming Soon. Each link target was then opened in a fresh REA browser scenario. Schedule and standings team links point to team-specific moneyline screens, schedule total links to a team-specific Game Total screen, and lineup players to specific prop research pages. The earlier props investigation verified navigation from a prop row to detail with pick and event context.

The sampled guest header uses a menu button and shared team/player search. A floating My Picks control is present. The dark appearance rendered even with light browser preference. A theme switch and theme persistence were unverified.

Controls vary by task. Standings groups tables within the current season. Schedule has week buttons. Lineups surfaced projected starters for the upcoming slate. The three team market pages start with a week and matchup strip and add a separate upcoming-opponent strip for the selected team. Props exposes a Week & matchups control and its own player search. Season windows for historical charts and season controls on individual matchup panels serve different scopes.

See the [ledger](evidence/README.md) for URLs and capture dimensions. Browser history, search destination selection, preference persistence, intermediate widths and sustained loading/error states remain open.

At 390 × 844, Game Total replaced the desktop matchup grid with a single matchup dropdown. The line stepper, side buttons and books wrapped across rows, the upcoming-opponent strip showed only its first few items in the viewport, and the first-half label was clipped beside Save and Track. The floating My Picks control overlapped the lower content area. Use these as responsive acceptance checks. [Mobile viewport](screenshots/game-total-mobile.png).
