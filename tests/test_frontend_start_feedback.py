from pathlib import Path


APP_JS = Path(__file__).resolve().parents[1] / "src" / "werewolf_langgraph" / "static" / "app.js"


def _css_block(source, selector, start=0):
    selector_index = source.index(selector, start)
    block_start = source.index("{", selector_index) + 1
    block_end = source.index("}", block_start)
    return source[block_start:block_end]


def test_start_game_shows_feedback_before_network_request():
    source = APP_JS.read_text(encoding="utf-8")
    start_index = source.index("async function startGame()")
    feedback_index = source.index('setStartButtonState("starting")', start_index)
    fetch_index = source.index('fetch("/api/rooms"', start_index)

    assert feedback_index < fetch_index


def test_start_game_restores_button_when_room_creation_fails():
    source = APP_JS.read_text(encoding="utf-8")
    start_index = source.index("async function startGame()")
    catch_index = source.index("catch (error)", start_index)
    restore_index = source.index('setStartButtonState("idle")', catch_index)

    assert catch_index < restore_index


def test_start_game_error_is_visible_inside_name_modal():
    source = APP_JS.read_text(encoding="utf-8")
    index_html = APP_JS.with_name("index.html").read_text(encoding="utf-8")

    assert 'id="nameStatus"' in index_html
    assert 'showNameStatus(message);' in source
    assert 'showNameStatus("");' in source


def test_start_game_busy_copy_says_prepare_game():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'button.textContent = "开始游戏";' in source
    assert '"正在准备游戏，请稍候..."' in source
    assert '"正在创建房间..."' not in source


def test_start_game_does_not_show_role_modal_automatically():
    source = APP_JS.read_text(encoding="utf-8")
    start_index = source.index("async function startGame()")
    next_function_index = source.index("async function nextStage()", start_index)
    start_game_source = source[start_index:next_function_index]

    assert "showRoleModal()" not in start_game_source


def test_single_player_start_sets_local_player_id_for_auto_advance():
    source = APP_JS.read_text(encoding="utf-8")
    start_index = source.index("async function startGame()")
    next_function_index = source.index("async function nextStage()", start_index)
    start_game_source = source[start_index:next_function_index]

    assert "localPlayerId = nextRoom.human_id;" in start_game_source


def test_setup_button_asks_player_to_view_role_first():
    index_html = APP_JS.with_name("index.html").read_text(encoding="utf-8")

    assert '<button id="confirmRoleButton" class="primary-action" type="button">查看身份</button>' in index_html


def test_night_start_auto_advances_without_manual_wolf_button():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'const autoStages = ["night_start", "wolf_action", "seer_action", "witch_action", "hunter_shot"];' in source
    assert 'setVisible("#advanceButton", false);' in source
    assert "let autoAdvanceStage = null;" in source
    assert "if (autoAdvanceTimer && autoAdvanceStage === currentStage) return;" in source


def test_human_night_role_still_advances_until_waiting_for_input():
    source = APP_JS.read_text(encoding="utf-8")

    assert "room.waiting_for" in source
    assert 'currentStage === "wolf_action" && room.human_role === "werewolf"' not in source
    assert 'currentStage === "seer_action" && room.human_role === "seer"' not in source
    assert 'currentStage === "witch_action" && room.human_role === "witch"' not in source


def test_action_choices_use_in_page_confirmation():
    source = APP_JS.read_text(encoding="utf-8")

    assert "window.confirm" not in source
    assert "renderChoiceConfirmation" in source
    assert 'confirmChoiceButton' in source
    assert 'cancelChoiceButton' in source


def test_witch_action_uses_two_page_steps():
    source = APP_JS.read_text(encoding="utf-8")

    assert "let witchActionFlow = null;" in source
    assert "ensureWitchActionFlow(wait)" in source
    assert "buildWitchSavePrompt(flow)" in source
    assert "buildWitchPoisonPrompt(flow)" in source
    assert "submitWitchAction(flow, poisonTargetId)" in source
    assert 'chooseWithConfirm("witch_action"' not in source


def test_hunter_role_and_shot_choice_rendering_exist():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'hunter: "猎人"' in source
    assert 'hunter: "好人阵营"' in source
    assert 'wait.kind === "hunter_shot"' in source
    assert 'renderTargetChoices("#hunterAction", "hunter_shot", wait.candidates, "hunterAction")' in source
    assert 'kind === "hunter_shot"' in source


