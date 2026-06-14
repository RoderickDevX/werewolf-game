from __future__ import annotations

import argparse
import os
import random
import threading
import uuid
from dataclasses import asdict, dataclass
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
AVATAR_CHOICES = [
    {"id": "shinchan", "name": "Shinchan", "ai_name": AI_NAMES[0]},
    {"id": "lazy-yangyang", "name": "Lazy Yangyang", "ai_name": AI_NAMES[1]},
    {"id": "ggbond", "name": "GG Bond", "ai_name": AI_NAMES[2]},
    {"id": "conan", "name": "Conan", "ai_name": AI_NAMES[3]},
    {"id": "doraemon", "name": "Doraemon", "ai_name": AI_NAMES[4]},
    {"id": "peppa", "name": "Peppa", "ai_name": AI_NAMES[5]},
    {"id": "nailong", "name": "Nailong", "ai_name": AI_NAMES[6]},
    {"id": "spongebob", "name": "Spongebob", "ai_name": AI_NAMES[7]},
    {"id": "garfield", "name": "Garfield", "ai_name": "加菲猫"},
]
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
    avatar_id: Optional[str] = None


class JoinRoomRequest(BaseModel):
    human_name: str = "打摆子的家伙"
    avatar_id: str


class PlayerRoomRequest(BaseModel):
    player_id: str


class SubmitActionRequest(BaseModel):
    kind: str
    target_id: Optional[str] = None
    content: Optional[str] = None
    save_target_id: Optional[str] = None
    poison_target_id: Optional[str] = None


@dataclass(frozen=True)
class RoomMember:
    id: str
    name: str
    avatar_id: str
    is_host: bool = False
    is_ready: bool = False


