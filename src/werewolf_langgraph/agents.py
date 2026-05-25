from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from .state import (
    Camp,
    GameState,
    Phase,
    Player,
    Role,
    SeerCheck,
    SpeechRecord,
    VoteRecord,
    alive_player_ids,
    get_player,
    living_players,
)


@dataclass(frozen=True)
class SpeechDecision:
    record: SpeechRecord


@dataclass(frozen=True)
class VoteDecision:
    record: VoteRecord


@dataclass(frozen=True)
class WolfKillDecision:
    actor_id: str
    target_id: str
    reason: str


@dataclass(frozen=True)
class SeerDecision:
    check: SeerCheck
    reason: str


@dataclass(frozen=True)
class WitchDecision:
    witch_id: str
    save_target_id: Optional[str]
    poison_target_id: Optional[str]
    reason: str


@dataclass(frozen=True)
class HunterShotDecision:
    hunter_id: str
    target_id: str
    reason: str


def _extract_json(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            return {}
        try:
            value = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}

    if isinstance(value, dict):
        return value
    return {}


def _pick_valid_id(value: Any, candidates: list[str]) -> str:
    if isinstance(value, str) and value in candidates:
        return value
    return candidates[0]


def _optional_valid_id(value: Any, candidates: list[str]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str) and value in candidates:
        return value
    return None


def _public_summary(state: GameState) -> str:
    rows = []
    for player in state.players:
        status = "alive" if player.is_alive else "dead"
        rows.append(f"{player.id}: {player.name} ({status})")
    return "\n".join(rows)


def _recent_public_events(state: GameState, limit: int = 12) -> str:
    events = state.public_events[-limit:]
    if not events:
        return "No public events yet."
    return "\n".join(f"Day {event.day} {event.phase.value}: {event.content}" for event in events)


def _player_label(state: GameState, player_id: str) -> str:
    try:
        player = get_player(state, player_id)
    except KeyError:
        return f"{player_id}号"
    return f"{player.id}号 {player.name}"


def _alive_players_list(state: GameState) -> str:
    players = [_player_label(state, player.id) for player in living_players(state)]
    return "、".join(players) if players else "无"


def _last_night_dead(state: GameState) -> str:
    if not state.night_actions:
        return "无"
    latest = max(state.night_actions, key=lambda action: action.night)
    if not latest.dead_player_ids:
        return "无人死亡"
    return "、".join(_player_label(state, player_id) for player_id in latest.dead_player_ids)


def _history_speeches_this_round(state: GameState) -> str:
    records = [
        record
        for record in state.speeches
        if record.day == state.day and record.phase == Phase.DAY_DISCUSSION
    ]
    if not records:
        return "暂无发言。"
    return "\n".join(f"{_player_label(state, record.speaker_id)}：{record.content}" for record in records)


def _all_speeches_history(state: GameState) -> str:
    if not state.speeches:
        return "暂无发言。"
    return "\n".join(
        f"第{record.day}天 {_player_label(state, record.speaker_id)}：{record.content}"
        for record in state.speeches
    )


def _wolf_teammates(player: Player, state: GameState) -> str:
    teammates = [
        _player_label(state, teammate.id)
        for teammate in state.players
        if teammate.role == Role.WEREWOLF and teammate.id != player.id
    ]
    return "、".join(teammates) if teammates else "无"


def _seer_checks_context(player: Player, state: GameState) -> str:
    own_checks = [check for check in state.seer_checks if check.seer_id == player.id]
    if not own_checks:
        return "暂无查验记录。"
    lines = []
    for check in sorted(own_checks, key=lambda item: item.night):
        result = "查杀" if check.result_camp == Camp.WEREWOLF else "金水"
        lines.append(f"{check.night}夜查验{_player_label(state, check.target_id)}：{result}")
    return "；".join(lines)


def _witch_inventory_context(state: GameState) -> str:
    antidote = "可用" if state.witch_inventory.has_antidote else "已用"
    poison = "可用" if state.witch_inventory.has_poison else "已用"
    return f"解药：{antidote}；毒药：{poison}"