def test_witch_action_prompts_show_victim_and_poison_choice():
    source = APP_JS.read_text(encoding="utf-8")

    assert "今晚狼人击中了" in source
    assert "解药阶段" in source
    assert "毒药阶段" in source
    assert "不救，继续下一步" in source
    assert "不下毒" in source


def test_seer_reveal_waits_for_acknowledgement():
    source = APP_JS.read_text(encoding="utf-8")
    start_index = source.index("function renderSeerReveal()")
    next_function_index = source.index("function renderPlayers(", start_index)
    seer_reveal_source = source[start_index:next_function_index]
    apply_start = source.index("async function applyRoom(nextRoom, actionKind = null)")
    apply_end = source.index("async function transitionToStage(stage, renderFn)", apply_start)
    apply_room_source = source[apply_start:apply_end]
    index_html = APP_JS.with_name("index.html").read_text(encoding="utf-8")

    assert "pendingSeerReveal" in source
    assert "renderSeerReveal" in source
    assert "seerRevealModal" in source
    assert "seerAckButton" in source
    assert "modal.classList.remove(\"hidden\")" in seer_reveal_source
    assert "modal.classList.add(\"hidden\")" in seer_reveal_source
    assert "查验结果：" in seer_reveal_source
    assert "我已知晓" in index_html
    assert "scheduleNightAutoAdvance();" in seer_reveal_source
    assert "const shouldShowSeerReveal =" in apply_room_source
    assert "resetLocalStageState({ keepSeerReveal: shouldShowSeerReveal });" in apply_room_source
    assert "if (!options.keepSeerReveal) {" in apply_room_source


def test_set_busy_restores_modal_interaction():
    source = APP_JS.read_text(encoding="utf-8")
    start_index = source.index("function setBusy(isBusy)")
    next_function_index = source.index("function setStartButtonState", start_index)
    set_busy_source = source[start_index:next_function_index]

    assert 'element.disabled = true;' in set_busy_source
    assert 'element.disabled = false;' in set_busy_source


def test_start_game_uses_random_seat():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'human_seat: pickHumanSeat()' in source
    assert 'Math.floor(Math.random() * 9) + 1' in source


def test_start_game_uses_custom_human_name_input():
    source = APP_JS.read_text(encoding="utf-8")
    index_html = APP_JS.with_name("index.html").read_text(encoding="utf-8")
    poster_controls = index_html[
        index_html.index('<div class="poster-controls">') : index_html.index('<section id="gameScreen"', index_html.index('<div class="poster-controls">'))
    ]

    assert 'id="humanNameInput"' in index_html
    assert 'id="nameModal"' in index_html
    assert 'id="confirmNameButton"' in index_html
    assert 'id="cancelNameButton"' in index_html
    assert 'id="humanNameInput"' not in poster_controls
    assert 'document.querySelector("#humanNameInput").value.trim()' in source
    assert "const humanName = customHumanName || DEFAULT_HUMAN_NAME;" in source
    assert "human_name: humanName" in source


def test_start_button_opens_name_modal_before_room_creation():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function showNameModal()" in source
    assert "function hideNameModal()" in source
    assert 'document.querySelector("#startButton").addEventListener("click", showNameModal);' in source
    assert 'document.querySelector("#confirmNameButton").addEventListener("click", startGame);' in source
    assert 'document.querySelector("#cancelNameButton").addEventListener("click", hideNameModal);' in source
    assert 'document.querySelector("#humanNameInput").focus();' in source


def test_human_role_stays_hidden_until_viewed():
    source = APP_JS.read_text(encoding="utf-8")

    assert "let roleRevealed = false;" in source
    assert "roleRevealed = true;" in source
    assert 'if (player.is_human && !roleRevealed) return "pending";' in source
    assert 'pending: "身份待查看",' in source


def test_wolf_teammates_stay_hidden_until_role_is_confirmed():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function visiblePlayerRole(player)" in source
    assert 'if (player.is_human && !roleRevealed) return "pending";' in source
    assert 'if (!roleRevealed && player.role === "werewolf" && player.id !== room.human_id) return "hidden";' in source
    assert "const roleLabel = roleNames[visiblePlayerRole(player)] || visiblePlayerRole(player);" in source


