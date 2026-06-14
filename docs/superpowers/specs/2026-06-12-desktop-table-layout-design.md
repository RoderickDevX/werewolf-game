# Desktop Table Layout Design

## Goal

Adjust the Werewolf game page for desktop play so it feels like a focused game table instead of a stretched mobile/landing-page layout. The desktop experience should keep players, current action, logs, and controls visible at the same time.

## Primary Direction

Use a three-column desktop table layout:

- Left sidebar: fixed 9-player seat list.
- Center: current phase and active action area.
- Right sidebar: public events, speech/vote feed, and synchronization/waiting status.
- Top bar: room, round, viewer, and phase context.

This is a browser-based desktop layout change. It does not add an Electron/Tauri shell or a native `.exe` package.

## Problems To Fix

The current desktop page feels strange because:

- The 9-player grid stretches across the page and becomes hard to scan.
- Phase panels use hero-scale typography, which feels like a landing page rather than a playable board.
- Public logs and action controls sit below the table, forcing the player to scroll or visually hunt.
- Speech, vote, and night action controls are spread across different phase panels.
- Several visible Chinese strings are mojibake and must be repaired during the layout pass.

## Desktop Layout

### Top Bar

The top bar stays compact and always visible at the top of the game screen.

It shows:

- Game name.
- Room id.
- Current phase/stage.
- Day/night counters.
- Viewer seat.
- Viewer role state, such as "identity hidden", "identity confirmed", or game-over reveal.
- Sync/waiting status.

### Left Player Sidebar

The left sidebar is the stable table roster. It shows all 9 seats as compact rows:

- Avatar.
- Seat number.
- Name.
- Alive/dead state.
- Human/AI marker.
- Current actor highlight.
- Local viewer marker only on the current viewer's seat.
- Role label when visible under existing reveal rules.

This replaces the desktop 9-column player grid. The sidebar should fit within a normal 1080p desktop viewport without requiring page scrolling.

### Center Play Area

The center area is the main attention zone.

It shows:

- Current stage title in compact desktop scale.
- The current instruction or waiting message.
- Role/action context for the current phase.
- Candidate choices when the local player owns the pending action.
- A clear waiting state when another player owns the pending action.

The center should not use oversized hero text. It should feel like a game board or tabletop panel.

### Fixed Action Area

Action controls should live in one predictable area near the bottom of the center column:

- Confirm role.
- Advance stage for the host/driver.
- Speech textarea and submit button.
- Vote selector and submit button.
- Night action candidate buttons.
- Witch save/poison steps.
- Hunter shot choices.

Controls should appear only when actionable for the local viewer. Otherwise the area shows a short waiting message.

### Right Information Sidebar

The right sidebar is for information, not primary action.

It contains:

- Public event log.
- Speech feed.
- Vote feed.
- Latest night/day result summary.
- Multiplayer sync or waiting status.

The right sidebar should be scrollable internally so the whole page does not become a long vertical document.

## Lobby And Waiting Room

The lobby and waiting room should also be tuned for desktop, but the first priority is the in-game board.

Desktop lobby:

- Keep room list and create-room form side by side.
- Reduce hero prominence.
- Fix Chinese text.

Desktop waiting room:

- Use a 3x3 seat grid or compact roster.
- Show room id and invite state clearly.
- Keep ready/start/back controls in a fixed action row.

## Responsive Behavior

Desktop is the primary target for this pass.

Recommended breakpoints:

- `>= 1180px`: three-column table layout.
- `800px - 1179px`: two-column layout, with right sidebar below or collapsible.
- `< 800px`: keep a stacked mobile layout similar to the current responsive approach.

The mobile layout should remain usable, but pixel-perfect mobile redesign is out of scope for this pass.

## Visual Style

Keep the existing dark cartoon game mood, but make it quieter and more utilitarian for desktop play:

- 8px panel radius.
- Dense but readable controls.
- Smaller headings inside panels.
- Stable dimensions for seats and action controls.
- No large landing-page hero typography inside the active game.
- Use existing avatar assets.
- Avoid adding decorative gradient blobs.

## Text And Encoding

Visible Chinese strings in `index.html`, `app.js`, and related UI tests should be repaired where touched by this desktop layout pass.

The goal is not to rewrite every prompt or backend string in the whole project, but the desktop game surface should not show mojibake in normal play.

## Non-Goals

This pass will not:

- Package the game as a native desktop app.
- Add a database.
- Add WebSocket.
- Change Werewolf rules.
- Redesign AI prompts.
- Replace existing character images.
- Rebuild the whole frontend framework.

## Success Criteria

On a desktop viewport around 1440x900:

- All 9 players are visible without scrolling.
- Current phase and next required action are immediately visible.
- Public events or discussion history are visible at the same time as the action controls.
- Only the local viewer's seat is marked as "you".
- Waiting for another player is clear.
- The main game screen has no mojibake in normal visible UI.
- Existing multiplayer polling behavior remains intact.
- Existing tests pass, with new tests protecting desktop layout structure.