def _witch_actions_context(state: GameState) -> str:
    if not state.night_actions:
        return "暂无用药记录。"
    lines = []
    for action in sorted(state.night_actions, key=lambda item: item.night):
        wolf = f"狼人刀{_player_label(state, action.wolf_target_id)}" if action.wolf_target_id else "狼人未刀人"
        save = f"救{_player_label(state, action.saved_target_id)}" if action.saved_target_id else "未救人"
        poison = f"毒{_player_label(state, action.poison_target_id)}" if action.poison_target_id else "未毒人"
        dead = "、".join(_player_label(state, player_id) for player_id in action.dead_player_ids) if action.dead_player_ids else "无人死亡"
        lines.append(f"{action.night}夜：{wolf}；{save}；{poison}；{dead}")
    return "\n".join(lines)


def _private_context(player: Player, state: GameState) -> str:
    if player.role == Role.WEREWOLF:
        wolves = [p.name for p in state.players if p.role == Role.WEREWOLF]
        return "Your werewolf teammates: " + ", ".join(wolves)

    if player.role == Role.SEER:
        own_checks = [check for check in state.seer_checks if check.seer_id == player.id]
        if not own_checks:
            return "You have no seer checks yet."
        lines = []
        for check in own_checks:
            target = get_player(state, check.target_id)
            lines.append(f"{target.name}: {check.result_camp.value}")
        return "Your seer checks: " + "; ".join(lines)

    if player.role == Role.WITCH:
        antidote = "available" if state.witch_inventory.has_antidote else "used"
        poison = "available" if state.witch_inventory.has_poison else "used"
        return f"Witch inventory: antidote={antidote}, poison={poison}."

    return "You have no private night information."


def _anime_tone_for_player(player: Player) -> str:
    name = player.name
    if "蜡笔小新" in name:
        return (
            "你的发言语气参考“蜡笔小新”：天真、调皮、故意装傻，偶尔用小孩子式的歪逻辑吐槽别人。"
            "说话可以有点欠揍、有点奶声奶气，但不要直接复刻原作台词或固定口头禅。"
        )
    if "哆啦A梦" in name:
        return (
            "你的发言语气参考“哆啦A梦”：温和、可靠、像在帮大家解决问题，偶尔带一点无奈和操心。"
            "说话要有朋友感，喜欢把局势整理清楚，提醒大家不要被带偏。不要直接复刻原作台词或道具名梗。"
        )
    if "小猪佩奇" in name:
        return (
            "你的发言语气参考“小猪佩奇”：简单、直接、童真，句子不要太复杂，像小朋友认真参与讨论。"
            "可以带一点可爱、笃定和轻微重复，但不能幼稚到影响推理。不要直接复刻原作台词。"
        )
    if "懒羊羊" in name:
        return (
            "你的发言语气参考“懒羊羊”：懒散、怕麻烦、嘴上想躺平，但关键时刻会认真说出自己的判断。"
            "可以有一点抱怨、撒娇和不情愿的感觉，但最后必须给出明确怀疑对象和理由。不要直接复刻原作台词。"
        )
    if "猪猪侠" in name:
        return (
            "你的发言语气参考“猪猪侠”：热血、自信、有英雄感，喜欢站出来带队，语气积极但有点臭屁。"
            "发言要像在鼓舞大家一起找狼，敢点名、敢归票。不要直接复刻原作台词或固定口号。"
        )
    if "柯南" in name:
        return (
            "你的发言语气参考“柯南”：冷静、观察细节、推理感强，说话像在一步步拆解矛盾。"
            "要多使用“时间线、动机、发言漏洞、行为不一致”这类分析方式，语气克制但有压迫感。"
            "不要直接复刻原作台词或经典句式。"
        )
    return ""


def _speech_style_guidance(player: Player) -> str:
    tone = _anime_tone_for_player(player)
    if not tone:
        return ""
    return (
        "【语气附加规则】\n"
        "你可以借鉴玩家名字对应动漫角色的说话气质，但只能轻度模仿语气，不能照搬原作台词、固定口头禅或完整桥段。"
        "狼人杀判断优先，角色语气只作为表达风格，占比约 20%-30%。输出必须符合游戏身份和当前局势。\n"
        f"{tone}\n\n"
    )