class Room:
    def __init__(
        self,
        room_id: str,
        state: Optional[GraphState],
        human_id: str,
        graph: Any,
        *,
        host_id: Optional[str] = None,
        members: Optional[list[RoomMember]] = None,
        status: str = "playing",
    ):
        self.room_id = room_id
        self.state = state
        self.human_id = human_id
        self.graph = graph
        self.waiting_for: Optional[dict[str, Any]] = None
        self.status = status
        self.host_id = host_id or human_id
        self.members = members or []
        self.lock = threading.Lock()

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
    def index(request: Request) -> str:
        host = request.headers.get("host", "").split(":", maxsplit=1)[0].lower()
        local_hosts = {"127.0.0.1", "localhost", "::1"}
        page = "index.html" if host.startswith("werewolf.") or host in local_hosts else "home.html"
        with open(STATIC_DIR / page, "r", encoding="utf-8") as file:
            return file.read()

    @app.post("/api/rooms")
    def create_room(payload: CreateRoomRequest) -> dict[str, Any]:
        if payload.human_seat < 1 or payload.human_seat > 9:
            raise HTTPException(status_code=400, detail="human_seat must be between 1 and 9.")

        if payload.avatar_id:
            member = RoomMember(
                id="1",
                name=payload.human_name.strip() or "Player",
                avatar_id=_valid_avatar_id(payload.avatar_id),
                is_host=True,
            )
            room_id = uuid.uuid4().hex[:8]
            room = Room(
                room_id,
                None,
                human_id=member.id,
                graph=None,
                host_id=member.id,
                members=[member],
                status="waiting",
            )
            ROOMS[room_id] = room
            return _serialize_room(room)

        config = load_config()
        llm = create_deepseek_llm(config)
        graph = build_game_graph(llm)
        players = _make_players(payload.human_name.strip() or "打摆子的家伙", payload.human_seat)
        state = state_to_graph_state(create_initial_state(players))
        room_id = uuid.uuid4().hex[:8]
        room = Room(room_id, state, human_id=str(payload.human_seat), graph=graph)
        ROOMS[room_id] = room
        return _serialize_room(room)

    @app.get("/api/rooms")
    def list_rooms() -> dict[str, Any]:
        return {
            "rooms": [
                _serialize_lobby_room(room)
                for room in ROOMS.values()
                if room.status == "waiting" and len(room.members) < 9
            ]
        }

    @app.get("/api/rooms/{room_id}")
    def get_room(room_id: str, player_id: Optional[str] = None) -> dict[str, Any]:
        return _serialize_room(_get_room(room_id), viewer_id=player_id)

    @app.post("/api/rooms/{room_id}/join")
    def join_room(room_id: str, payload: JoinRoomRequest) -> dict[str, Any]:
        room = _get_room(room_id)
        if room.status != "waiting":
            raise HTTPException(status_code=400, detail="room already started.")
        if len(room.members) >= 9:
            raise HTTPException(status_code=400, detail="room is full.")

        avatar_id = _valid_avatar_id(payload.avatar_id)
        if avatar_id in {member.avatar_id for member in room.members}:
            raise HTTPException(status_code=400, detail="avatar already taken.")

        member = RoomMember(
            id=_next_member_id(room.members),
            name=payload.human_name.strip() or "Player",
            avatar_id=avatar_id,
        )
        room.members = [*room.members, member]
        room.human_id = member.id
        return _serialize_room(room, viewer_id=member.id)

    @app.post("/api/rooms/{room_id}/ready")
    def set_ready(room_id: str, payload: PlayerRoomRequest) -> dict[str, Any]:
        room = _get_room(room_id)
        if room.status != "waiting":
            raise HTTPException(status_code=400, detail="room already started.")
        room.members = [
            RoomMember(
                id=member.id,
                name=member.name,
                avatar_id=member.avatar_id,
                is_host=member.is_host,
                is_ready=not member.is_ready if member.id == payload.player_id else member.is_ready,
            )
            for member in room.members
        ]
        return _serialize_room(room, viewer_id=payload.player_id)

    @app.post("/api/rooms/{room_id}/start")
    def start_room(room_id: str, payload: PlayerRoomRequest) -> dict[str, Any]:
        room = _get_room(room_id)
        if room.status != "waiting":
            raise HTTPException(status_code=400, detail="room already started.")
        if payload.player_id != room.host_id:
            raise HTTPException(status_code=403, detail="only host can start the room.")

        config = load_config()
        llm = create_deepseek_llm(config)
        graph = build_game_graph(llm)
        players = _make_multiplayer_players(room.members)
        room.graph = graph
        room.state = state_to_graph_state(create_initial_state(players))
        room.status = "playing"
        room.human_id = payload.player_id
        return _serialize_room(room, viewer_id=payload.player_id)

    @app.post("/api/rooms/{room_id}/next_stage")
    def next_stage(room_id: str, player_id: Optional[str] = None) -> dict[str, Any]:
        room = _get_room(room_id)
        if player_id and player_id != room.host_id:
            raise HTTPException(status_code=403, detail="only host can advance the room.")
        with room.lock:
            if room.waiting_for:
                return _serialize_room(room, viewer_id=player_id)
            if room.state["winner"] and room.state["stage"] not in {Stage.NIGHT_RESULT, Stage.DAY_VOTE_RESULT}:
                return _serialize_room(room, viewer_id=player_id)

            result = room.graph.invoke(room.state, config=room.config)
            _store_graph_result(room, result)
        return _serialize_room(room, viewer_id=player_id)

    @app.post("/api/rooms/{room_id}/submit_action")
    def submit_action(room_id: str, payload: SubmitActionRequest, player_id: Optional[str] = None) -> dict[str, Any]:
        room = _get_room(room_id)
        with room.lock:
            if not room.waiting_for:
                raise HTTPException(status_code=400, detail="No human action is currently required.")
            if payload.kind != room.waiting_for.get("kind"):
                raise HTTPException(status_code=400, detail="Submitted action does not match current requirement.")
            _ensure_current_human_player(room, player_id)

            result = room.graph.invoke(Command(resume=_resume_payload(payload)), config=room.config)
            _store_graph_result(room, result)
        return _serialize_room(room, viewer_id=player_id)

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


def _ensure_current_human_player(room: Room, player_id: Optional[str]) -> None:
    if not player_id:
        return
    expected_id = _waiting_player_id(room)
    if expected_id and player_id != expected_id:
        raise HTTPException(status_code=403, detail="action is only allowed for the current player.")


def _waiting_player_id(room: Room) -> Optional[str]:
    if not room.waiting_for:
        return None
    for key in ("speaker_id", "voter_id"):
        value = room.waiting_for.get(key)
        if isinstance(value, str):
            return value
    if room.state is None:
        return None
    game_state = graph_state_to_game_state(room.state)
    kind = room.waiting_for.get("kind")
    role_by_kind = {
        "wolf_kill": Role.WEREWOLF,
        "seer_check": Role.SEER,
        "witch_action": Role.WITCH,
        "hunter_shot": Role.HUNTER,
    }.get(kind)
    if role_by_kind is None:
        return None
    for player in game_state.players:
        if player.is_human and player.is_alive and player.role == role_by_kind:
            return player.id
    return None


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


