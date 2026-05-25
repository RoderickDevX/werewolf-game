from __future__ import annotations

from collections import Counter
from typing import Any, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from .agents import create_role_agents
from .state import (
    Camp,
    GraphState,
    NightAction,
    Phase,
    Player,
    Role,
    SeerCheck,
    SpeechRecord,
    Stage,
    VoteRecord,
    WitchInventory,
    alive_player_ids,
    get_player,
    graph_state_to_game_state,
    interrupt_payload,
    living_players,
    public_event,
    set_players_alive,
)


def build_game_graph(llm: BaseChatModel):
    workflow = StateGraph(GraphState)
    workflow.add_node("advance_stage", _make_advance_stage(llm))
    workflow.add_edge(START, "advance_stage")
    workflow.add_edge("advance_stage", END)
    return workflow.compile(checkpointer=MemorySaver())


def _make_advance_stage(llm: BaseChatModel):
    def advance_stage(state: GraphState) -> dict[str, Any]:
        stage = state["stage"]
        if state["winner"]:
            return {"phase": Phase.GAME_OVER, "stage": Stage.GAME_OVER}
        if stage == Stage.SETUP:
            return _enter_night(state)
        if stage == Stage.NIGHT_START:
            return {"stage": Stage.WOLF_ACTION}
        if stage == Stage.WOLF_ACTION:
            return _wolf_action(state, llm)
        if stage == Stage.SEER_ACTION:
            return _seer_action(state, llm)
        if stage == Stage.WITCH_ACTION:
            return _witch_action(state, llm)
        if stage == Stage.HUNTER_SHOT:
            return _hunter_shot(state, llm)
        if stage == Stage.NIGHT_RESULT:
            return {"phase": Phase.GAME_OVER, "stage": Stage.GAME_OVER}
        if stage == Stage.DAWN:
            return _enter_day_discussion(state)
        if stage == Stage.DAY_DISCUSSION:
            return _day_discussion(state, llm)
        if stage == Stage.DAY_DISCUSSION_DONE:
            return _enter_day_vote(state)
        if stage == Stage.DAY_VOTE:
            return _day_vote(state, llm)
        if stage == Stage.DAY_VOTE_RESULT:
            return _enter_next_round(state)
        return {}

    return advance_stage


def _enter_night(state: GraphState) -> dict[str, Any]:
    night = state["night"] + 1
    return {
        "phase": Phase.NIGHT,
        "stage": Stage.NIGHT_START,
        "night": night,
        "pending_wolf_target_id": None,
        "pending_witch_save_id": None,
        "pending_witch_poison_id": None,
        "pending_hunter_id": None,
        "pending_hunter_return_stage": None,
        "public_events": [
            *state["public_events"],
            public_event(state, f"第 {night} 夜开始。", Phase.NIGHT),
        ],
    }


def _wolf_action(state: GraphState, llm: BaseChatModel) -> dict[str, Any]:
    game_state = graph_state_to_game_state(state)
    wolves = [player for player in living_players(game_state) if player.role == Role.WEREWOLF]
    candidates = [player for player in living_players(game_state) if player.role != Role.WEREWOLF]
    if not wolves or not candidates:
        return {"stage": Stage.SEER_ACTION, "pending_wolf_target_id": None}

    human_wolf = next((player for player in wolves if player.is_human), None)
    if human_wolf:
        payload = interrupt(
            interrupt_payload(
                "wolf_kill",
                "请选择今晚要袭击的玩家。",
                [_candidate(player) for player in candidates],
            )
        )
        target_id = _valid_target(payload, candidates)
        return {
            "stage": Stage.SEER_ACTION,
            "pending_wolf_target_id": target_id,
            "public_events": [
                *state["public_events"],
                public_event(state, "狼人已选定夜晚袭击目标。", Phase.NIGHT),
            ],
        }

    agents = create_role_agents(llm, game_state)
    choices = [agents[wolf.id].choose_wolf_kill(game_state).target_id for wolf in wolves]
    target_id = Counter(choices).most_common(1)[0][0]
    return {
        "stage": Stage.SEER_ACTION,
        "pending_wolf_target_id": target_id,
        "public_events": [
            *state["public_events"],
            public_event(state, "狼人已选定夜晚袭击目标。", Phase.NIGHT),
        ],
    }


