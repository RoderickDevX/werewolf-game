import random

from fastapi.testclient import TestClient

from werewolf_langgraph import web


def setup_function():
    web.ROOMS.clear()


def test_create_room_adds_waiting_room_to_lobby(monkeypatch):
    monkeypatch.setattr(web, "build_game_graph", lambda llm: None)
    client = TestClient(web.create_app())

    response = client.post(
        "/api/rooms",
        json={"human_name": "Alice", "avatar_id": "shinchan"},
    )

    assert response.status_code == 200
    room = response.json()
    assert room["status"] == "waiting"
    assert room["host_id"] == "1"
    assert room["human_count"] == 1
    assert room["ai_fill_count"] == 8
    assert room["members"][0]["name"] == "Alice"
    assert room["members"][0]["avatar_id"] == "shinchan"

    lobby = client.get("/api/rooms").json()
    assert [item["room_id"] for item in lobby["rooms"]] == [room["room_id"]]


def test_join_room_rejects_duplicate_avatar(monkeypatch):
    monkeypatch.setattr(web, "build_game_graph", lambda llm: None)
    client = TestClient(web.create_app())
    room = client.post("/api/rooms", json={"human_name": "Alice", "avatar_id": "shinchan"}).json()

    response = client.post(
        f"/api/rooms/{room['room_id']}/join",
        json={"human_name": "Bob", "avatar_id": "shinchan"},
    )

    assert response.status_code == 400
    assert "avatar" in response.json()["detail"]


def test_avatar_choices_include_garfield_instead_of_generic_human():
    avatar_ids = {avatar["id"] for avatar in web.AVATAR_CHOICES}
    garfield = next(avatar for avatar in web.AVATAR_CHOICES if avatar["id"] == "garfield")

    assert "garfield" in avatar_ids
    assert "human" not in avatar_ids
    assert garfield["name"] == "Garfield"
    assert garfield["ai_name"] == "加菲猫"


def test_join_room_adds_next_human_seat(monkeypatch):
    monkeypatch.setattr(web, "build_game_graph", lambda llm: None)
    client = TestClient(web.create_app())
    room = client.post("/api/rooms", json={"human_name": "Alice", "avatar_id": "shinchan"}).json()

    response = client.post(
        f"/api/rooms/{room['room_id']}/join",
        json={"human_name": "Bob", "avatar_id": "nailong"},
    )

    assert response.status_code == 200
    joined = response.json()
    assert joined["human_id"] == "2"
    assert joined["human_count"] == 2
    assert joined["ai_fill_count"] == 7
    assert [member["id"] for member in joined["members"]] == ["1", "2"]


def test_leave_room_removes_non_host_from_waiting_room(monkeypatch):
    monkeypatch.setattr(web, "build_game_graph", lambda llm: None)
    client = TestClient(web.create_app())
    room = client.post("/api/rooms", json={"human_name": "Alice", "avatar_id": "shinchan"}).json()
    joined = client.post(
        f"/api/rooms/{room['room_id']}/join",
        json={"human_name": "Bob", "avatar_id": "nailong"},
    ).json()

    response = client.post(f"/api/rooms/{room['room_id']}/leave", json={"player_id": joined["human_id"]})

    assert response.status_code == 200
    remaining = client.get(f"/api/rooms/{room['room_id']}", params={"player_id": room["human_id"]}).json()
    assert remaining["human_count"] == 1
    assert [member["id"] for member in remaining["members"]] == ["1"]
    assert "nailong" in {avatar["id"] for avatar in remaining["available_avatars"]}


def test_leave_room_deletes_room_for_host(monkeypatch):
    monkeypatch.setattr(web, "build_game_graph", lambda llm: None)
    client = TestClient(web.create_app())
    room = client.post("/api/rooms", json={"human_name": "Alice", "avatar_id": "shinchan"}).json()

    response = client.post(f"/api/rooms/{room['room_id']}/leave", json={"player_id": room["human_id"]})

    assert response.status_code == 200
    assert response.json() == {"status": "closed"}
    assert client.get(f"/api/rooms/{room['room_id']}").status_code == 404
    assert client.get("/api/rooms").json()["rooms"] == []


