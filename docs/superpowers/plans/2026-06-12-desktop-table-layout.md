# Desktop Table Layout Implementation Plan

> **For AI agents:** Use test-driven development for each task. Keep steps checked off as they are completed.

**Goal:** Convert the active game screen into a desktop-first table layout with fixed player roster, central action area, and right-side logs.

**Architecture:** Keep the current static FastAPI frontend and existing game APIs. Reorganize the game screen DOM with semantic desktop containers, update CSS grid areas for desktop/tablet/mobile breakpoints, and keep existing JavaScript render functions working against the same element ids.

**Tech stack:** Static HTML/CSS/JavaScript, FastAPI static serving, pytest source tests.

---

## Files

- Modify `src/werewolf_langgraph/static/index.html`: add desktop table shell wrappers and repair normal visible Chinese text in the game surface.
- Modify `src/werewolf_langgraph/static/styles.css`: add desktop three-column layout, compact player roster styles, center action stage, and right-side log/feed panel.
- Modify `src/werewolf_langgraph/static/app.js`: update user-visible labels touched by desktop layout and add any small hooks needed for the right sidebar/status.
- Modify `tests/test_frontend_start_feedback.py`: add source tests for desktop table structure and CSS behavior.
- Modify `tests/test_site_routing.py`: update script version assertion if cache-busting changes.

## Task 1: Protect Desktop Table Structure

- [ ] Step 1: Add failing source tests that expect `desktopTableShell`, `desktopPlayerRail`, `desktopActionColumn`, and `desktopInfoRail` in `index.html`.
- [ ] Step 2: Add failing CSS tests that expect `.desktop-table-shell`, grid areas for `players`, `stage`, and `log`, and a desktop media query.
- [ ] Step 3: Run `pytest tests/test_frontend_start_feedback.py -q` and confirm the new tests fail.
- [ ] Step 4: Add the HTML wrappers and CSS grid areas.
- [ ] Step 5: Run the focused tests and confirm they pass.

## Task 2: Make Player Roster Desktop-Readable

- [ ] Step 1: Add failing tests that ensure `.players` is a one-column desktop roster inside the desktop shell and switches back responsively.
- [ ] Step 2: Run the focused tests and confirm failure.
- [ ] Step 3: Update CSS so desktop players render as compact seat rows with stable avatar/name/status dimensions.
- [ ] Step 4: Run focused tests and confirm pass.

## Task 3: Compact The Central Action Area

- [ ] Step 1: Add failing tests for compact phase headings and fixed action controls in the center column.
- [ ] Step 2: Run focused tests and confirm failure.
- [ ] Step 3: Update `.phase-stage`, `.phase-panel`, `.choice-box`, `.human-speech`, and `.vote-box` desktop styles.
- [ ] Step 4: Run focused tests and confirm pass.

## Task 4: Repair Visible Desktop Text

- [ ] Step 1: Add/update tests that expect normal Chinese title, lobby labels, waiting labels, and game surface labels in `index.html`.
- [ ] Step 2: Run focused tests and confirm current mojibake fails.
- [ ] Step 3: Replace the visible `index.html` mojibake strings with normal Chinese text.
- [ ] Step 4: Run focused tests and confirm pass.

## Task 5: Regression Verification

- [ ] Step 1: Run `pytest tests/test_frontend_start_feedback.py tests/test_site_routing.py -q`.
- [ ] Step 2: Run `pytest -q`.
- [ ] Step 3: Inspect `git diff --stat`.
