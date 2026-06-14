# Mobile Image Loading Optimization Design

## Goal

Improve mobile image loading speed for the Werewolf web app, especially when users open the site by URL on phones. The first implementation pass focuses on the highest-impact, lowest-risk fixes:

- Let static image assets be cached by browsers.
- Replace oversized PNG assets used on mobile with smaller WebP assets.
- Convert the slow Garfield avatar PNG path to WebP.
- Keep the current visual design and gameplay flow unchanged.

## Current Problems

The FastAPI middleware currently applies `Cache-Control: no-store` to every response, including files served from `/static`. That prevents browsers from reusing images across refreshes or repeat visits.

Several image assets are much larger than their displayed size requires:

- `game-mobile-character-background.png` is about 6.2 MB and is used as the game background.
- `garfield.png` is about 271 KB while the other avatar files are much smaller WebP files.
- The lobby loads a grid of avatar images, so even moderately sized avatar files can feel slow on mobile when they cannot be cached.

## Proposed Approach

### Static Asset Caching

Keep no-cache behavior for HTML and API responses, but allow `/static` assets to use browser caching. Static assets should receive a long-lived cache header because the project can change asset URLs when an image is replaced or renamed.

Expected behavior:

- `/api/*` remains no-store.
- `/` HTML remains no-store.
- `/static/*` receives a cacheable header.

### Image Asset Optimization

Create smaller WebP versions for the slow images and update references:

- Add `game-mobile-character-background.webp`.
- Add `avatars/garfield.webp`.
- Update CSS to use the WebP game background.
- Update JavaScript avatar mapping so Garfield uses WebP.

The existing PNG files can remain in the repo for compatibility unless later cleanup is requested. This keeps the first change safer and avoids breaking tests or packaging unexpectedly.

### Loading Behavior

Keep the current UI structure. The first pass does not add skeleton loaders or lazy rendering changes unless tests reveal they are necessary. The avatar grid already uses `loading="lazy"`, and the largest immediate win is reducing transfer size plus allowing cache reuse.

## Testing

Add or update focused tests to verify:

- Static assets do not receive `no-store`.
- HTML/API responses still receive no-cache behavior.
- CSS references the optimized game background WebP.
- Garfield avatar rendering uses `garfield.webp`.
- Required optimized assets are packaged.

Run the relevant frontend/static tests after implementation, then the broader test suite if the focused tests pass.

## Out Of Scope

- CDN setup.
- 1Panel or Nginx configuration changes.
- Visual redesign of the lobby or game screen.
- New progressive image placeholders.
- Removing old PNG files.
