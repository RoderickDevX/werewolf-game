# HTTP Polling Multiplayer Implementation Plan

> **For AI agents:** Use test-driven development for each task. Keep steps checked off as they are completed.

**Goal:** Make rooms playable from multiple browsers or phones by adding local player identity persistence and HTTP polling synchronization.

**Architecture:** Keep the existing FastAPI in-memory room model. Add frontend session persistence, viewer-specific room fetching, waiting-room polling, game-state polling, and local-player-only action controls. Add focused source tests that protect the multiplayer synchronization behavior.

**Tech stack:** FastAPI, static HTML/CSS/JavaScript, pytest.

---

## Files

- Modify `src/werewolf_langgraph/static/app.js`: local session storage, URL update, polling loops, viewer ownership checks, local-only "you" label.
- Modify `src/werewolf_langgraph/static/index.html`: add a waiting/action status element if existing panels do not provide one.
- Modify `tests/test_frontend_start_feedback.py`: source-level tests for polling, storage, and local player controls.
- Optionally modify `tests/test_multiplayer_lobby.py`: backend edge tests if frontend needs additional API behavior.

## Task 1: Persist And Restore Player Session

- [ ] Step 1: Add failing tests in `tests/test_frontend_start_feedback.py` that expect `saveLocalSession`, `restoreLocalSession`, `clearLocalSession`, `localStorage`, and `URLSearchParams`.
- [ ] Step 2: Run the focused tests and confirm they fail because these functions do not exist.
- [ ] Step 3: Implement session helpers in `app.js` and call `saveLocalSession` after successful create/join/start responses.
- [ ] Step 4: Run the focused tests and confirm they pass.

## Task 2: Poll Waiting Room And Game Room

- [ ] Step 1: Add failing tests that expect `startRoomPolling`, `stopRoomPolling`, `fetchRoomState`, and `setInterval`.
- [ ] Step 2: Run the focused tests and confirm they fail.
- [ ] Step 3: Implement polling with a single timer and viewer-specific `GET /api/rooms/{room_id}?player_id=...`.
- [ ] Step 4: Run the focused tests and confirm they pass.

## Task 3: Fix Local Player View

- [ ] Step 1: Add failing tests that ensure only `player.id === room.human_id` gets the "you" suffix and that action controls are gated by `isLocalPendingActor`.
- [ ] Step 2: Run the focused tests and confirm they fail.
- [ ] Step 3: Implement `isLocalPendingActor`, `pendingActorLabel`, waiting copy, and local-only player labels.
- [ ] Step 4: Run the focused tests and confirm they pass.

## Task 4: Restore From URL Or Local Storage On Load

- [ ] Step 1: Add failing tests that expect page load to call a restore function before/alongside lobby initialization.
- [ ] Step 2: Run the focused tests and confirm they fail.
- [ ] Step 3: Implement startup restore behavior and graceful fallback to lobby.
- [ ] Step 4: Run the focused tests and confirm they pass.

## Task 5: Regression Verification

- [ ] Step 1: Run `pytest tests/test_frontend_start_feedback.py tests/test_multiplayer_lobby.py tests/test_site_routing.py -q`.
- [ ] Step 2: Run `pytest -q`.
- [ ] Step 3: Inspect `git diff --stat` and summarize changed files.
