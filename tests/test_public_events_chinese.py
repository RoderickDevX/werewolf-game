from werewolf_langgraph.game_graph import (
    _day_discussion,
    _day_vote,
    _enter_day_discussion,
    _enter_day_vote,
    _enter_night,
    _night_result_text,
    _resolve_hunter_shot,
    _resolve_night,
)
from werewolf_langgraph.state import (
    GameState,
    Phase,
    Player,
    Role,
    SpeechRecord,
    Stage,
    VoteRecord,
    create_initial_state,
    state_to_graph_state,
)


def test_initial_public_event_is_chinese():
    game_state = create_initial_state([Player(id="1", name="一号", role=Role.VILLAGER)])

    assert game_state.public_events[0].content == "游戏已创建，等待第一个夜晚开始。"


def test_night_public_events_are_chinese():
    game_state = GameState(
        players=[
            Player(id="1", name="一号", role=Role.WEREWOLF),
            Player(id="2", name="二号", role=Role.VILLAGER),
            Player(id="3", name="三号", role=Role.VILLAGER),
        ],
        phase=Phase.SETUP,
        stage=Stage.SETUP,
    )
    state = state_to_graph_state(game_state)

    night = _enter_night(state)
    result = _resolve_night({**state, "phase": Phase.NIGHT, "stage": Stage.WITCH_ACTION, "night": 1})

    assert night["public_events"][-1].content == "第 1 夜开始。"
    assert result["public_events"][-1].content == "夜晚结束，无人死亡。"


def test_day_public_events_are_chinese():
    game_state = GameState(
        players=[Player(id="1", name="一号", role=Role.WEREWOLF), Player(id="2", name="二号", role=Role.VILLAGER)],
        phase=Phase.DAY_VOTE,
        stage=Stage.DAY_VOTE,
        day=1,
        night=1,
        speeches=[
            SpeechRecord(day=1, phase=Phase.DAY_DISCUSSION, speaker_id="1", content="我发言完毕。"),
            SpeechRecord(day=1, phase=Phase.DAY_DISCUSSION, speaker_id="2", content="我也发言完毕。"),
        ],
        votes=[VoteRecord(day=1, voter_id="1", target_id="2"), VoteRecord(day=1, voter_id="2", target_id="1")],
    )
    state = state_to_graph_state(game_state)

    discussion = _enter_day_discussion(state)
    discussion_done = _day_discussion({**state, "phase": Phase.DAY_DISCUSSION, "stage": Stage.DAY_DISCUSSION}, llm=None)
    vote = _enter_day_vote(state)
    vote_result = _day_vote(state, llm=None)

    assert discussion["public_events"][-1].content == "第 1 天发言开始。"
    assert discussion_done["public_events"][-1].content == "第 1 天发言结束。"
    assert vote["public_events"][-1].content == "第 1 天投票开始。"
    assert vote_result["public_events"][-2].content == "二号被放逐出局。"
    assert vote_result["public_events"][-1].content == "狼人阵营获胜。"


def test_hunter_and_night_result_public_events_are_chinese():
    game_state = GameState(
        players=[
            Player(id="1", name="狼人", role=Role.WEREWOLF),
            Player(id="2", name="猎人", role=Role.HUNTER, is_alive=False),
            Player(id="3", name="村民", role=Role.VILLAGER),
        ],
        phase=Phase.NIGHT,
        stage=Stage.HUNTER_SHOT,
        day=1,
        night=1,
        pending_hunter_id="2",
        pending_hunter_return_stage=Stage.NIGHT_RESULT,
    )
    state = state_to_graph_state(game_state)

    shot = _resolve_hunter_shot(state, "1")

    assert _night_result_text(game_state, ["3"]) == "夜晚结束，死亡玩家：村民。"
    assert shot["public_events"][-2].content == "猎人开枪带走了狼人。"
    assert shot["public_events"][-1].content == "好人阵营获胜。"
