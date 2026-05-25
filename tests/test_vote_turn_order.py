from werewolf_langgraph.game_graph import _day_vote, _enter_next_round, _next_vote_voter, _resolve_hunter_shot, _resolve_night, _vote_order
from werewolf_langgraph.state import GameState, Phase, Player, Role, Stage, VoteRecord, state_to_graph_state


def test_vote_order_follows_seat_number_and_skips_dead_players():
    game_state = GameState(
        players=[
            Player(id="1", name="1", role=Role.VILLAGER),
            Player(id="2", name="2", role=Role.VILLAGER, is_alive=False),
            Player(id="3", name="3", role=Role.WEREWOLF),
            Player(id="4", name="4", role=Role.SEER),
        ],
        phase=Phase.DAY_VOTE,
        stage=Stage.DAY_VOTE,
        day=1,
    )
    state = state_to_graph_state(game_state)

    assert [player.id for player in _vote_order(state)] == ["1", "3", "4"]


def test_next_vote_voter_advances_after_each_cast_vote():
    game_state = GameState(
        players=[
            Player(id="1", name="1", role=Role.VILLAGER),
            Player(id="2", name="2", role=Role.VILLAGER),
            Player(id="3", name="3", role=Role.WEREWOLF),
        ],
        phase=Phase.DAY_VOTE,
        stage=Stage.DAY_VOTE,
        day=1,
        votes=[VoteRecord(day=1, voter_id="1", target_id="3")],
    )
    state = state_to_graph_state(game_state)

    assert _next_vote_voter(state, None).id == "2"


def test_next_vote_voter_returns_none_after_everyone_voted():
    game_state = GameState(
        players=[
            Player(id="1", name="1", role=Role.VILLAGER),
            Player(id="2", name="2", role=Role.VILLAGER),
        ],
        phase=Phase.DAY_VOTE,
        stage=Stage.DAY_VOTE,
        day=1,
        votes=[
            VoteRecord(day=1, voter_id="1", target_id="2"),
            VoteRecord(day=1, voter_id="2", target_id="1"),
        ],
    )
    state = state_to_graph_state(game_state)

    assert _next_vote_voter(state, None) is None


def test_day_vote_enters_result_screen_before_next_round():
    game_state = GameState(
        players=[
            Player(id="1", name="1", role=Role.VILLAGER),
            Player(id="2", name="2", role=Role.VILLAGER),
            Player(id="3", name="3", role=Role.WEREWOLF),
            Player(id="4", name="4", role=Role.WEREWOLF),
        ],
        phase=Phase.DAY_VOTE,
        stage=Stage.DAY_VOTE,
        day=1,
        night=1,
        votes=[
            VoteRecord(day=1, voter_id="1", target_id="4"),
            VoteRecord(day=1, voter_id="2", target_id="4"),
            VoteRecord(day=1, voter_id="3", target_id="1"),
            VoteRecord(day=1, voter_id="4", target_id="1"),
        ],
    )
    state = state_to_graph_state(game_state)

    result = _day_vote(state, llm=None)

    assert result["stage"] == Stage.DAY_VOTE_RESULT
    assert result["phase"] == Phase.DAY_VOTE
    assert result["day"] == 1
    assert result["night"] == 1
    assert any(event.phase == Phase.DAY_VOTE and event.content == "4被放逐出局。" for event in result["public_events"])



def test_day_vote_winner_still_enters_vote_result_screen_before_game_over():
    game_state = GameState(
        players=[
            Player(id="1", name="1", role=Role.WEREWOLF),
            Player(id="2", name="2", role=Role.VILLAGER),
        ],
        phase=Phase.DAY_VOTE,
        stage=Stage.DAY_VOTE,
        day=1,
        night=1,
        votes=[
            VoteRecord(day=1, voter_id="1", target_id="2"),
            VoteRecord(day=1, voter_id="2", target_id="1"),
        ],
    )
    state = state_to_graph_state(game_state)

    result = _day_vote(state, llm=None)

    assert result["stage"] == Stage.DAY_VOTE_RESULT
    assert result["phase"] == Phase.GAME_OVER
    assert result["winner"] == "werewolf"
    assert any(event.phase == Phase.DAY_VOTE and event.content == "2被放逐出局。" for event in result["public_events"])


def test_night_winner_enters_night_result_screen_before_game_over():
    game_state = GameState(
        players=[
            Player(id="1", name="1", role=Role.WEREWOLF),
            Player(id="2", name="2", role=Role.VILLAGER),
        ],
        phase=Phase.NIGHT,
        stage=Stage.WITCH_ACTION,
        day=1,
        night=1,
        pending_wolf_target_id="2",
    )
    state = state_to_graph_state(game_state)

    result = _resolve_night(state)

    assert result["stage"] == Stage.NIGHT_RESULT
    assert result["phase"] == Phase.GAME_OVER
    assert result["winner"] == "werewolf"


def test_human_hunter_killed_at_night_shoots_before_winner():
    game_state = GameState(
        players=[
            Player(id="1", name="wolf", role=Role.WEREWOLF),
            Player(id="2", name="hunter", role=Role.HUNTER, is_human=True),
            Player(id="3", name="villager", role=Role.VILLAGER),
        ],
        phase=Phase.NIGHT,
        stage=Stage.WITCH_ACTION,
        day=1,
        night=1,
        pending_wolf_target_id="2",
    )
    state = state_to_graph_state(game_state)

    result = _resolve_night(state)

    assert result["stage"] == Stage.HUNTER_SHOT
    assert result["pending_hunter_id"] == "2"
    assert result["pending_hunter_return_stage"] == Stage.NIGHT_RESULT
    assert result["winner"] is None
    assert "身份为猎人" in result["public_events"][-1].content


def test_hunter_shot_can_kill_final_wolf_and_make_good_win():
    game_state = GameState(
        players=[
            Player(id="1", name="wolf", role=Role.WEREWOLF),
            Player(id="2", name="hunter", role=Role.HUNTER, is_alive=False),
            Player(id="3", name="villager", role=Role.VILLAGER),
        ],
        phase=Phase.NIGHT,
        stage=Stage.HUNTER_SHOT,
        day=1,
        night=1,
        pending_hunter_id="2",
        pending_hunter_return_stage=Stage.NIGHT_RESULT,
    )
    state = state_to_graph_state(game_state)

    result = _resolve_hunter_shot(state, "1")

    assert result["players"][0].is_alive is False
    assert result["stage"] == Stage.NIGHT_RESULT
    assert result["phase"] == Phase.GAME_OVER
    assert result["winner"] == "good"


def test_enter_next_round_advances_day_and_night():
    game_state = GameState(
        players=[
            Player(id="1", name="1", role=Role.VILLAGER),
            Player(id="2", name="2", role=Role.VILLAGER),
        ],
        phase=Phase.DAY_VOTE,
        stage=Stage.DAY_VOTE_RESULT,
        day=1,
        night=1,
    )
    state = state_to_graph_state(game_state)

    result = _enter_next_round(state)

    assert result["stage"] == Stage.NIGHT_START
    assert result["phase"] == Phase.NIGHT
    assert result["day"] == 2
    assert result["night"] == 2
