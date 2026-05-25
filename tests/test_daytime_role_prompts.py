from types import SimpleNamespace

from werewolf_langgraph.agents import RoleAgent
from werewolf_langgraph.state import (
    Camp,
    GameState,
    NightAction,
    Phase,
    Player,
    Role,
    SeerCheck,
    SpeechRecord,
    WitchInventory,
)


class CapturingLLM:
    def __init__(self):
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return SimpleNamespace(content='{"thought": "test", "speech": "测试发言"}')


class EmptySpeechLLM:
    def invoke(self, messages):
        return SimpleNamespace(content='{"thought": "test", "speech": ""}')


def _prompt_from(agent, state):
    agent.speak(state)
    return agent.llm.messages[1].content


def _vote_prompt_from(agent, state):
    agent.vote(state)
    return agent.llm.messages[1].content


def test_werewolf_day_prompt_uses_previous_speeches_and_teammates():
    wolf = Player(id="1", name="一号", role=Role.WEREWOLF)
    teammate = Player(id="2", name="二号", role=Role.WEREWOLF)
    villager = Player(id="3", name="三号", role=Role.VILLAGER)
    state = GameState(
        players=[wolf, teammate, villager],
        phase=Phase.DAY_DISCUSSION,
        day=1,
        speeches=[
            SpeechRecord(day=1, phase=Phase.DAY_DISCUSSION, speaker_id="3", content="我是预言家，昨晚查杀1号。")
        ],
    )
    llm = CapturingLLM()

    prompt = _prompt_from(RoleAgent(llm, wolf), state)

    assert "狼人专属白天发言提示词" in prompt
    assert "你的狼队友座位号：2号" in prompt
    assert "3号 三号：我是预言家，昨晚查杀1号。" in prompt
    assert "归票拉票" in prompt


def test_seer_and_witch_day_prompts_include_private_context_without_global_role_leak():
    seer = Player(id="1", name="一号", role=Role.SEER)
    wolf = Player(id="2", name="二号", role=Role.WEREWOLF)
    witch = Player(id="3", name="三号", role=Role.WITCH)
    state = GameState(
        players=[seer, wolf, witch],
        phase=Phase.DAY_DISCUSSION,
        day=2,
        night=1,
        speeches=[
            SpeechRecord(day=2, phase=Phase.DAY_DISCUSSION, speaker_id="2", content="我觉得1号不像真预言家。")
        ],
        seer_checks=[SeerCheck(night=1, seer_id="1", target_id="2", result_camp=Camp.WEREWOLF)],
        night_actions=[NightAction(night=1, wolf_target_id="3", saved_target_id="3", dead_player_ids=())],
        witch_inventory=WitchInventory(has_antidote=False, has_poison=True),
    )

    seer_prompt = _prompt_from(RoleAgent(CapturingLLM(), seer), state)
    witch_prompt = _prompt_from(RoleAgent(CapturingLLM(), witch), state)

    assert "预言家专属白天发言提示词" in seer_prompt
    assert "1夜查验2号 二号：查杀" in seer_prompt
    assert "2号 二号：我觉得1号不像真预言家。" in seer_prompt
    assert "女巫专属白天发言提示词" in witch_prompt
    assert "解药：已用；毒药：可用" in witch_prompt
    assert "1夜：狼人刀3号 三号；救3号 三号；未毒人；无人死亡" in witch_prompt


def test_vote_prompt_uses_full_discussion_history_and_role_context():
    wolf = Player(id="1", name="一号", role=Role.WEREWOLF)
    seer = Player(id="2", name="二号", role=Role.SEER)
    villager = Player(id="3", name="三号", role=Role.VILLAGER)
    state = GameState(
        players=[wolf, seer, villager],
        phase=Phase.DAY_VOTE,
        day=1,
        speeches=[
            SpeechRecord(day=1, phase=Phase.DAY_DISCUSSION, speaker_id="2", content="我是预言家，1号查杀。"),
            SpeechRecord(day=1, phase=Phase.DAY_DISCUSSION, speaker_id="3", content="我觉得2号发言太像真预言家了。"),
        ],
        seer_checks=[SeerCheck(night=1, seer_id="2", target_id="1", result_camp=Camp.WEREWOLF)],
    )

    prompt = _vote_prompt_from(RoleAgent(CapturingLLM(), wolf), state)

    assert "白天投票阶段" in prompt
    assert "本轮你投票前的玩家发言记录" in prompt
    assert "2号 二号：我是预言家，1号查杀。" in prompt
    assert "3号 三号：我觉得2号发言太像真预言家了。" in prompt
    assert "你的狼队友座位号" in prompt


def test_day_two_prompt_includes_previous_round_speeches():
    villager = Player(id="1", name="一号", role=Role.VILLAGER)
    seer = Player(id="2", name="二号", role=Role.SEER)
    wolf = Player(id="3", name="三号", role=Role.WEREWOLF)
    state = GameState(
        players=[villager, seer, wolf],
        phase=Phase.DAY_DISCUSSION,
        day=2,
        speeches=[
            SpeechRecord(day=1, phase=Phase.DAY_DISCUSSION, speaker_id="2", content="我是预言家，1号金水。"),
            SpeechRecord(day=1, phase=Phase.DAY_DISCUSSION, speaker_id="3", content="我觉得2号像假跳。"),
            SpeechRecord(day=2, phase=Phase.DAY_DISCUSSION, speaker_id="1", content="我先听听大家怎么说。"),
        ],
    )

    prompt = _prompt_from(RoleAgent(CapturingLLM(), villager), state)

    assert "第1天 2号 二号：我是预言家，1号金水。" in prompt
    assert "第1天 3号 三号：我觉得2号像假跳。" in prompt
    assert "第2天 1号 一号：我先听听大家怎么说。" in prompt


def test_day_prompt_includes_anime_tone_from_player_name():
    conan = Player(id="7", name="柯南", role=Role.VILLAGER)
    state = GameState(players=[conan], phase=Phase.DAY_DISCUSSION, day=1)

    prompt = _prompt_from(RoleAgent(CapturingLLM(), conan), state)

    assert "【语气附加规则】" in prompt
    assert "你的发言语气参考“柯南”" in prompt
    assert "时间线、动机、发言漏洞、行为不一致" in prompt
    assert "狼人杀判断优先" in prompt


def test_empty_model_speech_uses_neutral_fallback():
    player = Player(id="1", name="一号", role=Role.VILLAGER)
    state = GameState(players=[player], phase=Phase.DAY_DISCUSSION, day=1)

    decision = RoleAgent(EmptySpeechLLM(), player).speak(state)

    assert decision.record.content == "我先整理一下场上的发言，再看谁的逻辑更站不住脚。"
    assert "不能一直过麦" not in decision.record.content
    assert "视角不自然" not in decision.record.content
