from __future__ import annotations

import argparse
import os
import random
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from langgraph.types import Command
from pydantic import BaseModel

from .config import load_config
from .deepseek import create_deepseek_llm
from .game_graph import build_game_graph
from .state import (
    Camp,
    GraphState,
    Phase,
    Player,
    Role,
    Stage,
    create_initial_state,
    graph_state_to_game_state,
    state_to_graph_state,
)


AI_NAMES = ["蜡笔小新", "懒羊羊", "猪猪侠", "柯南", "哆啦A梦", "小猪佩奇", "奶龙", "海绵宝宝"]
DEFAULT_ROLES = [
    Role.WEREWOLF,
    Role.WEREWOLF,
    Role.WEREWOLF,
    Role.SEER,
    Role.WITCH,
    Role.HUNTER,
    Role.VILLAGER,
    Role.VILLAGER,
    Role.VILLAGER,
]
STATIC_DIR = Path(__file__).resolve().parent / "static"

def _default_host() -> str:
    return os.getenv("WEREWOLF_HOST", "127.0.0.1")


def _default_port() -> int:
    raw_port = os.getenv("WEREWOLF_PORT", "8000").strip()
    try:
        return int(raw_port)
    except ValueError as error:
        raise ValueError("WEREWOLF_PORT must be an integer.") from error


class CreateRoomRequest(BaseModel):
    human_name: str = "打摆子的家伙"
    human_seat: int = 1


class SubmitActionRequest(BaseModel):
    kind: str
    target_id: Optional[str] = None
    content: Optional[str] = None
    save_target_id: Optional[str] = None
    poison_target_id: Optional[str] = None


class Room:
    def __init__(self, room_id: str, state: GraphState, human_id: str, graph: Any):
        self.room_id = room_id
        self.state = state
        self.human_id = human_id
        self.graph = graph
        self.waiting_for: Optional[dict[str, Any]] = None

    @property
    def config(self) -> dict[str, Any]:
        return {"configurable": {"thread_id": self.room_id}}


ROOMS: dict[str, Room] = {}