def _seer_action(state: GraphState, llm: BaseChatModel) -> dict[str, Any]:
    game_state = graph_state_to_game_state(state)
    seer = _first_alive_player(game_state.players, Role.SEER)
    if seer is None:
        return {"stage": Stage.WITCH_ACTION}

    candidates = [
        player
        for player in living_players(game_state)
        if player.id != seer.id and player.id not in {check.target_id for check in state["seer_checks"] if check.seer_id == seer.id}
    ]
    if not candidates:
        candidates = [player for player in living_players(game_state) if player.id != seer.id]
    if not candidates:
        return {"stage": Stage.WITCH_ACTION}

    if seer.is_human:
        payload = interrupt(
            interrupt_payload(
                "seer_check",
                "请选择要查验的玩家。",
                [_candidate(player) for player in candidates],
            )
        )
        target_id = _valid_target(payload, candidates)
        target = get_player(game_state, target_id)
        check = SeerCheck(night=state["night"], seer_id=seer.id, target_id=target_id, result_camp=target.camp)
    else:
        decision = create_role_agents(llm, game_state)[seer.id].choose_seer_check(game_state)
        check = decision.check

    return {
        "stage": Stage.WITCH_ACTION,
        "seer_checks": [*state["seer_checks"], check],
        "public_events": [
            *state["public_events"],
            public_event(state, "预言家已完成查验。", Phase.NIGHT),
        ],
    }


def _witch_action(state: GraphState, llm: BaseChatModel) -> dict[str, Any]:
    game_state = graph_state_to_game_state(state)
    witch = _first_alive_player(game_state.players, Role.WITCH)
    if witch is None:
        return _resolve_night(state)

    poison_candidates = [player for player in living_players(game_state) if player.id != witch.id]
    save_candidates = []
    if state["pending_wolf_target_id"] and state["witch_inventory"].has_antidote:
        save_candidates = [get_player(game_state, state["pending_wolf_target_id"])]

    if witch.is_human:
        payload = interrupt(
            {
                "kind": "witch_action",
                "message": "请选择是否使用解药或毒药。",
                "save_candidates": [_candidate(player) for player in save_candidates],
                "poison_candidates": [_candidate(player) for player in poison_candidates] if state["witch_inventory"].has_poison else [],
                "can_save": state["witch_inventory"].has_antidote and bool(save_candidates),
                "can_poison": state["witch_inventory"].has_poison,
            }
        )
        save_id = _optional_target(payload.get("save_target_id"), save_candidates)
        poison_id = _optional_target(payload.get("poison_target_id"), poison_candidates if state["witch_inventory"].has_poison else [])
    else:
        decision = create_role_agents(llm, game_state)[witch.id].choose_witch_action(
            game_state, state["pending_wolf_target_id"]
        )
        save_id = decision.save_target_id
        poison_id = decision.poison_target_id

    inventory = state["witch_inventory"]
    action_state = {
        **state,
        "stage": Stage.WITCH_ACTION,
        "pending_witch_save_id": save_id,
        "pending_witch_poison_id": poison_id,
        "witch_inventory": WitchInventory(
            has_antidote=inventory.has_antidote and save_id is None,
            has_poison=inventory.has_poison and poison_id is None,
        ),
        "public_events": [
            *state["public_events"],
            public_event(state, "女巫已完成夜晚行动。", Phase.NIGHT),
        ],
    }
    return {**_resolve_night(action_state), "witch_inventory": action_state["witch_inventory"]}


def _resolve_night(state: GraphState) -> dict[str, Any]:
    game_state = graph_state_to_game_state(state)
    dead_ids: list[str] = []
    wolf_target = state["pending_wolf_target_id"]
    save_target = state["pending_witch_save_id"]
    poison_target = state["pending_witch_poison_id"]

    if wolf_target and wolf_target != save_target:
        dead_ids.append(wolf_target)
    if poison_target and poison_target not in dead_ids:
        dead_ids.append(poison_target)

    players = set_players_alive(state["players"], set(dead_ids))
    action = NightAction(
        night=state["night"],
        wolf_target_id=wolf_target,
        saved_target_id=save_target,
        poison_target_id=poison_target,
        dead_player_ids=tuple(dead_ids),
    )
    events = [*state["public_events"], public_event(state, _night_result_text(game_state, dead_ids), Phase.NIGHT)]
    night_actions = [*state["night_actions"], action]
    hunter = _dead_hunter(state["players"], dead_ids)
    if hunter:
        return {
            "players": players,
            "phase": Phase.NIGHT,
            "stage": Stage.HUNTER_SHOT,
            "winner": None,
            "night_actions": night_actions,
            "pending_wolf_target_id": None,
            "pending_witch_save_id": None,
            "pending_witch_poison_id": None,
            "pending_hunter_id": hunter.id,
            "pending_hunter_return_stage": Stage.NIGHT_RESULT,
            "public_events": [
                *events,
                public_event(state, f"{hunter.name} 死亡，身份为猎人，可以发动技能。", Phase.NIGHT),
            ],
        }

    next_state = {**state, "players": players}
    winner = _winner(next_state)

    if winner:
        return {
            "players": players,
            "phase": Phase.GAME_OVER,
            "stage": Stage.NIGHT_RESULT,
            "winner": winner.value,
            "night_actions": night_actions,
            "pending_wolf_target_id": None,
            "pending_witch_save_id": None,
            "pending_witch_poison_id": None,
            "pending_hunter_id": None,
            "pending_hunter_return_stage": None,
            "public_events": [*events, public_event(state, _winner_text(winner), Phase.GAME_OVER)],
        }

    return {
        "players": players,
        "phase": Phase.DAY_DISCUSSION,
        "stage": Stage.DAWN,
        "night_actions": night_actions,
        "pending_wolf_target_id": None,
        "pending_witch_save_id": None,
        "pending_witch_poison_id": None,
        "pending_hunter_id": None,
        "pending_hunter_return_stage": None,
        "public_events": events,
    }