def test_day_discussion_advances_live_instead_of_replay_after_completion():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function scheduleDiscussionAutoAdvance()" in source
    assert "function renderDiscussionFeedProgress()" in source
    assert "playSequentialDiscussion" not in source
    assert 'if (currentStage === "day_discussion") {' in source
    assert "scheduleDiscussionAutoAdvance();" in source
    assert "let discussionAdvanceKey = null;" in source
    assert "if (discussionAdvanceTimer && discussionAdvanceKey === advanceKey) return;" in source


def test_first_discussion_wait_shows_thinking_prompt():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function renderFirstDiscussionWaitPrompt()" in source
    assert "请认真思考自己接下来的发言" in source
    assert "renderFirstDiscussionWaitPrompt();" in source


def test_discussion_done_button_is_not_blocked_by_old_playback_flag():
    source = APP_JS.read_text(encoding="utf-8")
    apply_start = source.index("async function applyRoom(nextRoom, actionKind = null)")
    apply_end = source.index("async function transitionToStage(stage, renderFn)", apply_start)
    apply_room_source = source[apply_start:apply_end]

    assert "clearTimeout(discussionAdvanceTimer);" in apply_room_source
    assert "discussionPlaybackRunning = false;" in apply_room_source
    assert 'setVisible("#discussionNextButton", displayStage === "day_discussion_done");' in source


def test_remote_stage_change_clears_local_pending_state_like_local_apply():
    source = APP_JS.read_text(encoding="utf-8")
    remote_start = source.index("async function applyRemoteRoom(nextRoom)")
    remote_end = source.index("async function fetchRoomState()", remote_start)
    apply_remote_source = source[remote_start:remote_end]

    assert "const previousStage = currentStage;" in apply_remote_source
    assert "resetLocalStageState();" in apply_remote_source
    assert "if (previousStage !== currentStage)" in apply_remote_source


def test_human_speech_finish_can_submit_empty_text():
    source = APP_JS.read_text(encoding="utf-8")
    start_index = source.index("async function submitSpeech()")
    next_function_index = source.index("async function submitVote()", start_index)
    submit_speech_source = source[start_index:next_function_index]

    assert "if (!content) return;" not in submit_speech_source
    assert 'await submitAction({ kind: "speech", content });' in submit_speech_source


def test_vote_controls_only_show_when_waiting_for_human_vote():
    source = APP_JS.read_text(encoding="utf-8")
    render_start = source.index("function renderPanels(displayStage = currentStage)")
    render_end = source.index("document.querySelector(\"#wolfStatus\").textContent", render_start)
    render_source = source[render_start:render_end]

    assert 'const showVoteControls = waitingKind === "vote" && isLocalPendingActor();' in render_source
    assert 'setVisible("#voteTarget", showVoteControls);' in render_source
    assert 'setVisible("#voteButton", showVoteControls);' in render_source


def test_vote_target_selection_survives_room_rerender():
    source = APP_JS.read_text(encoding="utf-8")
    start_index = source.index("function renderVoteTargets()")
    end_index = source.index("function renderEvents()", start_index)
    render_vote_targets_source = source[start_index:end_index]

    assert "const selectedTargetId = select.value;" in render_vote_targets_source
    assert "if (selectedTargetId && select.querySelector" in render_vote_targets_source
    assert "select.value = selectedTargetId;" in render_vote_targets_source


def test_vote_feed_and_auto_advance_exist():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function scheduleVoteAutoAdvance()" in source
    assert "function renderVoteFeedProgress()" in source
    assert "function appendVoteBubble(vote, voter, target)" in source
    assert 'if (currentStage === "day_vote") {' in source
    assert "scheduleVoteAutoAdvance();" in source
    assert "let voteAdvanceKey = null;" in source
    assert "if (voteAdvanceTimer && voteAdvanceKey === advanceKey) return;" in source


