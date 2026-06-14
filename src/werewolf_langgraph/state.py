from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal, Optional, Set, TypedDict


class Role(str, Enum):
    WEREWOLF = "werewolf"
    SEER = "seer"
    WITCH = "witch"
    HUNTER = "hunter"
    VILLAGER = "villager"


class Camp(str, Enum):
    WEREWOLF = "werewolf"
    GOOD = "good"


class Phase(str, Enum):
    SETUP = "setup"
    NIGHT = "night"
    DAY_DISCUSSION = "day_discussion"
    DAY_VOTE = "day_vote"
    GAME_OVER = "game_over"


class Stage(str, Enum):
    SETUP = "setup"
    NIGHT_START = "night_start"
    WOLF_ACTION = "wolf_action"
    SEER_ACTION = "seer_action"
    WITCH_ACTION = "witch_action"
    DAWN = "dawn"
    NIGHT_RESULT = "night_result"
    DAY_DISCUSSION = "day_discussion"
    DAY_DISCUSSION_DONE = "day_discussion_done"
    DAY_VOTE = "day_vote"
    DAY_VOTE_RESULT = "day_vote_result"
    HUNTER_SHOT = "hunter_shot"
    GAME_OVER = "game_over"


ROLE_LABELS: dict[Role, str] = {
    Role.WEREWOLF: "Werewolf",
    Role.SEER: "Seer",
    Role.WITCH: "Witch",
    Role.HUNTER: "Hunter",
    Role.VILLAGER: "Villager",
}


@dataclass(frozen=True)
class Player:
    id: str
    name: str
    role: Role
    is_human: bool = False
    is_alive: bool = True
    avatar_id: Optional[str] = None

    @property
    def camp(self) -> Camp:
        return Camp.WEREWOLF if self.role == Role.WEREWOLF else Camp.GOOD


@dataclass(frozen=True)
class SpeechRecord:
    day: int
    phase: Phase
    speaker_id: str
    content: str


@dataclass(frozen=True)
class VoteRecord:
    day: int
    voter_id: str
    target_id: str
    reason: str = ""


@dataclass(frozen=True)
class SeerCheck:
    night: int
    seer_id: str
    target_id: str
    result_camp: Camp


@dataclass(frozen=True)
class WitchInventory:
    has_antidote: bool = True
    has_poison: bool = True


@dataclass(frozen=True)
class NightAction:
    night: int
    wolf_target_id: Optional[str] = None
    saved_target_id: Optional[str] = None
    poison_target_id: Optional[str] = None
    dead_player_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class PublicEvent:
    day: int
    phase: Phase
    content: str


@dataclass
class GameState:
    players: list[Player]
    phase: Phase = Phase.SETUP
    stage: Stage = Stage.SETUP
    day: int = 1
    night: int = 0
    speeches: list[SpeechRecord] = field(default_factory=list)
    votes: list[VoteRecord] = field(default_factory=list)
    seer_checks: list[SeerCheck] = field(default_factory=list)
    night_actions: list[NightAction] = field(default_factory=list)
    public_events: list[PublicEvent] = field(default_factory=list)
    witch_inventory: WitchInventory = field(default_factory=WitchInventory)
    winner: Optional[Camp] = None
    pending_wolf_target_id: Optional[str] = None
    pending_witch_save_id: Optional[str] = None
    pending_witch_poison_id: Optional[str] = None
    pending_hunter_id: Optional[str] = None
    pending_hunter_return_stage: Optional[Stage] = None


class GraphState(TypedDict):
    players: list[Player]
    phase: Phase
    stage: Stage
    day: int
    night: int
    speeches: list[SpeechRecord]
    votes: list[VoteRecord]
    seer_checks: list[SeerCheck]
    night_actions: list[NightAction]
    public_events: list[PublicEvent]
    witch_inventory: WitchInventory
    winner: Optional[Literal["werewolf", "good"]]
    pending_wolf_target_id: Optional[str]
    pending_witch_save_id: Optional[str]
    pending_witch_poison_id: Optional[str]
    pending_hunter_id: Optional[str]
    pending_hunter_return_stage: Optional[Stage]


def create_initial_state(players: list[Player]) -> GameState:
    return GameState(
        players=players,
        public_events=[
            PublicEvent(day=1, phase=Phase.SETUP, content="游戏已创建，等待第一个夜晚开始。")
        ],
    )


def living_players(state: GameState) -> list[Player]:
    return [player for player in state.players if player.is_alive]


def alive_player_ids(state: GameState) -> list[str]:
    return [player.id for player in living_players(state)]


def get_player(state: GameState, player_id: str) -> Player:
    for player in state.players:
        if player.id == player_id:
            return player
    raise KeyError(f"Unknown player id: {player_id}")


def state_to_graph_state(state: GameState) -> GraphState:
    return {
        "players": state.players,
        "phase": state.phase,
        "stage": state.stage,
        "day": state.day,
        "night": state.night,
        "speeches": state.speeches,
        "votes": state.votes,
        "seer_checks": state.seer_checks,
        "night_actions": state.night_actions,
        "public_events": state.public_events,
        "witch_inventory": state.witch_inventory,
        "winner": state.winner.value if state.winner else None,
        "pending_wolf_target_id": state.pending_wolf_target_id,
        "pending_witch_save_id": state.pending_witch_save_id,
        "pending_witch_poison_id": state.pending_witch_poison_id,
        "pending_hunter_id": state.pending_hunter_id,
        "pending_hunter_return_stage": state.pending_hunter_return_stage,
    }


def graph_state_to_game_state(state: GraphState) -> GameState:
    winner = Camp(state["winner"]) if state["winner"] else None
    return GameState(
        players=state["players"],
        phase=state["phase"],
        stage=state["stage"],
        day=state["day"],
        night=state["night"],
        speeches=state["speeches"],
        votes=state["votes"],
        seer_checks=state["seer_checks"],
        night_actions=state["night_actions"],
        public_events=state["public_events"],
        witch_inventory=state["witch_inventory"],
        winner=winner,
        pending_wolf_target_id=state["pending_wolf_target_id"],
        pending_witch_save_id=state["pending_witch_save_id"],
        pending_witch_poison_id=state["pending_witch_poison_id"],
        pending_hunter_id=state["pending_hunter_id"],
        pending_hunter_return_stage=state["pending_hunter_return_stage"],
    )


def set_players_alive(players: list[Player], dead_player_ids: Set[str]) -> list[Player]:
    return [
        Player(
            id=player.id,
            name=player.name,
            role=player.role,
            is_human=player.is_human,
            is_alive=False if player.id in dead_player_ids else player.is_alive,
            avatar_id=player.avatar_id,
        )
        for player in players
    ]


def public_event(state: GraphState, content: str, phase: Optional[Phase] = None) -> PublicEvent:
    return PublicEvent(day=state["day"], phase=phase or state["phase"], content=content)


def interrupt_payload(kind: str, message: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {"kind": kind, "message": message, "candidates": candidates}
