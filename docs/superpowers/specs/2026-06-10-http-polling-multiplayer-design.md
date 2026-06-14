# HTTP Polling Multiplayer Design

## Goal

Make multiplayer rooms playable from multiple browsers or phones connected to the same server. Each joined player keeps their own seat and receives room/game updates through periodic HTTP polling.

## Scope

This design covers the minimum real multiplayer loop:

- A host creates a waiting room.
- Other players join the same room from another browser or phone.
- Waiting room membership and ready state refresh automatically.
- When the host starts the game, every joined player automatically enters the game view.
- During the game, every player refreshes the room state automatically.
- Only the current required human player can submit an action.
- A browser refresh restores the player's own room and seat.

The design does not add WebSocket, accounts, a database, cross-process shared storage, matchmaking, spectator permissions, or persistent history.

## Architecture

The backend keeps the existing in-memory `ROOMS` store and `GET /api/rooms/{room_id}?player_id=...` response shape. The frontend becomes responsible for maintaining the local viewer identity and polling the room state.

The frontend stores this object in `localStorage`:

```json
{"roomId":"abcd1234","playerId":"2"}
```

When the page loads, it checks this value. If present, it requests the room with the saved `player_id`. If the room exists, the page restores either the waiting room or the game view. If it no longer exists, local storage is cleared and the lobby is shown.

## Polling Rules

Waiting room:

- Poll every 1500 ms.
- Request `GET /api/rooms/{room_id}?player_id={localPlayerId}`.
- Keep showing the waiting room while `status` is `waiting`.
- Switch to the game view when `status` becomes `playing`.

Game room:

- Poll every 1500 ms.
- Skip applying stale responses by using the latest response only.
- Keep the current player's role-revealed flag local to the browser.
- Do not poll while a local submit or stage-advance request is in flight.

Lobby:

- The lobby room list can refresh on load and through the existing refresh button.
- It may use a slower periodic refresh later, but that is not required for the playable multiplayer loop.

## Player View

The current viewer is the stored `player_id`. The UI labels only that player as "you". Other human players are shown as human seats, but their hidden roles remain hidden unless existing reveal rules allow them.

When the backend returns `waiting_for`, the frontend determines whether the current viewer owns the pending action:

- `speech`: `waiting_for.speaker_id`
- `vote`: `waiting_for.voter_id`
- night role actions: the living human player whose role matches the action kind

If the current viewer is not the pending actor, action controls stay hidden and the panel shows a waiting message with the actor seat/name when available.

## URLs

After room creation or join, the frontend updates the browser URL to:

```text
/?room=abcd1234
```

If a new visitor opens a URL with a `room` query value but no saved membership for that room, the page shows the lobby/join flow and can join that room from the room list.

## Error Handling

If polling receives 404, clear the saved session and return to the lobby. If polling fails because of a transient network problem, show a compact status message and keep the last known state visible.

If an action submit receives 403 because another player owns the action, refresh the room state and show a waiting message instead of leaving stale controls visible.

## Testing

Backend tests should continue to verify player-specific serialization and action ownership.

Frontend source tests should verify:

- local room identity is stored after create/join;
- saved room identity is restored on page load;
- waiting/game polling functions exist and call the viewer-specific room endpoint;
- polling switches from waiting room to game view after the host starts;
- only the local player is labeled as "you";
- action controls are shown only when the local player owns the pending action.
