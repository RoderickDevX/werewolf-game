# Desktop Game Background Design

## Goal

Use the provided cartoon night village image as the desktop in-game background for the Werewolf game. The change should improve the computer layout's atmosphere without affecting the mobile game background, lobby, waiting room, opening poster, or game rules.

## Scope

This design covers only the active game screen, `#gameScreen`, on desktop and tablet-width layouts above the existing mobile breakpoint.

In scope:

- Add a desktop-only in-game background asset derived from the provided PNG.
- Switch desktop `.game-screen::before` to use the new horizontal village background.
- Keep the existing mobile in-game background on small screens.
- Refresh the stylesheet cache version in `index.html`.
- Add or update tests that protect the desktop/mobile asset split and package inclusion.

Out of scope:

- Redesigning the full fantasy wood-and-parchment UI from the reference mockup.
- Changing player cards, panels, buttons, typography, or layout structure.
- Replacing lobby or opening poster art.
- Changing game logic, multiplayer behavior, or backend APIs.
- Deploying changes to the server as part of the design step.

## Visual Direction

The desktop game screen should show the provided horizontal night village illustration behind the existing three-column interface. The image should read as a full-screen scene, not as a narrow centered strip.

Desktop background rules:

- Use a new asset named `game-desktop-village-background.webp`.
- Set the desktop background image to cover the viewport.
- Position it around the visual center so the moon, village street, and buildings remain recognizable.
- Use a dark overlay that preserves text readability while allowing the village image to remain visible.

Mobile background rules:

- Preserve the existing `game-mobile-character-background.webp`.
- Preserve the existing mobile sizing behavior, including `background-size: auto 100lvh`.
- Do not force the horizontal village image onto mobile.

## Asset Handling

The provided source image is a 1024 by 582 PNG. It should be converted into a WebP file for the app:

```text
src/werewolf_langgraph/static/assets/game-desktop-village-background.webp
```

The source PNG does not need to be committed. The WebP should be small enough for web delivery while retaining the illustrated details needed behind translucent panels.

## CSS Changes

Update `src/werewolf_langgraph/static/styles.css`:

- Desktop `.game-screen::before` should reference `game-desktop-village-background.webp`.
- Desktop should use `background-size: cover`.
- Desktop should use a stable center-oriented `background-position`.
- The mobile `@media (max-width: 680px)` block should override the image back to `game-mobile-character-background.webp`.

Update `src/werewolf_langgraph/static/index.html`:

- Change the stylesheet version query string to a new value, such as `20260701-desktop-village-background`.

## Tests

Update tests to cover the intended behavior:

- Static packaging includes `game-desktop-village-background.webp`.
- Desktop CSS references `game-desktop-village-background.webp`.
- Desktop CSS uses `background-size: cover`.
- Mobile CSS still references `game-mobile-character-background.webp`.
- Mobile CSS still uses `background-size: auto 100lvh`.
- The game HTML references the refreshed stylesheet version.

Run the full test suite after implementation.

## Success Criteria

On a desktop viewport around 1440x900 or wider:

- The in-game screen uses the provided night village background.
- The background fills the screen instead of appearing as a narrow strip.
- The active game UI remains readable.
- The existing mobile in-game background is unchanged.
- The package includes the new WebP asset.
- Existing tests pass.