def _hunter_shot(state: GraphState, llm: BaseChatModel) -> dict[str, Any]:
    game_state = graph_state_to_game_state(state)
    hunter_id = state["pending_hunter_id"]
    if not hunter_id:
        return _finish_after_hunter_shot(state)

    hunter = get_player(game_state, hunter_id)
    candidates = [player for player in living_players(game_state) if player.id != hunter_id]
    if not candidates:
        return _finish_after_hunter_shot(state)

    if hunter.is_human:
        payload = interrupt(
            interrupt_payload(
                "hunter_shot",
                "请选择猎人死亡时要带走的玩家。",
                [_candidate(player) for player in candidates],
            )
        )
        target_id = _valid_target(payload, candidates)
    else:
        target_id = _choose_ai_hunter_target(llm, game_state, hunter, candidates)

    return _resolve_hunter_shot(state, target_id)


def _resolve_hunter_shot(state: GraphState, target_id: str) -> dict[str, Any]:
    game_state = graph_state_to_game_state(state)
    candidates = [player for player in living_players(game_state) if player.id != state["pending_hunter_id"]]
    if not candidates:
        return _finish_after_hunter_shot(state)

    valid_target_id = _valid_target({"target_id": target_id}, candidates)
    target = get_player(game_state, valid_target_id)
    hunter = get_player(game_state, state["pending_hunter_id"]) if state["pending_hunter_id"] else None
    next_state = {
        **state,
        "players": set_players_alive(state["players"], {valid_target_id}),
        "pending_hunter_id": None,
        "public_events": [
            *state["public_events"],
            public_event(state, f"{hunter.name if hunter else '猎人'}开枪带走了{target.name}。", state["phase"]),
        ],
    }
    return _finish_after_hunter_shot(next_state)


def _finish_after_hunter_shot(state: GraphState) -> dict[str, Any]:
    winner = _winner(state)
    return_stage = state["pending_hunter_return_stage"] or state["stage"]
    base = {
        "players": state["players"],
        "pending_hunter_id": None,
        "pending_hunter_return_stage": None,
        "pending_wolf_target_id": None,
        "pending_witch_save_id": None,
        "pending_witch_poison_id": None,
        "public_events": state["public_events"],
    }
    if winner:
        return {
            **base,
            "phase": Phase.GAME_OVER,
            "stage": return_stage,
            "winner": winner.value,
            "public_events": [
                *state["public_events"],
                public_event(state, _winner_text(winner), Phase.GAME_OVER),
            ],
        }
    if return_stage == Stage.NIGHT_RESULT:
        return {**base, "phase": Phase.DAY_DISCUSSION, "stage": Stage.DAWN, "winner": None}
    return {**base, "phase": Phase.DAY_VOTE, "stage": Stage.DAY_VOTE_RESULT, "winner": None}


def _enter_day_discussion(state: GraphState) -> dict[str, Any]:
    return {
        "phase": Phase.DAY_DISCUSSION,
        "stage": Stage.DAY_DISCUSSION,
        "public_events": [
            *state["public_events"],
            public_event(state, f"第 {state['day']} 天发言开始。", Phase.DAY_DISCUSSION),
        ],
    }