def test_join_room_rejects_full_room(monkeypatch):
    monkeypatch.setattr(web, "build_game_graph", lambda llm: None)
    client = TestClient(web.create_app())
    room = client.post("/api/rooms", json={"human_name": "P1", "avatar_id": web.AVATAR_CHOICES[0]["id"]}).json()
    for index, avatar in enumerate(web.AVATAR_CHOICES[1:], start=2):
        response = client.post(
            f"/api/rooms/{room['room_id']}/join",
            json={"human_name": f"P{index}", "avatar_id": avatar["id"]},
        )
        assert response.status_code == 200

    response = client.post(
        f"/api/rooms/{room['room_id']}/join",
        json={"human_name": "P10", "avatar_id": "extra"},
    )

    assert response.status_code == 400
    assert "full" in response.json()["detail"]


def test_start_room_requires_host_and_fills_ai_players(monkeypatch):
    monkeypatch.setattr(random, "shuffle", lambda items: None)
    monkeypatch.setattr(web, "create_deepseek_llm", lambda config: object())
    monkeypatch.setattr(web, "build_game_graph", lambda llm: None)
    client = TestClient(web.create_app())
    room = client.post("/api/rooms", json={"human_name": "Alice", "avatar_id": "shinchan"}).json()
    joined = client.post(
        f"/api/rooms/{room['room_id']}/join",
        json={"human_name": "Bob", "avatar_id": "nailong"},
    ).json()

    forbidden = client.post(f"/api/rooms/{room['room_id']}/start", json={"player_id": joined["human_id"]})
    assert forbidden.status_code == 403

    response = client.post(f"/api/rooms/{room['room_id']}/start", json={"player_id": room["human_id"]})

    assert response.status_code == 200
    started = response.json()
    assert started["status"] == "playing"
    assert len(started["players"]) == 9
    assert len([player for player in started["players"] if player["is_human"]]) == 2
    assert len({player["name"] for player in started["players"]}) == 9
    assert client.get("/api/rooms").json()["rooms"] == []


def test_start_room_randomizes_human_seat_numbers(monkeypatch):
    def shuffle_seats(items):
        if items == [str(index) for index in range(1, 10)]:
            items[:] = ["4", "7", "2", "1", "3", "5", "6", "8", "9"]

    monkeypatch.setattr(random, "shuffle", shuffle_seats)
    monkeypatch.setattr(web, "create_deepseek_llm", lambda config: object())
    monkeypatch.setattr(web, "build_game_graph", lambda llm: None)
    client = TestClient(web.create_app())
    room = client.post("/api/rooms", json={"human_name": "Alice", "avatar_id": "shinchan"}).json()
    bob = client.post(
        f"/api/rooms/{room['room_id']}/join",
        json={"human_name": "Bob", "avatar_id": "nailong"},
    ).json()

    started = client.post(f"/api/rooms/{room['room_id']}/start", json={"player_id": room["human_id"]}).json()
    bob_view = client.get(f"/api/rooms/{room['room_id']}", params={"player_id": bob["human_id"]}).json()

    assert started["human_id"] == "4"
    assert started["host_id"] == "4"
    assert bob_view["human_id"] == "7"
    players_by_name = {player["name"]: player for player in started["players"]}
    assert players_by_name["Alice"]["id"] == "4"
    assert players_by_name["Bob"]["id"] == "7"
    assert [player["id"] for player in started["players"]] == [str(index) for index in range(1, 10)]