def _daytime_prompt(player: Player, state: GameState) -> str:
    common = (
        f"- 你的座位号：{player.id}号\n"
        f"- 当前存活玩家：{_alive_players_list(state)}\n"
        f"- 昨夜死者（如有）：{_last_night_dead(state)}\n"
        "- 过往所有发言记录：\n"
        f"{_all_speeches_history(state)}\n"
        "- 本轮你发言前的玩家发言记录：\n"
        f"{_history_speeches_this_round(state)}"
    )

    if player.role == Role.WEREWOLF:
        return (
            "# 当前任务：白天发言阶段 (Daytime Discussion Phase)\n"
            "## 狼人专属白天发言提示词\n"
            f"{_speech_style_guidance(player)}"
            "【专属机密】你的真实身份是：狼人 (Werewolf)。你的目标是抗推好人，掩护队友，争取胜利。绝对不能暴露你的真实身份和AI属性。\n\n"
            "【当前战场状态输入】\n"
            f"- 你的座位号：{player.id}号\n"
            f"- 你的狼队友座位号：{_wolf_teammates(player, state)}\n"
            f"- 当前存活玩家：{_alive_players_list(state)}\n"
            f"- 昨夜死者（如有）：{_last_night_dead(state)}\n"
            "- 过往所有发言记录：\n"
            f"{_all_speeches_history(state)}\n"
            "- 本轮你发言前的玩家发言记录：\n"
            f"{_history_speeches_this_round(state)}\n\n"
            "【狼人白天专属战术规范】\n"
            "1. 明确战术路线：你在 thought 中必须先决定本局走悍跳预言家、深水隐狼或倒钩狼。\n"
            "2. 发言要求：发言必须带座位号，绝不使用客套话。根据场上发言制造矛盾、混淆视听；如果决定隐蔽，要显得找狼心切但又拿不准。\n"
            "3. 归票拉票：发言最后必须给出明确怀疑对象（非狼队友），并号召大家投票给他。\n\n"
            "请严格输出 JSON 对象，包含 thought 和 speech。speech 字数 150-300 字。"
        )

    if player.role == Role.SEER:
        return (
            "# 当前任务：白天发言阶段 (Daytime Discussion Phase)\n"
            "## 预言家专属白天发言提示词\n"
            f"{_speech_style_guidance(player)}"
            "【专属机密】你的真实身份是：预言家 (Seer)。你是好人的核心，必须把你的查验信息传递出去，并带领好人投票出狼人。绝对不能暴露你是AI。\n\n"
            "【当前战场状态输入】\n"
            f"- 你的座位号：{player.id}号\n"
            f"- 你的历史查验记录：{_seer_checks_context(player, state)}\n"
            f"{common}\n\n"
            "【预言家白天专属战术规范】\n"
            "1. 强势报查验：发言第一句话必须报出你昨晚查验的座位号和结果（查杀/金水）。绝不能退缩。\n"
            "2. 如果查验到狼人，必须强势号召全场今天出查杀；如果查验到好人，要拉拢金水站边。\n"
            "3. 如果场上有人悍跳预言家身份，必须拆穿他的漏洞，证明你才是真预言家。\n"
            "4. 拒绝废话，点名道姓安排今天的归票目标。\n\n"
            "请严格输出 JSON 对象，包含 thought 和 speech。speech 字数 150-300 字。"
        )

    if player.role == Role.WITCH:
        return (
            "# 当前任务：白天发言阶段 (Daytime Discussion Phase)\n"
            "## 女巫专属白天发言提示词\n"
            f"{_speech_style_guidance(player)}"
            "【专属机密】你的真实身份是：女巫 (Witch)。你手握生杀大权，是场上极其强大的神职。绝对不能暴露你是AI。\n\n"
            "【当前战场状态输入】\n"
            f"- 你的座位号：{player.id}号\n"
            f"- 你的药剂状态：{_witch_inventory_context(state)}\n"
            f"- 你的历史用药记录：{_witch_actions_context(state)}\n"
            f"{common}\n\n"
            "【女巫白天专属战术规范】\n"
            "1. 若双药还在或只用了第一晚解药，尽量隐藏身份，伪装成认真盘逻辑的平民。\n"
            "2. 若准备带队或被踩入狼坑，可以果断起跳女巫，强势报银水或毒人信息。\n"
            "3. 结合昨晚刀型和对跳预言家发言，判断谁是真预言家，并号召全场站边。\n\n"
            "请严格输出 JSON 对象，包含 thought 和 speech。speech 字数 150-300 字。"
        )

    return (
        "# 当前任务：白天发言阶段 (Daytime Discussion Phase)\n"
        "## 平民专属白天发言提示词\n"
        f"{_speech_style_guidance(player)}"
        "【专属机密】你的真实身份是：平民 (Villager)。你是好人阵营的基石，晚上没有视野，白天必须靠发言逻辑找出狼人。绝对不能暴露你是AI。\n\n"
        "【当前战场状态输入】\n"
        f"{common}\n\n"
        "【平民白天专属战术规范】\n"
        "1. 坚守闭眼视角：不能装作知道夜晚信息，避免视角过宽。\n"
        "2. 必须对比场上起跳预言家，明确表态目前倾向相信谁，并指出另一方漏洞。\n"
        "3. 点出狼坑，不能划水。点名发言不好的人并给出理由。\n"
        "4. 如果有人踩你是狼，要强烈反击并表水求生，最后呼吁投给你怀疑的对象。\n\n"
        "请严格输出 JSON 对象，包含 thought 和 speech。speech 字数 150-300 字。"
    )