def _day_discussion(state: GraphState, llm: BaseChatModel) -> dict[str, Any]:
    game_state = graph_state_to_game_state({**state, "phase": Phase.DAY_DISCUSSION, "stage": Stage.DAY_DISCUSSION})
    speeches = list(state["speeches"])
    next_speaker = _next_discussion_speaker(state, game_state)

    if next_speaker is None:
        return {
            "phase": Phase.DAY_DISCUSSION,
            "stage": Stage.DAY_DISCUSSION_DONE,
            "speeches": speeches,
            "public_events": [
                *state["public_events"],
                public_event(state, f"第 {state['day']} 天发言结束。", Phase.DAY_DISCUSSION),
            ],
        }

    if next_speaker.is_human:
        payload = interrupt(
            {
                "kind": "speech",
                "message": "轮到你白天发言。",
                "speaker_id": next_speaker.id,
                "speaker_name": next_speaker.name,
                "candidates": [],
            }
        )
        content = str(payload.get("content", "")).strip() or "我先听大家发言。"
        speeches.append(SpeechRecord(day=state["day"], phase=Phase.DAY_DISCUSSION, speaker_id=next_speaker.id, content=content))
    else:
        agents = create_role_agents(llm, game_state)
        speeches.append(agents[next_speaker.id].speak(game_state).record)

    return {
        "phase": Phase.DAY_DISCUSSION,
        "stage": Stage.DAY_DISCUSSION,
        "speeches": speeches,
        "public_events": [
            *state["public_events"],
            public_event(state, f"{next_speaker.name}已完成发言。", Phase.DAY_DISCUSSION),
        ],
    }


def _enter_day_vote(state: GraphState) -> dict[str, Any]:
    return {
        "phase": Phase.DAY_VOTE,
        "stage": Stage.DAY_VOTE,
        "public_events": [
            *state["public_events"],
            public_event(state, f"第 {state['day']} 天投票开始。", Phase.DAY_VOTE),
        ],
    }


def _day_vote(state: GraphState, llm: BaseChatModel) -> dict[str, Any]:
    game_state = graph_state_to_game_state({**state, "phase": Phase.DAY_VOTE, "stage": Stage.DAY_VOTE})
    votes = list(state["votes"])
    next_voter = _next_vote_voter(state, game_state)

    if next_voter is not None:
        candidates = [player for player in living_players(game_state) if player.id != next_voter.id]
        if next_voter.is_human:
            payload = interrupt(
                {
                    "kind": "vote",
                    "message": "请选择你要投票放逐的玩家。",
                    "voter_id": next_voter.id,
                    "voter_name": next_voter.name,
                    "candidates": [_candidate(player) for player in candidates],
                }
            )
            target_id = _valid_target(payload, candidates)
            votes.append(VoteRecord(day=state["day"], voter_id=next_voter.id, target_id=target_id, reason="Human vote."))
        else:
            agents = create_role_agents(llm, game_state)
            votes.append(agents[next_voter.id].vote(game_state).record)

        voter = next_voter
        target = get_player(game_state, votes[-1].target_id)
        return {
            "phase": Phase.DAY_VOTE,
            "stage": Stage.DAY_VOTE,
            "votes": votes,
            "public_events": [
                *state["public_events"],
                public_event(state, f"{voter.name}投票给{target.name}。", Phase.DAY_VOTE),
            ],
        }

    today_votes = [vote for vote in votes if vote.day == state["day"]]
    executed_id = Counter(vote.target_id for vote in today_votes).most_common(1)[0][0]
    players = set_players_alive(state["players"], {executed_id})
    executed = get_player(game_state, executed_id)
    events = [
        *state["public_events"],
        public_event(state, f"{executed.name}被放逐出局。", Phase.DAY_VOTE),
    ]

    if executed.role == Role.HUNTER:
        return {
            "players": players,
            "phase": Phase.DAY_VOTE,
            "stage": Stage.HUNTER_SHOT,
            "day": state["day"],
            "night": state["night"],
            "votes": votes,
            "winner": None,
            "pending_wolf_target_id": None,
            "pending_witch_save_id": None,
            "pending_witch_poison_id": None,
            "pending_hunter_id": executed.id,
            "pending_hunter_return_stage": Stage.DAY_VOTE_RESULT,
            "public_events": [
                *events,
                public_event(state, f"{executed.name} 死亡，身份为猎人，可以发动技能。", Phase.DAY_VOTE),
            ],
        }

    next_state = {**state, "players": players}
    winner = _winner(next_state)

    if winner:
        return {
            "players": players,
            "phase": Phase.GAME_OVER,
            "stage": Stage.DAY_VOTE_RESULT,
            "day": state["day"],
            "night": state["night"],
            "votes": votes,
            "winner": winner.value,
            "pending_wolf_target_id": None,
            "pending_witch_save_id": None,
            "pending_witch_poison_id": None,
            "pending_hunter_id": None,
            "pending_hunter_return_stage": None,
            "public_events": [*events, public_event(state, _winner_text(winner), Phase.GAME_OVER)],
        }

    return {
        "players": players,
        "phase": Phase.DAY_VOTE,
        "stage": Stage.DAY_VOTE_RESULT,
        "day": state["day"],
        "night": state["night"],
        "votes": votes,
        "pending_wolf_target_id": None,
        "pending_witch_save_id": None,
        "pending_witch_poison_id": None,
        "pending_hunter_id": None,
        "pending_hunter_return_stage": None,
        "public_events": events,
    }