def test_started_room_preserves_human_and_ai_avatar_ids(monkeypatch):
    monkeypatch.setattr(random, "shuffle", lambda items: None)
    monkeypatch.setattr(web, "create_deepseek_llm", lambda config: object())
    monkeypatch.setattr(web, "build_game_graph", lambda llm: None)
    client = TestClient(web.create_app())
    room = client.post("/api/rooms", json={"human_name": "Alice", "avatar_id": "shinchan"}).json()
    client.post(
        f"/api/rooms/{room['room_id']}/join",
        json={"human_name": "Bob", "avatar_id": "nailong"},
    )

    response = client.post(f"/api/rooms/{room['room_id']}/start", json={"player_id": room["human_id"]})

    assert response.status_code == 200
    players = response.json()["players"]
    assert players[0]["avatar_id"] == "shinchan"
    assert players[1]["avatar_id"] == "nailong"
    assert players[-1]["name"] == "加菲猫"
    assert players[-1]["avatar_id"] == "garfield"


def test_started_room_rejects_join(monkeypatch):
    monkeypatch.setattr(random, "shuffle", lambda items: None)
    monkeypatch.setattr(web, "create_deepseek_llm", lambda config: object())
    monkeypatch.setattr(web, "build_game_graph", lambda llm: None)
    client = TestClient(web.create_app())
    room = client.post("/api/rooms", json={"human_name": "Alice", "avatar_id": "shinchan"}).json()
    client.post(f"/api/rooms/{room['room_id']}/start", json={"player_id": room["human_id"]})

    response = client.post(
        f"/api/rooms/{room['room_id']}/join",
        json={"human_name": "Bob", "avatar_id": "nailong"},
    )

    assert response.status_code == 400
    assert "started" in response.json()["detail"]


def test_get_room_uses_player_viewer_role(monkeypatch):
    monkeypatch.setattr(random, "shuffle", lambda items: None)
    monkeypatch.setattr(web, "create_deepseek_llm", lambda config: object())
    monkeypatch.setattr(web, "build_game_graph", lambda llm: None)
    client = TestClient(web.create_app())
    room = client.post("/api/rooms", json={"human_name": "Alice", "avatar_id": "shinchan"}).json()
    bob = client.post(
        f"/api/rooms/{room['room_id']}/join",
        json={"human_name": "Bob", "avatar_id": "nailong"},
    ).json()
    client.post(f"/api/rooms/{room['room_id']}/start", json={"player_id": room["human_id"]})

    alice_view = client.get(f"/api/rooms/{room['room_id']}", params={"player_id": room["human_id"]}).json()
    bob_view = client.get(f"/api/rooms/{room['room_id']}", params={"player_id": bob["human_id"]}).json()

    assert alice_view["human_id"] == "1"
    assert alice_view["human_role"] == "werewolf"
    assert bob_view["human_id"] == "2"
    assert bob_view["human_role"] == "werewolf"
    assert bob_view["players"][0]["role"] == "werewolf"


def test_submit_action_rejects_wrong_human_player():
    client = TestClient(web.create_app())
    room = web.Room("room1", None, human_id="1", graph=None, status="playing")
    room.waiting_for = {"kind": "speech", "speaker_id": "2"}
    web.ROOMS["room1"] = room

    response = client.post(
        "/api/rooms/room1/submit_action",
        params={"player_id": "1"},
        json={"kind": "speech", "content": "hello"},
    )

    assert response.status_code == 403
    assert "current player" in response.json()["detail"]


def test_next_stage_requires_host_player():
    client = TestClient(web.create_app())
    room = web.Room("room1", {"winner": None, "stage": web.Stage.NIGHT_START}, human_id="1", graph=None, status="playing")
    room.host_id = "1"
    web.ROOMS["room1"] = room

    response = client.post("/api/rooms/room1/next_stage", params={"player_id": "2"})

    assert response.status_code == 403
    assert "host" in response.json()["detail"]


def test_room_actions_use_room_lock():
    room = web.Room("room1", {"winner": None, "stage": web.Stage.NIGHT_START}, human_id="1", graph=None, status="playing")

    assert hasattr(room, "lock")