def create_app() -> FastAPI:
    app = FastAPI(title="Werewolf")
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.middleware("http")
    async def no_cache_middleware(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        with open(STATIC_DIR / "index.html", "r", encoding="utf-8") as file:
            return file.read()

    @app.post("/api/rooms")
    def create_room(payload: CreateRoomRequest) -> dict[str, Any]:
        if payload.human_seat < 1 or payload.human_seat > 9:
            raise HTTPException(status_code=400, detail="human_seat must be between 1 and 9.")

        config = load_config()
        llm = create_deepseek_llm(config)
        graph = build_game_graph(llm)
        players = _make_players(payload.human_name.strip() or "打摆子的家伙", payload.human_seat)
        state = state_to_graph_state(create_initial_state(players))
        room_id = uuid.uuid4().hex[:8]
        room = Room(room_id, state, human_id=str(payload.human_seat), graph=graph)
        ROOMS[room_id] = room
        return _serialize_room(room)

    @app.get("/api/rooms/{room_id}")
    def get_room(room_id: str) -> dict[str, Any]:
        return _serialize_room(_get_room(room_id))

    @app.post("/api/rooms/{room_id}/next_stage")
    def next_stage(room_id: str) -> dict[str, Any]:
        room = _get_room(room_id)
        if room.waiting_for:
            return _serialize_room(room)
        if room.state["winner"] and room.state["stage"] not in {Stage.NIGHT_RESULT, Stage.DAY_VOTE_RESULT}:
            return _serialize_room(room)

        result = room.graph.invoke(room.state, config=room.config)
        _store_graph_result(room, result)
        return _serialize_room(room)

    @app.post("/api/rooms/{room_id}/submit_action")
    def submit_action(room_id: str, payload: SubmitActionRequest) -> dict[str, Any]:
        room = _get_room(room_id)
        if not room.waiting_for:
            raise HTTPException(status_code=400, detail="No human action is currently required.")
        if payload.kind != room.waiting_for.get("kind"):
            raise HTTPException(status_code=400, detail="Submitted action does not match current requirement.")

        result = room.graph.invoke(Command(resume=_resume_payload(payload)), config=room.config)
        _store_graph_result(room, result)
        return _serialize_room(room)

    return app


def _store_graph_result(room: Room, result: dict[str, Any]) -> None:
    interrupts = result.get("__interrupt__") or []
    if interrupts:
        room.waiting_for = interrupts[0].value
        snapshot = room.graph.get_state(room.config)
        room.state = snapshot.values
        return

    room.waiting_for = None
    room.state = result


def _resume_payload(payload: SubmitActionRequest) -> dict[str, Any]:
    data = payload.model_dump(exclude_none=True)
    return data


def _make_players(human_name: str, human_seat: int) -> list[Player]:
    roles = DEFAULT_ROLES[:]
    random.shuffle(roles)
    ai_names = iter(random.sample(AI_NAMES, k=len(DEFAULT_ROLES) - 1))
    players = []
    for seat in range(1, 10):
        role = roles[seat - 1]
        if seat == human_seat:
            players.append(Player(id=str(seat), name=human_name, role=role, is_human=True))
        else:
            players.append(Player(id=str(seat), name=next(ai_names), role=role, is_human=False))
    return players


def _get_room(room_id: str) -> Room:
    room = ROOMS.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found.")
    return room


def _serialize_room(room: Room) -> dict[str, Any]:
    game_state = graph_state_to_game_state(room.state)
    human = next(player for player in game_state.players if player.id == room.human_id)
    show_wolf_teammates = human.role == Role.WEREWOLF and not bool(game_state.winner)
    return {
        "room_id": room.room_id,
        "human_id": room.human_id,
        "human_role": human.role.value,
        "phase": game_state.phase.value,
        "stage": game_state.stage.value,
        "day": game_state.day,
        "night": game_state.night,
        "winner": game_state.winner.value if game_state.winner else None,
        "wolf_teammates": _serialize_wolf_teammates(game_state.players, human),
        "waiting_for": room.waiting_for,
        "players": [
            _serialize_player(
                player,
                reveal_role=_should_reveal_role(player, room.human_id, bool(game_state.winner), show_wolf_teammates),
            )
            for player in game_state.players
        ],
        "speeches": [_serialize_dataclass(record) for record in game_state.speeches],
        "votes": [_serialize_dataclass(record) for record in game_state.votes],
        "seer_checks": [_serialize_dataclass(record) for record in game_state.seer_checks],
        "events": [_serialize_event(event) for event in game_state.public_events],
    }


def _serialize_player(player: Player, reveal_role: bool) -> dict[str, Any]:
    return {
        "id": player.id,
        "name": player.name,
        "role": player.role.value if reveal_role else "hidden",
        "is_human": player.is_human,
        "is_alive": player.is_alive,
    }


def _should_reveal_role(player: Player, human_id: str, game_over: bool, show_wolf_teammates: bool = False) -> bool:
    if player.id == human_id or game_over or (player.role == Role.HUNTER and not player.is_alive):
        return True
    if show_wolf_teammates and player.role == Role.WEREWOLF:
        return True
    return False


def _serialize_wolf_teammates(players: list[Player], human: Player) -> list[dict[str, str]]:
    if human.role != Role.WEREWOLF:
        return []
    return [{"id": player.id, "name": player.name} for player in players if player.role == Role.WEREWOLF and player.id != human.id]


def _serialize_event(event) -> dict[str, Any]:
    return {"day": event.day, "phase": event.phase.value, "content": event.content}


def _serialize_dataclass(value: Any) -> dict[str, Any]:
    data = asdict(value)
    for key, item in list(data.items()):
        if isinstance(item, (Role, Phase, Camp, Stage)):
            data[key] = item.value
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Werewolf web app.")
    parser.add_argument("--host", default=_default_host())
    parser.add_argument("--port", type=int, default=_default_port())
    args = parser.parse_args()
    uvicorn.run(
        create_app(),
        host=args.host,
        port=args.port,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


app = create_app()