def test_vote_result_screen_and_continue_button_exist():
    source = APP_JS.read_text(encoding="utf-8")
    index_html = APP_JS.with_name("index.html").read_text(encoding="utf-8")

    assert 'day_vote_result: ["放逐结果", "查看投票结局", "phaseVoteResult"]' in source
    assert 'setVisible("#voteResultNextButton", displayStage === "day_vote_result");' in source
    assert 'const voteResultNextButton = document.querySelector("#voteResultNextButton");' in source
    assert 'if (voteResultNextButton) voteResultNextButton.disabled = !canContinue;' in source
    assert 'voteResultSummary' in source
    assert 'document.querySelector("#voteResultNextButton")?.addEventListener("click", nextStage);' in source
    assert 'id="phaseVoteResult"' in index_html
    assert 'id="voteResultSummary"' in index_html
    assert 'id="voteResultNextButton"' in index_html


def test_role_reveal_rendering_does_not_require_vote_result_dom_to_exist():
    source = APP_JS.read_text(encoding="utf-8")
    render_start = source.index("function renderPanels(displayStage = currentStage)")
    render_end = source.index("document.querySelector(\"#wolfStatus\").textContent", render_start)
    render_source = source[render_start:render_end]
    index_html = APP_JS.with_name("index.html").read_text(encoding="utf-8")

    assert 'document.querySelector("#voteResultNextButton").disabled' not in render_source
    assert 'document.querySelector("#voteResultNextButton")?.addEventListener("click", nextStage);' in source
    assert "final-result-step" in index_html



def test_final_result_step_shows_night_result_before_game_over():
    source = APP_JS.read_text(encoding="utf-8")
    index_html = APP_JS.with_name("index.html").read_text(encoding="utf-8")

    assert 'night_result: ["\u591c\u665a\u7ed3\u679c", "\u67e5\u770b\u672c\u591c\u7ed3\u5c40", "phaseNightResult"]' in source
    assert 'setVisible("#nightResultNextButton", displayStage === "night_result");' in source
    assert 'document.querySelector("#nightResultNextButton")?.addEventListener("click", nextStage);' in source
    assert 'const canAdvanceWinnerResult = room && room.winner && (currentStage === "night_result" || currentStage === "day_vote_result");' in source
    assert 'id="phaseNightResult"' in index_html
    assert 'id="nightResultSummary"' in index_html
    assert 'id="nightResultNextButton"' in index_html

def test_nine_player_layout_and_candidate_grid():
    source = APP_JS.read_text(encoding="utf-8")
    css = APP_JS.with_name("styles.css").read_text(encoding="utf-8")

    assert "repeat(9, minmax(0, 1fr))" in css
    assert 'const DEFAULT_HUMAN_NAME = "打摆子的家伙";' in source


def test_cartoon_werewolf_opening_uses_poster_artwork():
    index_html = APP_JS.with_name("index.html").read_text(encoding="utf-8")
    css = APP_JS.with_name("styles.css").read_text(encoding="utf-8")

    assert "<title>卡通狼人杀</title>" in index_html
    assert 'src="/static/assets/uploaded-opening-poster-mobile.webp"' in index_html
    assert 'class="poster-start-button"' in index_html
    assert '<button id="startButton" class="poster-start-button" type="button"' in index_html
    assert ".poster-start-button:hover" in css
    assert "transform: scale(1.08);" in css
    for character_name in [
        "蜡笔小新",
        "哆啦A梦",
        "奶龙",
        "海绵宝宝",
        "猪猪侠",
        "懒羊羊",
        "小猪佩奇",
        "柯南",
    ]:
        assert character_name in index_html

    assert ".opening-poster" in css
    assert ".poster-start-button" in css
    assert "cartoon-werewolf-opening-wide.png" not in css


def test_opening_poster_waits_for_image_load_before_showing_controls():
    source = APP_JS.read_text(encoding="utf-8")
    index_html = APP_JS.with_name("index.html").read_text(encoding="utf-8")
    css = APP_JS.with_name("styles.css").read_text(encoding="utf-8")

    assert 'rel="preload"' in index_html
    assert 'href="/static/assets/uploaded-opening-poster-mobile.webp"' in index_html
    assert 'id="openingPoster"' in index_html
    assert 'class="start-content poster-loading"' in index_html
    assert 'id="posterLoading"' in index_html
    assert "function markPosterLoaded()" in source
    assert 'document.querySelector("#openingPoster")' in source
    assert 'poster.complete' in source
    assert 'poster.addEventListener("load", markPosterLoaded, { once: true });' in source
    assert '.start-content.poster-loading .opening-poster' in css
    assert '.start-content.poster-loaded .poster-controls' in css
    assert '.poster-loading-panel' in css


