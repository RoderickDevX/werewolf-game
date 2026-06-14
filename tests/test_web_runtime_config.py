import sys

from fastapi.testclient import TestClient

from werewolf_langgraph import web


def test_main_uses_environment_defaults(monkeypatch):
    monkeypatch.setenv("WEREWOLF_HOST", "0.0.0.0")
    monkeypatch.setenv("WEREWOLF_PORT", "9000")
    monkeypatch.setattr(sys, "argv", ["werewolf-web"])

    captured = {}

    def fake_run(app, **kwargs):
        captured["kwargs"] = kwargs

    monkeypatch.setattr(web.uvicorn, "run", fake_run)

    web.main()

    assert captured["kwargs"]["host"] == "0.0.0.0"
    assert captured["kwargs"]["port"] == 9000
    assert captured["kwargs"]["proxy_headers"] is True
    assert captured["kwargs"]["forwarded_allow_ips"] == "*"


def test_main_allows_cli_overrides(monkeypatch):
    monkeypatch.setenv("WEREWOLF_HOST", "0.0.0.0")
    monkeypatch.setenv("WEREWOLF_PORT", "9000")
    monkeypatch.setattr(sys, "argv", ["werewolf-web", "--host", "127.0.0.1", "--port", "8123"])

    captured = {}

    def fake_run(app, **kwargs):
        captured["kwargs"] = kwargs

    monkeypatch.setattr(web.uvicorn, "run", fake_run)

    web.main()

    assert captured["kwargs"]["host"] == "127.0.0.1"
    assert captured["kwargs"]["port"] == 8123


def test_static_assets_are_cacheable_while_html_and_api_remain_no_store():
    client = TestClient(web.create_app())

    html_response = client.get("/", headers={"host": "werewolf.roderickdev.cn"})
    assert "no-store" in html_response.headers["Cache-Control"]

    api_response = client.get("/api/rooms")
    assert "no-store" in api_response.headers["Cache-Control"]

    static_response = client.get("/static/assets/avatars/shinchan.webp")
    assert static_response.status_code == 200
    assert "no-store" not in static_response.headers["Cache-Control"]
    assert "public" in static_response.headers["Cache-Control"]
    assert "max-age=" in static_response.headers["Cache-Control"]
