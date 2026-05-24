from pathlib import Path


APP_JS = Path(__file__).resolve().parents[1] / "src" / "werewolf_langgraph" / "static" / "app.js"


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


def test_setup_button_asks_player_to_view_role_first():
    index_html = APP_JS.with_name("index.html").read_text(encoding="utf-8")

    assert '<button id="confirmRoleButton" class="primary-action" type="button">查看身份</button>' in index_html


def test_night_start_auto_advances_without_manual_wolf_button():
    source = APP_JS.read_text(encoding="utf-8")

    assert 'const autoStages = ["night_start", "wolf_action", "seer_action", "witch_action", "hunter_shot"];' in source
    assert 'setVisible("#advanceButton", false);' in source


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
    assert "if (!shouldShowSeerReveal) {" in apply_room_source


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
    assert 'player.is_human && !roleRevealed ? "身份待查看" : roleNames[player.role] || player.role' in source


def test_day_discussion_advances_live_instead_of_replay_after_completion():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function scheduleDiscussionAutoAdvance()" in source
    assert "function renderDiscussionFeedProgress()" in source
    assert "playSequentialDiscussion" not in source
    assert 'if (currentStage === "day_discussion") {' in source
    assert "scheduleDiscussionAutoAdvance();" in source


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

    assert 'const showVoteControls = waitingKind === "vote";' in render_source
    assert 'setVisible("#voteTarget", showVoteControls);' in render_source
    assert 'setVisible("#voteButton", showVoteControls);' in render_source


def test_vote_feed_and_auto_advance_exist():
    source = APP_JS.read_text(encoding="utf-8")

    assert "function scheduleVoteAutoAdvance()" in source
    assert "function renderVoteFeedProgress()" in source
    assert "function appendVoteBubble(vote, voter, target)" in source
    assert 'if (currentStage === "day_vote") {' in source
    assert "scheduleVoteAutoAdvance();" in source


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
    assert 'src="/static/assets/uploaded-opening-poster.webp"' in index_html
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


def test_game_screen_uses_separate_cartoon_background():
    css = APP_JS.with_name("styles.css").read_text(encoding="utf-8")
    asset = APP_JS.with_name("assets") / "game-cartoon-background.webp"

    assert asset.exists()
    assert ".game-screen::before" in css
    assert 'url("/static/assets/game-cartoon-background.webp")' in css
    assert "filter: saturate(1.08);" in css
    assert "background: rgba(13, 17, 26, 0.52);" in css
    assert "backdrop-filter: blur(6px);" in css
    assert "rgba(4, 7, 14, 0.72)" not in css