def test_game_screen_uses_separate_cartoon_background():
    css = APP_JS.with_name("styles.css").read_text(encoding="utf-8")
    asset = APP_JS.with_name("assets") / "game-mobile-character-background.webp"

    assert asset.exists()
    assert ".game-screen::before" in css
    assert 'url("/static/assets/game-mobile-character-background.webp")' in css
    assert "filter: saturate(1.08);" in css
    assert "background: rgba(13, 17, 26, 0.52);" in css
    assert "backdrop-filter: blur(6px);" in css
    assert "rgba(4, 7, 14, 0.72)" not in css


def test_player_avatar_mapping_and_rendering_exist():
    source = APP_JS.read_text(encoding="utf-8")
    css = APP_JS.with_name("styles.css").read_text(encoding="utf-8")

    for character_name in [
        "柯南",
        "哆啦A梦",
        "蜡笔小新",
        "海绵宝宝",
        "小猪佩奇",
        "猪猪侠",
        "懒羊羊",
        "奶龙",
    ]:
        assert character_name in source

    assert "const playerAvatarMap = {" in source
    assert "function avatarForPlayer(player)" in source
    assert 'const humanAvatar = "/static/assets/avatars/human.webp";' in source
    assert "if (player.avatar_id) return avatarImage(player.avatar_id);" in source
    assert "if (player.is_human) return humanAvatar;" not in source
    assert '"加菲猫": "/static/assets/avatars/garfield.webp",' in source
    assert 'avatar.className = "player-avatar";' in source
    assert "avatar.alt = `${player.name}头像`;" in source
    assert ".player-avatar" in css


def test_player_avatar_assets_exist():
    avatar_dir = APP_JS.with_name("assets") / "avatars"

    for filename in [
        "conan.webp",
        "doraemon.webp",
        "shinchan.webp",
        "spongebob.webp",
        "peppa.webp",
        "ggbond.webp",
        "lazy-yangyang.webp",
        "nailong.webp",
        "human.webp",
        "garfield.webp",
    ]:
        assert (avatar_dir / filename).exists()


def test_multiplayer_avatar_choice_replaces_default_human_with_garfield():
    source = APP_JS.read_text(encoding="utf-8")

    assert '{ id: "garfield", name: "加菲猫" }' in source
    assert '{ id: "human", name: "默认玩家" }' not in source
    assert 'if (avatar.id === "garfield") return "/static/assets/avatars/garfield.webp";' in source
    assert 'const humanAvatar = "/static/assets/avatars/human.webp";' in source


def test_mobile_lobby_avatar_grid_and_waiting_room_helpers_exist():
    source = APP_JS.read_text(encoding="utf-8")

    assert "let selectedAvatarId = avatarChoices[0].id;" in source
    assert "function renderAvatarChoices" in source
    assert "avatar-choice-button" in source
    assert 'loading="lazy" decoding="async" width="42" height="42"' in source
    assert 'loading="lazy" decoding="async" width="40" height="40"' in source
    assert 'avatar.width = 76;' in source
    assert 'avatar.height = 76;' in source
    assert 'document.querySelector("#avatarChoiceGrid")' in source
    assert 'document.querySelector("#copyRoomCodeButton")?.addEventListener("click", copyWaitingRoomCode);' in source
    assert "async function copyWaitingRoomCode()" in source
    assert 'document.querySelector("#waitingRoomCode").textContent = room.room_id;' in source
    assert 'document.querySelector("#waitingHostStatus").textContent' in source
    assert "waiting-seat-avatar" in source


def test_multiplayer_session_helpers_exist():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'const LOCAL_SESSION_KEY = "werewolf.roomSession";' in source
    assert "function saveLocalSession(nextRoom)" in source
    assert "function restoreLocalSession()" in source
    assert "function clearLocalSession()" in source
    assert "localStorage.setItem(LOCAL_SESSION_KEY" in source
    assert "localStorage.getItem(LOCAL_SESSION_KEY)" in source
    assert "localStorage.removeItem(LOCAL_SESSION_KEY)" in source
    assert "new URLSearchParams(window.location.search)" in source