def _make_multiplayer_players(members: list[RoomMember]) -> list[Player]:
    roles = DEFAULT_ROLES[:]
    random.shuffle(roles)
    members_by_id = {member.id: member for member in members}
    used_avatars = {member.avatar_id for member in members}
    remaining_avatars = [avatar for avatar in AVATAR_CHOICES if avatar["id"] not in used_avatars]
    ai_avatars = iter(remaining_avatars)
    players = []
    for seat in range(1, 10):
        seat_id = str(seat)
        role = roles[seat - 1]
        member = members_by_id.get(seat_id)
        if member:
            players.append(Player(id=seat_id, name=member.name, role=role, is_human=True, avatar_id=member.avatar_id))
            continue
        avatar = next(ai_avatars)
        players.append(Player(id=seat_id, name=avatar["ai_name"], role=role, is_human=False, avatar_id=avatar["id"]))
    return players


def _valid_avatar_id(avatar_id: str) -> str:
    avatar_ids = {avatar["id"] for avatar in AVATAR_CHOICES}
    if avatar_id not in avatar_ids:
        raise HTTPException(status_code=400, detail="unknown avatar.")
    return avatar_id


def _next_member_id(members: list[RoomMember]) -> str:
    used_ids = {member.id for member in members}
    for seat in range(1, 10):
        if str(seat) not in used_ids:
            return str(seat)
    raise HTTPException(status_code=400, detail="room is full.")


def _get_room(room_id: str) -> Room:
    room = ROOMS.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found.")
    return room


def _serialize_room(room: Room, viewer_id: Optional[str] = None) -> dict[str, Any]:
    if room.status == "waiting":
        return _serialize_waiting_room(room, viewer_id or room.human_id)
    if room.state is None:
        raise HTTPException(status_code=500, detail="room has no game state.")
    game_state = graph_state_to_game_state(room.state)
    human_id = viewer_id or room.human_id
    human = next(player for player in game_state.players if player.id == human_id)
    show_wolf_teammates = human.role == Role.WEREWOLF and not bool(game_state.winner)
    return {
        "room_id": room.room_id,
        "status": room.status,
        "host_id": room.host_id,
        "human_id": human_id,
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
                reveal_role=_should_reveal_role(player, human_id, bool(game_state.winner), show_wolf_teammates),
            )
            for player in game_state.players
        ],
        "speeches": [_serialize_dataclass(record) for record in game_state.speeches],
        "votes": [_serialize_dataclass(record) for record in game_state.votes],
        "seer_checks": [_serialize_dataclass(record) for record in game_state.seer_checks],
        "events": [_serialize_event(event) for event in game_state.public_events],
    }


def _serialize_waiting_room(room: Room, viewer_id: str) -> dict[str, Any]:
    used_avatars = {member.avatar_id for member in room.members}
    return {
        "room_id": room.room_id,
        "status": room.status,
        "host_id": room.host_id,
        "human_id": viewer_id,
        "human_count": len(room.members),
        "ai_fill_count": 9 - len(room.members),
        "members": [_serialize_member(member) for member in room.members],
        "available_avatars": [avatar for avatar in AVATAR_CHOICES if avatar["id"] not in used_avatars],
    }


def _serialize_lobby_room(room: Room) -> dict[str, Any]:
    host = next((member for member in room.members if member.id == room.host_id), room.members[0])
    return {
        "room_id": room.room_id,
        "status": room.status,
        "host_id": room.host_id,
        "host_name": host.name,
        "human_count": len(room.members),
        "ai_fill_count": 9 - len(room.members),
    }


def _serialize_member(member: RoomMember) -> dict[str, Any]:
    return {
        "id": member.id,
        "name": member.name,
        "avatar_id": member.avatar_id,
        "is_host": member.is_host,
        "is_ready": member.is_ready,
    }


def _serialize_player(player: Player, reveal_role: bool) -> dict[str, Any]:
    return {
        "id": player.id,
        "name": player.name,
        "role": player.role.value if reveal_role else "hidden",
        "is_human": player.is_human,
        "is_alive": player.is_alive,
        "avatar_id": player.avatar_id,
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