def _enter_next_round(state: GraphState) -> dict[str, Any]:
    next_day_state = {
        **state,
        "day": state["day"] + 1,
    }
    night_progress = _enter_night(next_day_state)
    return {
        "players": state["players"],
        "votes": state["votes"],
        "day": next_day_state["day"],
        "phase": night_progress["phase"],
        "stage": night_progress["stage"],
        "night": night_progress["night"],
        "pending_wolf_target_id": night_progress["pending_wolf_target_id"],
        "pending_witch_save_id": night_progress["pending_witch_save_id"],
        "pending_witch_poison_id": night_progress["pending_witch_poison_id"],
        "public_events": night_progress["public_events"],
    }


def _winner(state: GraphState) -> Optional[Camp]:
    wolves = len([player for player in state["players"] if player.is_alive and player.role == Role.WEREWOLF])
    good = len([player for player in state["players"] if player.is_alive and player.role != Role.WEREWOLF])
    if wolves == 0:
        return Camp.GOOD
    if good <= wolves:
        return Camp.WEREWOLF
    return None


def _dead_hunter(players: list[Player], dead_player_ids: list[str]) -> Optional[Player]:
    return next((player for player in players if player.id in dead_player_ids and player.role == Role.HUNTER), None)


def _choose_ai_hunter_target(llm: BaseChatModel, game_state, hunter: Player, candidates: list[Player]) -> str:
    agents = create_role_agents(llm, game_state)
    try:
        return agents[hunter.id].choose_hunter_shot(game_state, [player.id for player in candidates]).target_id
    except Exception:
        wolf = next((player for player in candidates if player.role == Role.WEREWOLF), None)
        return (wolf or candidates[0]).id


def _first_alive_player(players: list[Player], role: Role) -> Optional[Player]:
    return next((player for player in players if player.is_alive and player.role == role), None)


def _discussion_order(state: GraphState) -> list[Player]:
    game_state = graph_state_to_game_state(state)
    return sorted(living_players(game_state), key=lambda player: int(player.id))


def _vote_order(state: GraphState) -> list[Player]:
    game_state = graph_state_to_game_state(state)
    return sorted(living_players(game_state), key=lambda player: int(player.id))


def _next_discussion_speaker(state: GraphState, game_state) -> Optional[Player]:
    spoken_ids = {
        record.speaker_id
        for record in state["speeches"]
        if record.day == state["day"] and record.phase == Phase.DAY_DISCUSSION
    }
    for player in _discussion_order(state):
        if player.id not in spoken_ids:
            return player
    return None


def _next_vote_voter(state: GraphState, game_state) -> Optional[Player]:
    voted_ids = {
        record.voter_id
        for record in state["votes"]
        if record.day == state["day"]
    }
    for player in _vote_order(state):
        if player.id not in voted_ids:
            return player
    return None


def _candidate(player: Player) -> dict[str, Any]:
    return {"id": player.id, "name": player.name}


def _valid_target(payload: Any, candidates: list[Player]) -> str:
    candidate_ids = {player.id for player in candidates}
    target_id = payload.get("target_id") if isinstance(payload, dict) else None
    if target_id in candidate_ids:
        return target_id
    return candidates[0].id


def _optional_target(target_id: Any, candidates: list[Player]) -> Optional[str]:
    candidate_ids = {player.id for player in candidates}
    return target_id if isinstance(target_id, str) and target_id in candidate_ids else None


def _has_speech_today(state: Any, player_id: str) -> bool:
    return any(record.day == state["day"] and record.speaker_id == player_id for record in state["speeches"])


def _has_vote_today(state: Any, player_id: str) -> bool:
    return any(record.day == state["day"] and record.voter_id == player_id for record in state["votes"])


def _night_result_text(game_state, dead_ids: list[str]) -> str:
    if not dead_ids:
        return "夜晚结束，无人死亡。"
    names = "、".join(get_player(game_state, player_id).name for player_id in dead_ids)
    return f"夜晚结束，死亡玩家：{names}。"


def _winner_text(winner: Camp) -> str:
    return "狼人阵营获胜。" if winner == Camp.WEREWOLF else "好人阵营获胜。"