def test_room_request_saves_session_and_starts_polling():
    source = APP_JS.read_text(encoding="utf-8")
    start_index = source.index("async function roomRequest(url, payload)")
    end_index = source.index("function renderWaitingRoom()", start_index)
    room_request_source = source[start_index:end_index]

    assert "saveLocalSession(nextRoom);" in room_request_source
    assert "startRoomPolling();" in room_request_source


def test_room_polling_uses_viewer_specific_room_endpoint():
    source = APP_JS.read_text(encoding="utf-8")

    assert "let roomPollTimer = null;" in source
    assert "const ROOM_POLL_INTERVAL_MS = 1500;" in source
    assert "function startRoomPolling()" in source
    assert "function stopRoomPolling()" in source
    assert "async function fetchRoomState()" in source
    assert "setInterval(fetchRoomState, ROOM_POLL_INTERVAL_MS)" in source
    assert "encodeURIComponent(localPlayerId)" in source
    assert "fetch(`/api/rooms/${room.room_id}?player_id=${viewerId}`)" in source
    assert "if (roomRequestInFlight || requestId !== roomPollRequestId) return;" in source


def test_waiting_poll_switches_to_game_after_host_start():
    source = APP_JS.read_text(encoding="utf-8")
    start_index = source.index("async function applyRemoteRoom(nextRoom)")
    end_index = source.index("async function fetchRoomState()", start_index)
    apply_remote_source = source[start_index:end_index]

    assert 'if (nextRoom.status === "waiting") {' in apply_remote_source
    assert 'showScreen("waiting");' in apply_remote_source
    assert 'if (nextRoom.status === "playing") {' in apply_remote_source
    assert 'showScreen("game");' in apply_remote_source
    assert "renderRoom();" in apply_remote_source
    assert "scheduleCurrentAutoAdvance();" in apply_remote_source


def test_remote_poll_only_schedules_current_auto_advance():
    source = APP_JS.read_text(encoding="utf-8")
    start_index = source.index("async function applyRemoteRoom(nextRoom)")
    end_index = source.index("async function fetchRoomState()", start_index)
    apply_remote_source = source[start_index:end_index]

    assert "function scheduleCurrentAutoAdvance()" in source
    assert "scheduleNightAutoAdvance();\n    scheduleDiscussionAutoAdvance();\n    scheduleVoteAutoAdvance();" not in apply_remote_source


def test_room_posts_invalidate_in_flight_poll_responses():
    source = APP_JS.read_text(encoding="utf-8")
    next_start = source.index("async function nextStage()")
    next_end = source.index("async function submitAction(payload)", next_start)
    next_stage_source = source[next_start:next_end]
    submit_start = next_end
    submit_end = source.index("async function applyRoom", submit_start)
    submit_action_source = source[submit_start:submit_end]

    assert "roomPollRequestId += 1;" in next_stage_source
    assert "roomPollRequestId += 1;" in submit_action_source


def test_only_local_player_is_marked_you():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'player.id === room.human_id ? "（你）" : ""' in source
    assert 'player.is_human ? "（你）" : ""' not in source


def test_pending_actions_are_gated_to_local_actor():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function isLocalPendingActor(wait = room?.waiting_for)" in source
    assert "function pendingActorLabel(wait = room?.waiting_for)" in source
    assert "const isMine = isLocalPendingActor(wait);" in source
    assert 'showWaitingStatus(isMine ? "" : `等待 ${pendingActorLabel(wait)} 操作...`);' in source
    assert 'const showVoteControls = waitingKind === "vote" && isLocalPendingActor();' in source


def test_waiting_status_clears_when_no_action_is_pending():
    source = APP_JS.read_text(encoding="utf-8")
    start_index = source.index("function renderWaitingAction()")
    end_index = source.index("function clearActionBoxes()", start_index)
    render_waiting_source = source[start_index:end_index]

    assert 'if (!room.waiting_for) {' in render_waiting_source
    assert 'showWaitingStatus("");' in render_waiting_source


def test_desktop_table_shell_structure_exists():
    index_html = APP_JS.with_name("index.html").read_text(encoding="utf-8")

    assert 'class="desktop-table-shell"' in index_html
    assert 'id="desktopPlayerRail"' in index_html
    assert 'id="desktopActionColumn"' in index_html
    assert 'id="desktopInfoRail"' in index_html
    assert "desktop-top-bar" in index_html
    assert "desktop-action-dock" in index_html


