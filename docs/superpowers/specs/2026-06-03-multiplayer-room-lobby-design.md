# Multiplayer Room Lobby Design

## Goal

Add a multiplayer room flow so one player can create a room and other human players can join from the home page. Each game still has exactly 9 seats. A room can start with 1 to 9 human players, and empty seats are filled by AI players when the host starts the game.

## Home Page

The home page shows joinable rooms. A room is joinable only when it has not started and has fewer than 9 human players.

Each room card shows:

- Room name or host name
- Current human count out of 9
- How many AI players will be added if the room starts now
- Room status
- Join action

Rooms that have already started are hidden from the joinable room list. Existing room members can continue the game from the room page or an existing room URL.

## Room Creation

A player can create a room from the home page. The creator becomes the host and is placed in the room immediately.

The creator selects:

- Display name
- Cartoon avatar

The room starts in a waiting state and appears in the joinable room list until it starts or reaches 9 human players.

## Joining A Room

A player can join a waiting room from the home page if the room has fewer than 9 human players.

The joining player selects:

- Display name
- Cartoon avatar

Cartoon avatars are unique within a room. Once a human player chooses an avatar, other human players cannot choose it in that room. AI fill-ins also use only remaining unused avatars.

## Waiting Room

The waiting room shows all 9 seats. Human players occupy joined seats. Empty seats show that they will be filled by AI if the host starts the game.

Only the host can start the game. Non-host players can mark themselves ready or cancel ready. Ready status helps the host coordinate the room, but the host remains the only player with the start action.

## Starting The Game

When the host starts the game:

1. The room is removed from the joinable room list.
2. Empty seats are filled with AI players.
3. The final player list is exactly 9 players.
4. Roles are randomly assigned using the existing 9-player role pool: 3 werewolves, 1 seer, 1 witch, 1 hunter, and 3 villagers.
5. The game proceeds through the existing room page and game flow.

## Room States

- `waiting`: Room is visible on the home page if it has fewer than 9 human players.
- `playing`: Room is hidden from the home page and remains accessible to room members.
- `ended`: Room is no longer joinable. Cleanup or history behavior can be handled separately.

## Scope

This design covers the multiplayer lobby, room membership, avatar uniqueness, host-only start, and AI fill-in behavior. It does not change the core role counts, win rules, night/day stage order, or role action semantics.

## Testing

Add tests that verify:

- The home page room list includes only waiting rooms with fewer than 9 human players.
- Room creation makes the creator the host and first human member.
- Joining is rejected for started rooms and rooms with 9 human players.
- Duplicate avatars are rejected within the same room.
- Starting a room is allowed only for the host.
- Starting a room fills empty seats with AI players up to exactly 9 total players.
- Started rooms are hidden from the joinable room list.