def _vote_prompt(player: Player, state: GameState) -> str:
    common = (
        f"- 你的座位号：{player.id}号\n"
        f"- 当前存活玩家：{_alive_players_list(state)}\n"
        f"- 昨夜死者（如有）：{_last_night_dead(state)}\n"
        "- 过往所有发言记录：\n"
        f"{_all_speeches_history(state)}\n"
        "- 本轮你投票前的玩家发言记录：\n"
        f"{_history_speeches_this_round(state)}"
    )

    if player.role == Role.WEREWOLF:
        return (
            "# 当前任务：白天投票阶段 (Daytime Voting Phase)\n"
            "## 狼人专属投票提示词\n"
            "【专属机密】你的真实身份是：狼人 (Werewolf)。你要根据整轮发言和自己的身份，投出最有利于狼队的人。绝对不能暴露你的真实身份和AI属性。\n\n"
            "【当前战场状态输入】\n"
            f"- 你的座位号：{player.id}号\n"
            f"- 你的狼队友座位号：{_wolf_teammates(player, state)}\n"
            f"{common}\n\n"
            "【狼人投票规范】\n"
            "1. 结合全场发言，优先投掉真预言家、强势带队好人或明显站边你不利的人。\n"
            "2. 如果狼队友已经暴露，视局势决定是否倒钩或切割，但不要让自己显得过于明显。\n"
            "3. 你必须给出明确投票对象和简短理由。"
        )

    if player.role == Role.SEER:
        return (
            "# 当前任务：白天投票阶段 (Daytime Voting Phase)\n"
            "## 预言家专属投票提示词\n"
            "【专属机密】你的真实身份是：预言家 (Seer)。你要根据整轮发言、查验记录和自己的身份投出狼人。绝对不能暴露你是AI。\n\n"
            "【当前战场状态输入】\n"
            f"- 你的座位号：{player.id}号\n"
            f"- 你的历史查验记录：{_seer_checks_context(player, state)}\n"
            f"{common}\n\n"
            "【预言家投票规范】\n"
            "1. 如果有对跳或查杀目标，优先投狼。\n"
            "2. 结合前面所有人的发言，判断谁在带节奏、谁在保人、谁的逻辑最像狼。\n"
            "3. 你必须给出明确投票对象和简短理由。"
        )

    if player.role == Role.WITCH:
        return (
            "# 当前任务：白天投票阶段 (Daytime Voting Phase)\n"
            "## 女巫专属投票提示词\n"
            "【专属机密】你的真实身份是：女巫 (Witch)。你要结合整轮发言和你的药剂状态投票。绝对不能暴露你是AI。\n\n"
            "【当前战场状态输入】\n"
            f"- 你的座位号：{player.id}号\n"
            f"- 你的药剂状态：{_witch_inventory_context(state)}\n"
            f"- 你的历史用药记录：{_witch_actions_context(state)}\n"
            f"{common}\n\n"
            "【女巫投票规范】\n"
            "1. 结合昨夜刀型、发言站边和场上节奏，判断谁更像狼。\n"
            "2. 如果你已经暴露，投票时要兼顾自保和带队。\n"
            "3. 你必须给出明确投票对象和简短理由。"
        )

    return (
        "# 当前任务：白天投票阶段 (Daytime Voting Phase)\n"
        "## 平民专属投票提示词\n"
        "【专属机密】你的真实身份是：平民 (Villager)。你没有夜间视野，只能根据整轮发言和自己的判断投票。绝对不能暴露你是AI。\n\n"
        "【当前战场状态输入】\n"
        f"{common}\n\n"
        "【平民投票规范】\n"
        "1. 根据前面所有人的发言，找出谁的逻辑最差、谁在偷换概念、谁在带节奏。\n"
        "2. 结合自己的身份做出最合理的站边和投票。\n"
        "3. 你必须给出明确投票对象和简短理由。"
    )