def test_desktop_table_css_uses_three_column_grid():
    css = APP_JS.with_name("styles.css").read_text(encoding="utf-8")

    assert ".desktop-table-shell" in css
    assert "grid-template-areas:" in css
    assert '"top top top"' in css
    assert '"players stage log"' in css
    assert "grid-area: players;" in css
    assert "grid-area: stage;" in css
    assert "grid-area: log;" in css
    assert "@media (max-width: 1179px)" in css


def test_desktop_player_roster_is_compact_sidebar():
    css = APP_JS.with_name("styles.css").read_text(encoding="utf-8")

    assert "#desktopPlayerRail .players" in css
    assert "grid-template-columns: 1fr;" in css
    assert "#desktopPlayerRail .player" in css
    assert "grid-template-columns: 56px minmax(0, 1fr);" in css
    assert "min-height: 72px;" in css


def test_desktop_columns_scroll_without_clipping_content():
    css = APP_JS.with_name("styles.css").read_text(encoding="utf-8")

    assert "grid-template-rows: auto minmax(0, 1fr);" in css
    assert "height: calc(100vh - 36px);" in css
    assert ".desktop-action-dock" in css
    assert "overflow: auto;" in css
    assert ".phase-panel.active" in css
    assert "min-height: 100%;" in css


def test_mobile_game_phase_panel_is_translucent_enough_for_character_background():
    css = APP_JS.with_name("styles.css").read_text(encoding="utf-8")

    assert "@media (max-width: 680px)" in css
    assert ".phase-stage," in css
    assert "background: rgba(13, 17, 26, 0.34);" in css
    assert "backdrop-filter: blur(2px);" in css


def test_mobile_game_player_roster_is_translucent_enough_for_character_background():
    css = APP_JS.with_name("styles.css").read_text(encoding="utf-8")

    assert "@media (max-width: 680px)" in css
    assert ".table-area {" in css
    assert ".player {" in css
    assert "background: rgba(13, 17, 26, 0.28);" in css
    assert "background: rgba(255, 255, 255, 0.035);" in css


def test_mobile_game_background_does_not_resize_during_browser_chrome_scroll():
    css = APP_JS.with_name("styles.css").read_text(encoding="utf-8")
    mobile_media_index = css.index("@media (max-width: 680px)")
    mobile_background = _css_block(css, ".game-screen::before", mobile_media_index)

    assert "position: fixed;" in mobile_background
    assert "position: absolute;" not in mobile_background
    assert "height: 100%;" not in mobile_background
    assert "min-height: 100svh;" in mobile_background
    assert "background-size: auto 100svh;" in mobile_background


def test_mobile_game_layout_allows_setup_action_to_be_reached():
    css = APP_JS.with_name("styles.css").read_text(encoding="utf-8")

    assert "@media (max-width: 680px)" in css
    assert '"top"' in css
    assert '"stage"' in css
    assert '"players"' in css
    assert '"log"' in css
    assert ".desktop-table-shell {" in css
    assert "height: auto;" in css
    assert "min-height: 0;" in css
    assert ".desktop-action-dock {" in css
    assert "min-height: auto;" in css
    assert ".phase-panel.active {" in css
    assert "align-content: start;" in css


def test_mobile_player_cards_keep_chinese_names_horizontal():
    source = APP_JS.read_text(encoding="utf-8")
    css = APP_JS.with_name("styles.css").read_text(encoding="utf-8")

    assert 'name.className = "player-name";' in source
    assert 'meta.className = "player-meta";' in source
    assert ".player-name" in css
    assert ".player-meta" in css
    assert "white-space: nowrap;" in css
    assert "text-overflow: ellipsis;" in css
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in css
    assert "#desktopPlayerRail .players {" in css
    assert "#desktopPlayerRail .player {" in css
    assert "grid-template-columns: initial;" in css
    assert "justify-items: center;" in css


def test_desktop_visible_chinese_text_is_not_mojibake():
    index_html = APP_JS.with_name("index.html").read_text(encoding="utf-8")

    assert "<title>卡通狼人杀</title>" in index_html
    assert "联机大厅" in index_html
    assert "创建房间" in index_html
    assert "等待房间" in index_html
    assert "公开记录" in index_html
    assert "查看身份" in index_html
    assert "鍗" not in index_html
