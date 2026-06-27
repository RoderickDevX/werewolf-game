from fastapi.testclient import TestClient

from werewolf_langgraph.web import create_app


def test_root_domain_serves_game_hub():
    client = TestClient(create_app())

    response = client.get("/", headers={"Host": "roderickdev.cn"})

    assert response.status_code == 200
    assert "RoderickDev" in response.text
    assert "https://werewolf.roderickdev.cn" in response.text


def test_werewolf_subdomain_serves_game():
    client = TestClient(create_app())

    response = client.get("/", headers={"Host": "werewolf.roderickdev.cn"})

    assert response.status_code == 200
    assert "id=\"lobbyScreen\"" in response.text
    assert "id=\"waitingRoomScreen\"" in response.text
    assert "id=\"gameScreen\"" in response.text
    assert "styles.css?v=20260627-desktop-background-cover" in response.text
    assert "app.js?v=20260603-multiplayer-lobby" in response.text
    assert "RoderickDev" not in response.text


def test_localhost_serves_game():
    client = TestClient(create_app())

    response = client.get("/", headers={"Host": "127.0.0.1:8000"})

    assert response.status_code == 200
    assert "id=\"lobbyScreen\"" in response.text
    assert "id=\"waitingRoomScreen\"" in response.text
    assert "id=\"gameScreen\"" in response.text
    assert "RoderickDev" not in response.text


def test_game_page_contains_mobile_lobby_controls():
    client = TestClient(create_app())

    response = client.get("/", headers={"Host": "127.0.0.1:8000"})

    assert response.status_code == 200
    assert 'class="mobile-lobby-topbar"' in response.text
    assert 'id="avatarChoiceGrid"' in response.text
    assert 'id="createAvatarSelect"' in response.text
    assert 'id="roomList"' in response.text
    assert 'id="createRoomButton"' in response.text


def test_game_page_contains_mobile_waiting_room_controls():
    client = TestClient(create_app())

    response = client.get("/", headers={"Host": "127.0.0.1:8000"})

    assert response.status_code == 200
    assert 'id="waitingRoomCode"' not in response.text
    assert 'id="copyRoomCodeButton"' not in response.text
    assert 'id="waitingSeats"' in response.text
    assert 'id="readyButton"' in response.text
    assert 'id="startRoomButton"' in response.text
    assert 'id="backToLobbyButton"' in response.text