class RoleAgent:
    def __init__(self, llm: BaseChatModel, player: Player):
        self.llm = llm
        self.player = player

    def _ask_json(self, task: str, schema_hint: str) -> dict[str, Any]:
        system_prompt = (
            "You are a Werewolf party game player. "
            "Use only the information provided to you. "
            "Never reveal hidden information unless it is strategically useful. "
            "Never mention that you are an AI, model, or assistant. "
            "Return strict JSON only. Do not include markdown."
        )
        user_prompt = (
            f"Player id: {self.player.id}\n"
            f"Player name: {self.player.name}\n"
            f"Secret role: {self.player.role.value}\n\n"
            f"{task}\n\n"
            f"Required JSON schema: {schema_hint}"
        )
        response = self.llm.invoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]
        )
        return _extract_json(str(response.content))

    def speak(self, state: GameState) -> SpeechDecision:
        data = self._ask_json(
            _daytime_prompt(self.player, state),
            '{"thought": "Chinese private analysis", "speech": "Chinese speech"}',
        )
        speech = data.get("speech")
        if not isinstance(speech, str) or not speech.strip():
            speech = "我先整理一下场上的发言，再看谁的逻辑更站不住脚。"

        return SpeechDecision(
            record=SpeechRecord(
                day=state.day,
                phase=state.phase,
                speaker_id=self.player.id,
                content=speech.strip(),
            )
        )

    def vote(self, state: GameState) -> VoteDecision:
        candidates = [player_id for player_id in alive_player_ids(state) if player_id != self.player.id]
        if not candidates:
            raise ValueError("No valid vote candidates.")

        task = (
            f"{_vote_prompt(self.player, state)}\n\n"
            f"Candidate ids: {', '.join(candidates)}\n"
            "请选择一位最应该被放逐的玩家。"
        )
        data = self._ask_json(task, '{"target_id": "player id", "reason": "short Chinese reason"}')
        target_id = _pick_valid_id(data.get("target_id"), candidates)
        reason = data.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            reason = "Based on the current discussion."

        return VoteDecision(
            record=VoteRecord(
                day=state.day,
                voter_id=self.player.id,
                target_id=target_id,
                reason=reason.strip(),
            )
        )

    def choose_wolf_kill(self, state: GameState) -> WolfKillDecision:
        if self.player.role != Role.WEREWOLF:
            raise ValueError("Only werewolves can choose a night kill.")

        candidates = [player.id for player in living_players(state) if player.role != Role.WEREWOLF]
        if not candidates:
            raise ValueError("No valid wolf kill candidates.")

        task = (
            "It is werewolf night action. Choose one non-werewolf alive player to kill.\n"
            f"Candidate ids: {', '.join(candidates)}\n"
            f"Public players:\n{_public_summary(state)}\n\n"
            f"Recent public events:\n{_recent_public_events(state)}\n\n"
            f"Private context:\n{_private_context(self.player, state)}"
        )
        data = self._ask_json(task, '{"target_id": "player id", "reason": "short Chinese reason"}')
        target_id = _pick_valid_id(data.get("target_id"), candidates)
        reason = data.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            reason = "Targeting a player who may have a strong village role."

        return WolfKillDecision(actor_id=self.player.id, target_id=target_id, reason=reason.strip())

    def choose_seer_check(self, state: GameState) -> SeerDecision:
        if self.player.role != Role.SEER:
            raise ValueError("Only the seer can check a player.")

        checked_ids = {check.target_id for check in state.seer_checks if check.seer_id == self.player.id}
        candidates = [
            player.id
            for player in living_players(state)
            if player.id != self.player.id and player.id not in checked_ids
        ]
        if not candidates:
            candidates = [player.id for player in living_players(state) if player.id != self.player.id]
        if not candidates:
            raise ValueError("No valid seer check candidates.")

        task = (
            "It is seer night action. Choose one alive player to inspect.\n"
            f"Candidate ids: {', '.join(candidates)}\n"
            f"Public players:\n{_public_summary(state)}\n\n"
            f"Private context:\n{_private_context(self.player, state)}"
        )
        data = self._ask_json(task, '{"target_id": "player id", "reason": "short Chinese reason"}')
        target_id = _pick_valid_id(data.get("target_id"), candidates)
        target = get_player(state, target_id)
        reason = data.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            reason = "Checking a player with high information value."

        return SeerDecision(
            check=SeerCheck(
                night=state.night,
                seer_id=self.player.id,
                target_id=target_id,
                result_camp=target.camp,
            ),
            reason=reason.strip(),
        )

    def choose_witch_action(self, state: GameState, wolf_target_id: Optional[str]) -> WitchDecision:
        if self.player.role != Role.WITCH:
            raise ValueError("Only the witch can use potions.")

        poison_candidates = [player.id for player in living_players(state) if player.id != self.player.id]
        save_candidates = [wolf_target_id] if wolf_target_id and state.witch_inventory.has_antidote else []

        task = (
            "It is witch night action. Decide whether to save the wolf target and whether to poison someone.\n"
            f"Wolf target id: {wolf_target_id}\n"
            f"Can save ids: {', '.join(save_candidates) if save_candidates else 'none'}\n"
            f"Can poison ids: {', '.join(poison_candidates) if state.witch_inventory.has_poison else 'none'}\n"
            f"Public players:\n{_public_summary(state)}\n\n"
            f"Private context:\n{_private_context(self.player, state)}"
        )
        data = self._ask_json(
            task,
            '{"save_target_id": "player id or null", "poison_target_id": "player id or null", "reason": "short Chinese reason"}',
        )

        save_target_id = _optional_valid_id(data.get("save_target_id"), save_candidates)
        poison_pool = poison_candidates if state.witch_inventory.has_poison else []
        poison_target_id = _optional_valid_id(data.get("poison_target_id"), poison_pool)
        reason = data.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            reason = "Using potions cautiously based on night information."

        return WitchDecision(
            witch_id=self.player.id,
            save_target_id=save_target_id,
            poison_target_id=poison_target_id,
            reason=reason.strip(),
        )

    def choose_hunter_shot(self, state: GameState, candidates: list[str]) -> HunterShotDecision:
        if self.player.role != Role.HUNTER:
            raise ValueError("Only the hunter can fire a hunter shot.")
        if not candidates:
            raise ValueError("No valid hunter shot candidates.")

        task = (
            "You died as the hunter. Choose one alive player to take down with your final shot.\n"
            f"Candidate ids: {', '.join(candidates)}\n"
            f"Public players:\n{_public_summary(state)}\n\n"
            f"Recent public events:\n{_recent_public_events(state)}"
        )
        data = self._ask_json(task, '{"target_id": "player id", "reason": "short Chinese reason"}')
        target_id = _pick_valid_id(data.get("target_id"), candidates)
        reason = data.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            reason = "Taking the most suspicious player down with the final hunter shot."
        return HunterShotDecision(hunter_id=self.player.id, target_id=target_id, reason=reason.strip())


def create_role_agents(llm: BaseChatModel, state: GameState) -> dict[str, RoleAgent]:
    return {player.id: RoleAgent(llm, player) for player in state.players if not player.is_human}
