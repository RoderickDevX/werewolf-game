from werewolf_langgraph.state import Player, Role, create_initial_state, state_to_graph_state
from werewolf_langgraph.web import Room, _serialize_room


def test_serialize_room_reveals_wolf_teammates_roles_to_a_werewolf_human():
    players = [
        Player(id="1", name="alpha", role=Role.WEREWOLF, is_human=True),
        Player(id="2", name="bravo", role=Role.WEREWOLF),
        Player(id="3", name="charlie", role=Role.VILLAGER),
    ]
    state = state_to_graph_state(create_initial_state(players))
    room = Room("room1", state, human_id="1", graph=None)

    payload = _serialize_room(room)
    roles_by_id = {player["id"]: player["role"] for player in payload["players"]}

    assert roles_by_id["1"] == "werewolf"
    assert roles_by_id["2"] == "werewolf"
    assert roles_by_id["3"] == "hidden"


def test_serialize_room_exposes_wolf_teammates_to_a_werewolf_human():
    players = [
        Player(id="1", name="甲", role=Role.WEREWOLF, is_human=True),
        Player(id="2", name="乙", role=Role.WEREWOLF),
        Player(id="3", name="丙", role=Role.VILLAGER),
    ]
    state = state_to_graph_state(create_initial_state(players))
    room = Room("room1", state, human_id="1", graph=None)

    payload = _serialize_room(room)

    assert payload["wolf_teammates"] == [{"id": "2", "name": "乙"}]
