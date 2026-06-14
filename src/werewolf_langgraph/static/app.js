let room = null;
let localPlayerId = null;
let currentStage = "setup";
let renderedSpeechKeys = new Set();
let discussionPlaybackRunning = false;
let votePlaybackRunning = false;
let autoAdvanceTimer = null;
let autoAdvanceStage = null;
let discussionAdvanceTimer = null;
let discussionAdvanceKey = null;
let voteAdvanceTimer = null;
let voteAdvanceKey = null;
let roomPollTimer = null;
let roomPollRequestId = 0;
let roomRequestInFlight = false;
let roleRevealed = false;
let pendingChoice = null;
let pendingSeerReveal = null;
let witchActionFlow = null;

const LOCAL_SESSION_KEY = "werewolf.roomSession";
const ROOM_POLL_INTERVAL_MS = 1500;

const DEFAULT_HUMAN_NAME = "打摆子的家伙";
const avatarChoices = [
  { id: "shinchan", name: "蜡笔小新" },
  { id: "lazy-yangyang", name: "懒羊羊" },
  { id: "ggbond", name: "猪猪侠" },
  { id: "conan", name: "柯南" },
  { id: "doraemon", name: "哆啦 A 梦" },
  { id: "peppa", name: "小猪佩奇" },
  { id: "nailong", name: "奶龙" },
  { id: "spongebob", name: "海绵宝宝" },
  { id: "garfield", name: "加菲猫" },
];
let selectedAvatarId = avatarChoices[0].id;
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const roleNames = {
  werewolf: "狼人",
  seer: "预言家",
  witch: "女巫",
  hunter: "猎人",
  villager: "平民",
  hidden: "身份未知",
  pending: "身份待查看",
};

const campNames = {
  werewolf: "狼人阵营",
  seer: "好人阵营",
  witch: "好人阵营",
  hunter: "好人阵营",
  villager: "好人阵营",
};

const playerAvatarMap = {
  "柯南": "/static/assets/avatars/conan.webp",
  "哆啦A梦": "/static/assets/avatars/doraemon.webp",
  "蜡笔小新": "/static/assets/avatars/shinchan.webp",
  "海绵宝宝": "/static/assets/avatars/spongebob.webp",
  "小猪佩奇": "/static/assets/avatars/peppa.webp",
  "猪猪侠": "/static/assets/avatars/ggbond.webp",
  "懒羊羊": "/static/assets/avatars/lazy-yangyang.webp",
  "奶龙": "/static/assets/avatars/nailong.webp",
  "加菲猫": "/static/assets/avatars/garfield.webp",
};

const humanAvatar = "/static/assets/avatars/human.webp";

const stageCopy = {
  setup: ["准备", "等待夜幕降临", "phaseSetup"],
  night_start: ["夜晚", "天黑请闭眼", "phaseNight"],
  wolf_action: ["狼人行动", "狼人正在选择今晚的目标", "phaseWolf"],
  seer_action: ["预言家查验", "预言家正在查看一名玩家的身份", "phaseSeer"],
  witch_action: ["女巫用药", "女巫正在决定是否使用药剂", "phaseWitch"],
  hunter_shot: ["猎人开枪", "猎人正在选择带走一名玩家", "phaseNightResult"],
  dawn: ["天亮了", "清晨的钟声响起", "phaseDawn"],
  night_result: ["夜晚结果", "查看本夜结局", "phaseNightResult"],
  day_discussion: ["白天讨论", "轮流发言", "phaseDiscussion"],
  day_discussion_done: ["白天讨论", "轮流发言", "phaseDiscussion"],
  day_vote: ["投票环节", "选择你怀疑的人", "phaseVote"],
  day_vote_result: ["放逐结果", "查看投票结局", "phaseVoteResult"],
  game_over: ["胜负判定", "游戏结束", "phaseResult"],
};

function initializeLobby() {
  populateAvatarSelect("#createAvatarSelect");
  renderAvatarChoices();
  bindLobbyEvents();
  if (!restoreLocalSession()) {
    loadLobbyRooms();
  }
}

function bindLobbyEvents() {
  document.querySelector("#refreshRoomsButton")?.addEventListener("click", loadLobbyRooms);
  document.querySelector("#createRoomButton")?.addEventListener("click", createLobbyRoom);
  document.querySelector("#readyButton")?.addEventListener("click", toggleReady);
  document.querySelector("#startRoomButton")?.addEventListener("click", startWaitingRoom);
  document.querySelector("#copyRoomCodeButton")?.addEventListener("click", copyWaitingRoomCode);
  document.querySelector("#backToLobbyButton")?.addEventListener("click", () => {
    room = null;
    localPlayerId = null;
    clearLocalSession();
    stopRoomPolling();
    showScreen("lobby");
    loadLobbyRooms();
  });
}

function saveLocalSession(nextRoom) {
  if (!nextRoom?.room_id || !nextRoom?.human_id) return;
  localStorage.setItem(LOCAL_SESSION_KEY, JSON.stringify({ roomId: nextRoom.room_id, playerId: nextRoom.human_id }));
  const url = new URL(window.location.href);
  url.searchParams.set("room", nextRoom.room_id);
  window.history.replaceState({}, "", url);
}

function clearLocalSession() {
  localStorage.removeItem(LOCAL_SESSION_KEY);
  const url = new URL(window.location.href);
  url.searchParams.delete("room");
  window.history.replaceState({}, "", url);
}

function restoreLocalSession() {
  const params = new URLSearchParams(window.location.search);
  const roomIdFromUrl = params.get("room");
  const raw = localStorage.getItem(LOCAL_SESSION_KEY);
  if (!raw) return false;
  try {
    const saved = JSON.parse(raw);
    if (!saved?.roomId || !saved?.playerId) return false;
    if (roomIdFromUrl && roomIdFromUrl !== saved.roomId) return false;
    room = { room_id: saved.roomId };
    localPlayerId = saved.playerId;
    fetchRoomState();
    startRoomPolling();
    return true;
  } catch (error) {
    clearLocalSession();
    return false;
  }
}

function populateAvatarSelect(selector, available = avatarChoices) {
  const select = document.querySelector(selector);
  if (!select) return;
  select.innerHTML = "";
  const nextAvailable = available.length ? available : avatarChoices;
  if (!nextAvailable.some((avatar) => avatar.id === selectedAvatarId)) {
    selectedAvatarId = nextAvailable[0].id;
  }
  for (const avatar of nextAvailable) {
    const option = document.createElement("option");
    option.value = avatar.id;
    option.textContent = avatar.name;
    option.selected = avatar.id === selectedAvatarId;
    select.appendChild(option);
  }
  select.value = selectedAvatarId;
  select.addEventListener("change", () => {
    selectedAvatarId = select.value;
    renderAvatarChoices(nextAvailable);
  }, { once: true });
}

function renderAvatarChoices(available = avatarChoices) {
  const grid = document.querySelector("#avatarChoiceGrid");
  if (!grid) return;
  const nextAvailable = available.length ? available : avatarChoices;
  if (!nextAvailable.some((avatar) => avatar.id === selectedAvatarId)) {
    selectedAvatarId = nextAvailable[0].id;
  }
  grid.innerHTML = "";
  for (const avatar of nextAvailable) {
    const button = document.createElement("button");
    const isSelected = avatar.id === selectedAvatarId;
    button.className = `avatar-choice-button${isSelected ? " selected" : ""}`;
    button.type = "button";
    button.setAttribute("aria-pressed", isSelected ? "true" : "false");
    button.innerHTML = `
      <img src="${avatarImage(avatar.id)}" alt="" loading="lazy" decoding="async" />
      <span>${avatar.name}</span>
    `;
    button.addEventListener("click", () => {
      selectedAvatarId = avatar.id;
      const select = document.querySelector("#createAvatarSelect");
      if (select) select.value = selectedAvatarId;
      renderAvatarChoices(nextAvailable);
    });
    grid.appendChild(button);
  }
}

async function loadLobbyRooms() {
  const status = document.querySelector("#roomListStatus");
  if (status) status.textContent = "正在加载...";
  try {
    const response = await fetch("/api/rooms");
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "load rooms failed");
    renderLobbyRooms(payload.rooms || []);
  } catch (error) {
    const list = document.querySelector("#roomList");
    if (list) list.innerHTML = '<div class="room-card"><div><h3>房间加载失败</h3><p class="room-meta">请稍后刷新。</p></div></div>';
    if (status) status.textContent = "加载失败";
  }
}

function renderLobbyRooms(rooms) {
  const list = document.querySelector("#roomList");
  const status = document.querySelector("#roomListStatus");
  if (!list) return;
  list.innerHTML = "";
  if (status) status.textContent = rooms.length ? `${rooms.length} 个可加入` : "暂无可加入房间";
  if (!rooms.length) {
    list.innerHTML = '<div class="room-card"><div><h3>暂无房间</h3><p class="room-meta">创建一个房间，朋友就能在这里看到。</p></div></div>';
    return;
  }
  for (const item of rooms) {
    const card = document.createElement("article");
    card.className = "room-card";
    card.innerHTML = `
      <div>
        <h3>${item.host_name || "玩家"}的房间</h3>
        <p class="room-meta">${item.human_count}/9 真人 · AI 补位 ${item.ai_fill_count} · 房间号 ${item.room_id}</p>
      </div>
      <button class="primary-action" type="button">加入</button>
    `;
    card.querySelector("button").addEventListener("click", () => joinLobbyRoom(item.room_id));
    list.appendChild(card);
  }
}

async function createLobbyRoom() {
  const name = document.querySelector("#createNameInput").value.trim() || DEFAULT_HUMAN_NAME;
  const avatarId = selectedAvatarId;
  await roomRequest("/api/rooms", { human_name: name, avatar_id: avatarId });
}

async function joinLobbyRoom(roomId) {
  const name = document.querySelector("#createNameInput").value.trim() || DEFAULT_HUMAN_NAME;
  const avatarId = selectedAvatarId;
  await roomRequest(`/api/rooms/${roomId}/join`, { human_name: name, avatar_id: avatarId });
}

async function roomRequest(url, payload) {
  showLobbyStatus("正在进入房间...");
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const nextRoom = await response.json();
    if (!response.ok) throw new Error(nextRoom.detail || "room request failed");
    room = nextRoom;
    localPlayerId = nextRoom.human_id;
    saveLocalSession(nextRoom);
    renderWaitingRoom();
    showScreen("waiting");
    startRoomPolling();
  } catch (error) {
    showLobbyStatus(error.message || "进入房间失败");
  }
}

async function applyRemoteRoom(nextRoom) {
  const previousStage = currentStage;
  room = nextRoom;
  localPlayerId = nextRoom.human_id || localPlayerId;
  if (nextRoom.status === "waiting") {
    renderWaitingRoom();
    showScreen("waiting");
    return;
  }
  if (nextRoom.status === "playing") {
    currentStage = room.stage;
    if (previousStage !== currentStage) {
      resetLocalStageState();
    }
    showScreen("game");
    renderRoom();
    scheduleCurrentAutoAdvance();
  }
}

async function fetchRoomState() {
  if (!room?.room_id || !localPlayerId || roomRequestInFlight) return;
  const requestId = ++roomPollRequestId;
  const viewerId = encodeURIComponent(localPlayerId);
  try {
    const response = await fetch(`/api/rooms/${room.room_id}?player_id=${viewerId}`);
    const nextRoom = await response.json();
    if (roomRequestInFlight || requestId !== roomPollRequestId) return;
    if (response.status === 404) {
      clearLocalSession();
      stopRoomPolling();
      room = null;
      localPlayerId = null;
      showScreen("lobby");
      loadLobbyRooms();
      return;
    }
    if (!response.ok) throw new Error(nextRoom.detail || "fetch room failed");
    await applyRemoteRoom(nextRoom);
  } catch (error) {
    showWaitingStatus("同步房间状态失败，稍后重试...");
  }
}

function startRoomPolling() {
  stopRoomPolling();
  roomPollTimer = setInterval(fetchRoomState, ROOM_POLL_INTERVAL_MS);
}

function stopRoomPolling() {
  if (!roomPollTimer) return;
  clearInterval(roomPollTimer);
  roomPollTimer = null;
}

function renderWaitingRoom() {
  if (!room || room.status !== "waiting") return;
  document.querySelector("#waitingRoomTitle").textContent = `房间 ${room.room_id}`;
  document.querySelector("#waitingRoomCode").textContent = room.room_id;
  document.querySelector("#waitingRoomCount").textContent = `${room.human_count}/9 真人`;
  document.querySelector("#waitingRoomAiCount").textContent = `AI 补位 ${room.ai_fill_count}`;
  document.querySelector("#waitingHostStatus").textContent = localPlayerId === room.host_id ? "你是房主" : "等待房主开局";
  const seats = document.querySelector("#waitingSeats");
  seats.innerHTML = "";
  const membersById = new Map((room.members || []).map((member) => [member.id, member]));
  for (let seat = 1; seat <= 9; seat += 1) {
    const member = membersById.get(String(seat));
    const card = document.createElement("article");
    card.className = `waiting-seat${member ? "" : " ai"}${member?.id === localPlayerId ? " mine" : ""}`;
    card.innerHTML = member
      ? `
        <img class="waiting-seat-avatar" src="${avatarImage(member.avatar_id)}" alt="" loading="lazy" decoding="async" />
        <strong>${seat}. ${member.name}${member.id === localPlayerId ? "（我）" : ""}</strong>
        <span>${member.is_host ? "房主" : member.is_ready ? "已准备" : "未准备"}</span>
      `
      : `<strong>${seat}. AI 补位</strong><span>开局时自动加入</span>`;
    seats.appendChild(card);
  }
  document.querySelector("#startRoomButton").classList.toggle("hidden", localPlayerId !== room.host_id);
  populateAvatarSelect("#createAvatarSelect", room.available_avatars && room.available_avatars.length ? room.available_avatars : avatarChoices);
  renderAvatarChoices(room.available_avatars && room.available_avatars.length ? room.available_avatars : avatarChoices);
}

async function copyWaitingRoomCode() {
  if (!room?.room_id) return;
  try {
    await navigator.clipboard.writeText(room.room_id);
    showWaitingStatus("房间码已复制");
  } catch (error) {
    showWaitingStatus(`房间码：${room.room_id}`);
  }
}

async function toggleReady() {
  if (!room || !localPlayerId) return;
  await updateWaitingRoom(`/api/rooms/${room.room_id}/ready`, { player_id: localPlayerId });
}

async function startWaitingRoom() {
  if (!room || !localPlayerId) return;
  const nextRoom = await updateWaitingRoom(`/api/rooms/${room.room_id}/start`, { player_id: localPlayerId });
  if (nextRoom && nextRoom.status === "playing") {
    room = nextRoom;
    currentStage = room.stage;
    renderedSpeechKeys = new Set();
    saveLocalSession(nextRoom);
    showScreen("game");
    renderRoom();
  }
}

async function updateWaitingRoom(url, payload) {
  showWaitingStatus("正在更新...");
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const nextRoom = await response.json();
    if (!response.ok) throw new Error(nextRoom.detail || "update room failed");
    room = nextRoom;
    renderWaitingRoom();
    showWaitingStatus("");
    return nextRoom;
  } catch (error) {
    showWaitingStatus(error.message || "更新失败");
    return null;
  }
}

function avatarName(avatarId) {
  return (avatarChoices.find((avatar) => avatar.id === avatarId) || {}).name || avatarId;
}

function avatarImage(avatarId) {
  const avatar = avatarChoices.find((choice) => choice.id === avatarId);
  if (!avatar || avatar.id === "human") return humanAvatar;
  if (avatar.id === "garfield") return "/static/assets/avatars/garfield.webp";
  return `/static/assets/avatars/${avatar.id}.webp`;
}

function showScreen(name) {
  document.querySelector("#lobbyScreen")?.classList.toggle("hidden", name !== "lobby");
  document.querySelector("#waitingRoomScreen")?.classList.toggle("hidden", name !== "waiting");
  document.querySelector("#startScreen")?.classList.toggle("hidden", name !== "start");
  document.querySelector("#gameScreen")?.classList.toggle("hidden", name !== "game");
}

function showLobbyStatus(message) {
  const status = document.querySelector("#lobbyStatus");
  if (status) status.textContent = message;
}

function showWaitingStatus(message) {
  const status = document.querySelector("#waitingStatus");
  if (status) status.textContent = message;
}

function showNameModal() {
  if (room) return;
  const modal = document.querySelector("#nameModal");
  modal.classList.remove("hidden");
  showNameStatus("");
  document.querySelector("#humanNameInput").focus();
}

function hideNameModal() {
  document.querySelector("#nameModal").classList.add("hidden");
}

async function startGame() {
  if (room) return;
  roleRevealed = false;
  pendingSeerReveal = null;
  witchActionFlow = null;
  discussionPlaybackRunning = false;
  votePlaybackRunning = false;
  clearTimeout(discussionAdvanceTimer);
  discussionAdvanceTimer = null;
  clearTimeout(voteAdvanceTimer);
  voteAdvanceTimer = null;
  setStartButtonState("starting");
  try {
    const customHumanName = document.querySelector("#humanNameInput").value.trim();
    const humanName = customHumanName || DEFAULT_HUMAN_NAME;
    const response = await fetch("/api/rooms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ human_name: humanName, human_seat: pickHumanSeat() }),
    });
    const nextRoom = await response.json();
    if (!response.ok) throw new Error(nextRoom.detail || "create room failed");

    room = nextRoom;
    localPlayerId = nextRoom.human_id;
    currentStage = room.stage;
    renderedSpeechKeys = new Set();

    await withFog(async () => {
      hideNameModal();
      document.querySelector("#startScreen").classList.add("hidden");
      document.querySelector("#gameScreen").classList.remove("hidden");
      renderRoom();
    });
  } catch (error) {
    showStartError("创建房间失败，请检查服务或 DeepSeek 配置后重试。");
    setStartButtonState("idle");
  }
}

async function nextStage() {
  const canAdvanceWinnerResult = room && room.winner && (currentStage === "night_result" || currentStage === "day_vote_result");
  if (!room || !canDriveRoom() || room.waiting_for || (room.winner && !canAdvanceWinnerResult)) return;
  roomRequestInFlight = true;
  roomPollRequestId += 1;
  setBusy(true);
  try {
    const query = localPlayerId ? `?player_id=${encodeURIComponent(localPlayerId)}` : "";
    const response = await fetch(`/api/rooms/${room.room_id}/next_stage${query}`, { method: "POST" });
    const nextRoom = await response.json();
    if (!response.ok) throw new Error(nextRoom.detail || "next_stage failed");
    await applyRoom(nextRoom);
  } catch (error) {
    showLocalEvent("阶段推进失败，请稍后重试。");
  } finally {
    roomRequestInFlight = false;
    setBusy(false);
  }
}

async function submitAction(payload) {
  if (!room || !room.waiting_for) return;
  if (!isLocalPendingActor()) {
    await fetchRoomState();
    return;
  }
  roomRequestInFlight = true;
  roomPollRequestId += 1;
  setBusy(true);
  try {
    const query = localPlayerId ? `?player_id=${encodeURIComponent(localPlayerId)}` : "";
    const response = await fetch(`/api/rooms/${room.room_id}/submit_action${query}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const nextRoom = await response.json();
    if (!response.ok) throw new Error(nextRoom.detail || "submit failed");
    await applyRoom(nextRoom, payload.kind);
  } catch (error) {
    showLocalEvent("提交失败，请重新选择。");
  } finally {
    roomRequestInFlight = false;
    setBusy(false);
  }
}

async function applyRoom(nextRoom, actionKind = null) {
  const previousStage = currentStage;
  room = nextRoom;
  currentStage = room.stage;
  const shouldShowSeerReveal = actionKind === "seer_check" && room.seer_checks && room.human_role === "seer";
  if (shouldShowSeerReveal) {
    pendingSeerReveal = buildSeerReveal();
  }
  if (previousStage !== currentStage) {
    resetLocalStageState({ keepSeerReveal: shouldShowSeerReveal });
    await transitionToStage(currentStage, renderRoom);
  } else {
    renderRoom();
  }

  if (shouldShowSeerReveal) {
    renderRoom();
    return;
  }

  scheduleCurrentAutoAdvance();
}

function resetLocalStageState(options = {}) {
  pendingChoice = null;
  if (!options.keepSeerReveal) {
    pendingSeerReveal = null;
  }
  witchActionFlow = null;
  clearTimeout(discussionAdvanceTimer);
  discussionAdvanceTimer = null;
  discussionAdvanceKey = null;
  clearTimeout(voteAdvanceTimer);
  voteAdvanceTimer = null;
  voteAdvanceKey = null;
  discussionPlaybackRunning = false;
  votePlaybackRunning = false;
  if (currentStage === "day_discussion") {
    resetDiscussionFeed();
  } else if (currentStage === "day_vote") {
    resetVoteFeed();
  }
}

async function transitionToStage(stage, renderFn) {
  await showFog();
  currentStage = stage;
  renderFn();
  await hideFog();
}

async function withFog(work) {
  await showFog();
  await work();
  await hideFog();
}

async function showFog() {
  document.querySelector("#fogTransition").classList.add("active");
  await sleep(800);
}

async function hideFog() {
  document.querySelector("#fogTransition").classList.remove("active");
  await sleep(800);
}

function showRoleModal() {
  roleRevealed = true;
  renderRoom();
  const human = getHumanPlayer();
  const role = room.human_role;
  const wolfTeammates = room.wolf_teammates || [];
  const card = document.querySelector(".role-card");
  card.classList.remove("werewolf", "good");
  card.classList.add(role === "werewolf" ? "werewolf" : "good");
  document.querySelector("#roleName").textContent = roleNames[role] || role;
  document.querySelector("#roleSeat").textContent = `座位 ${human.id}`;
  document.querySelector("#roleCamp").textContent = campNames[role] || "未知阵营";
  const teammatesNode = document.querySelector("#roleTeammates");
  if (teammatesNode) {
    const teammateNames = wolfTeammates.map((player) => player.name).filter(Boolean);
    teammatesNode.textContent = role === "werewolf"
      ? `你的狼队友：${teammateNames.length ? teammateNames.join("、") : "无"}`
      : "";
    teammatesNode.classList.toggle("hidden", role !== "werewolf");
  }
  document.querySelector("#roleModal").classList.remove("hidden");
}

async function closeRoleModal() {
  document.querySelector("#roleModal").classList.add("hidden");
  if (room && room.stage === "setup" && !room.waiting_for) {
    await nextStage();
  }
}

function renderRoom() {
  if (!room) return;
  const displayStage = pendingSeerReveal ? "seer_action" : currentStage;
  const activePlayerId = getActivePlayerId(displayStage);
  renderHeader(displayStage);
  renderPlayers(activePlayerId);
  renderPanels(displayStage);
  renderEvents();
  renderVoteTargets();
  renderWaitingAction(displayStage);
  if (currentStage === "day_discussion" || currentStage === "day_discussion_done") {
    renderDiscussionFeedProgress();
  } else if (currentStage === "day_vote") {
    renderVoteFeedProgress();
  } else {
    renderSpeechFeedInstant();
  }
}

function renderHeader(displayStage = currentStage) {
  const [eyebrow, title] = stageCopy[displayStage] || stageCopy.setup;
  document.querySelector("#phaseEyebrow").textContent = eyebrow;
  document.querySelector("#phaseTitle").textContent = title;
  document.querySelector("#roundInfo").textContent = `第 ${room.day} 天 / 第 ${room.night} 夜`;
  document.querySelector("#seatInfo").textContent = `座位 ${room.human_id}`;
}

function renderPanels(displayStage = currentStage) {
  const panelId = (stageCopy[displayStage] || stageCopy.setup)[2];
  document.querySelectorAll(".phase-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === panelId);
  });

  const waitingKind = room?.waiting_for?.kind || null;
  const canAdvanceWinnerResult = room?.winner && (displayStage === "night_result" || displayStage === "day_vote_result");
  const canContinue = Boolean(room && canDriveRoom() && !room.waiting_for && (!room.winner || canAdvanceWinnerResult));
  const showSpeechControls = waitingKind === "speech" && isLocalPendingActor();
  const showVoteControls = waitingKind === "vote" && isLocalPendingActor();

  setVisible("#advanceButton", false);
  setVisible("#dawnNextButton", displayStage === "dawn");
  setVisible("#nightResultNextButton", displayStage === "night_result");
  setVisible("#discussionNextButton", displayStage === "day_discussion_done");
  setVisible("#voteResultNextButton", displayStage === "day_vote_result");
  setVisible("#speechInput", showSpeechControls);
  setVisible("#speechButton", showSpeechControls);
  setVisible("#voteTarget", showVoteControls);
  setVisible("#voteButton", showVoteControls);

  document.querySelector("#advanceButton").disabled = !canContinue;
  document.querySelector("#dawnNextButton").disabled = !canContinue;
  const nightResultNextButton = document.querySelector("#nightResultNextButton");
  if (nightResultNextButton) nightResultNextButton.disabled = !canContinue;
  document.querySelector("#discussionNextButton").disabled = !canContinue || discussionPlaybackRunning;
  const voteResultNextButton = document.querySelector("#voteResultNextButton");
  if (voteResultNextButton) voteResultNextButton.disabled = !canContinue;
  document.querySelector("#speechButton").disabled = !showSpeechControls;
  document.querySelector("#voteButton").disabled = !showVoteControls;

  document.querySelector("#wolfStatus").textContent = nightNarration("wolf_action");
  document.querySelector("#seerStatus").textContent = nightNarration("seer_action");
  document.querySelector("#witchStatus").textContent = nightNarration("witch_action");

  const latestNight = [...room.events].reverse().find((event) => event.phase === "night");
  document.querySelector("#dawnSummary").textContent = latestNight?.content || "昨夜的信息正在公布。";
  const nightResultSummary = document.querySelector("#nightResultSummary");
  if (nightResultSummary) {
    nightResultSummary.textContent = latestNight?.content || "本夜结果已经公布。";
  }
  const voteResultSummary = document.querySelector("#voteResultSummary");
  if (voteResultSummary) {
    const latestVoteResult = [...room.events].reverse().find((event) => event.phase === "day_vote" && /被放逐出局|was voted out/i.test(event.content || ""));
    voteResultSummary.textContent = latestVoteResult?.content || "本轮投票已经结束。";
    const voteResultNextButton = document.querySelector("#voteResultNextButton");
    if (voteResultNextButton) voteResultNextButton.textContent = room.winner ? "查看最终胜负" : "继续下一轮";
  }

  if (room.winner) {
    document.querySelector("#winnerTitle").textContent = room.winner === "werewolf" ? "狼人阵营获胜" : "好人阵营获胜";
    document.querySelector("#winnerText").textContent = "所有身份已经公开，游戏结束。";
  }
}

function renderWaitingAction() {
  clearActionBoxes();
  if (pendingSeerReveal) {
    renderSeerReveal();
    return;
  }
  if (!room.waiting_for) {
    showWaitingStatus("");
    return;
  }
  const wait = room.waiting_for;
  const isMine = isLocalPendingActor(wait);
  showWaitingStatus(isMine ? "" : `等待 ${pendingActorLabel(wait)} 操作...`);
  if (wait.kind === "speech") {
    renderPlayers(wait.speaker_id || room.human_id);
    showLocalEvent(`轮到 ${wait.speaker_name || "你"} 发言。发言完毕后点击“我发言完毕”。`);
  } else if (wait.kind === "vote") {
    renderPlayers(wait.voter_id || room.human_id);
    showLocalEvent(`轮到 ${wait.voter_name || "你"} 投票。请选择一位玩家后提交投票。`);
    const target = document.querySelector("#voteTarget");
    if (target) target.focus();
  }
  if (!isMine) return;
  if (pendingChoice && pendingChoice.kind !== "witch_action") {
    renderChoiceConfirmation(wait);
    return;
  }
  if (wait.kind === "wolf_kill") renderTargetChoices("#wolfAction", "wolf_kill", wait.candidates, "wolfAction");
  if (wait.kind === "seer_check") renderTargetChoices("#seerAction", "seer_check", wait.candidates, "seerAction");
  if (wait.kind === "hunter_shot") renderTargetChoices("#hunterAction", "hunter_shot", wait.candidates, "hunterAction");
  if (wait.kind === "witch_action") renderWitchChoices(wait);
}

function clearActionBoxes() {
  ["#wolfAction", "#seerAction", "#witchAction", "#hunterAction"].forEach((selector) => {
    document.querySelector(selector).innerHTML = "";
  });
}

function renderTargetChoices(selector, kind, candidates, roleName) {
  const box = document.querySelector(selector);
  box.innerHTML = `<p class="status-line">${roleChoiceText(roleName)}</p><div class="choice-grid"></div>`;
  const grid = box.querySelector(".choice-grid");
  for (const candidate of candidates || []) {
    const button = document.createElement("button");
    button.className = "choice-card";
    button.textContent = `${candidate.id}. ${candidate.name}`;
    button.addEventListener("click", () => chooseWithConfirm(kind, candidate));
    grid.appendChild(button);
  }
}

function isLocalPendingActor(wait = room?.waiting_for) {
  if (!wait || !localPlayerId) return false;
  if (wait.kind === "speech") return wait.speaker_id === localPlayerId;
  if (wait.kind === "vote") return wait.voter_id === localPlayerId;
  const roleByKind = {
    wolf_kill: "werewolf",
    seer_check: "seer",
    witch_action: "witch",
    hunter_shot: "hunter",
  };
  return room?.human_role === roleByKind[wait.kind];
}

function pendingActorLabel(wait = room?.waiting_for) {
  if (!wait) return "其他玩家";
  if (wait.speaker_id) return `${wait.speaker_id} 号 ${wait.speaker_name || "玩家"}`;
  if (wait.voter_id) return `${wait.voter_id} 号 ${wait.voter_name || "玩家"}`;
  const roleLabels = {
    wolf_kill: "狼人",
    seer_check: "预言家",
    witch_action: "女巫",
    hunter_shot: "猎人",
  };
  return roleLabels[wait.kind] || "其他玩家";
}

function renderWitchChoices(wait) {
  const flow = ensureWitchActionFlow(wait);
  if (!flow) return;

  const box = document.querySelector("#witchAction");
  box.innerHTML = `<p class="status-line">${flow.step === "save" ? "解药阶段" : "毒药阶段"}</p><div class="choice-grid"></div>`;
  const grid = box.querySelector(".choice-grid");
  document.querySelector("#witchStatus").textContent = flow.step === "save" ? buildWitchSavePrompt(flow) : buildWitchPoisonPrompt(flow);

  if (flow.step === "save") {
    const victim = flow.saveCandidates[0];

    const saveButton = document.createElement("button");
    saveButton.className = "choice-card";
    saveButton.type = "button";
    saveButton.textContent = victim ? `救下 ${victim.id}. ${victim.name}` : "使用解药";
    saveButton.addEventListener("click", () => {
      const nextFlow = {
        ...flow,
        saveTargetId: victim ? victim.id : null,
      };
      witchActionFlow = {
        ...nextFlow,
        step: flow.canPoison ? "poison" : "save",
      };
      if (flow.canPoison) {
        renderRoom();
      } else {
        submitWitchAction(nextFlow, null);
      }
    });
    grid.appendChild(saveButton);

    const skipButton = document.createElement("button");
    skipButton.className = "choice-card";
    skipButton.type = "button";
    skipButton.textContent = "不救，继续下一步";
    skipButton.addEventListener("click", () => {
      const nextFlow = {
        ...flow,
        saveTargetId: null,
      };
      witchActionFlow = {
        ...nextFlow,
        step: flow.canPoison ? "poison" : "save",
      };
      if (flow.canPoison) {
        renderRoom();
      } else {
        submitWitchAction(nextFlow, null);
      }
    });
    grid.appendChild(skipButton);
    return;
  }

  const skipPoison = document.createElement("button");
  skipPoison.className = "choice-card";
  skipPoison.type = "button";
  skipPoison.textContent = "不下毒";
  skipPoison.addEventListener("click", () => submitWitchAction(flow, null));
  grid.appendChild(skipPoison);

  for (const candidate of flow.poisonCandidates) {
    const button = document.createElement("button");
    button.className = "choice-card";
    button.type = "button";
    button.textContent = `毒死 ${candidate.id}. ${candidate.name}`;
    button.addEventListener("click", () => submitWitchAction(flow, candidate.id));
    grid.appendChild(button);
  }
}

function ensureWitchActionFlow(wait) {
  const saveCandidates = wait.save_candidates || [];
  const poisonCandidates = wait.poison_candidates || [];
  const canSave = Boolean(wait.can_save && saveCandidates.length);
  const canPoison = Boolean(wait.can_poison && poisonCandidates.length);
  const initialStep = canSave ? "save" : "poison";

  if (!witchActionFlow || witchActionFlow.night !== room.night || witchActionFlow.waitKind !== wait.kind) {
    witchActionFlow = {
      night: room.night,
      waitKind: wait.kind,
      step: initialStep,
      saveTargetId: null,
      poisonTargetId: null,
      canSave,
      canPoison,
      saveCandidates,
      poisonCandidates,
    };
    return witchActionFlow;
  }

  witchActionFlow = {
    ...witchActionFlow,
    canSave,
    canPoison,
    saveCandidates,
    poisonCandidates,
  };

  if (witchActionFlow.step === "save" && !canSave) {
    witchActionFlow.step = "poison";
  }

  return witchActionFlow;
}

function buildWitchSavePrompt(flow) {
  const victim = flow.saveCandidates[0];
  if (!victim) return "今晚有玩家被狼人袭击，请决定是否使用解药。";
  return `今晚狼人击中了 ${victim.id}. ${victim.name}，请选择是否使用解药。`;
}

function buildWitchPoisonPrompt(flow) {
  if (!flow.canPoison) return "你已经完成解药选择，今晚无法再使用毒药。";
  return flow.saveTargetId ? "解药选择已确定，请选择毒药目标。" : "你选择不救人，请选择是否使用毒药。";
}

function submitWitchAction(flow, poisonTargetId) {
  const payload = { kind: "witch_action" };
  if (flow.saveTargetId !== null && flow.saveTargetId !== undefined) payload.save_target_id = flow.saveTargetId;
  if (poisonTargetId !== null && poisonTargetId !== undefined) payload.poison_target_id = poisonTargetId;
  submitAction(payload);
}

function chooseWithConfirm(kind, candidate, options = {}) {
  pendingChoice = { kind, candidate, options };
  renderWaitingAction();
}

function renderChoiceConfirmation(wait) {
  const { kind, candidate, options } = pendingChoice;
  const boxSelector = kind === "wolf_kill" ? "#wolfAction" : kind === "hunter_shot" ? "#hunterAction" : "#seerAction";
  const box = document.querySelector(boxSelector);
  const label = candidate ? `${candidate.id}. ${candidate.name}` : "未选择目标";
  const prompt = kind === "wolf_kill"
    ? `确认今晚袭击 ${label} 吗？`
    : kind === "hunter_shot"
      ? `确认猎人带走 ${label} 吗？`
      : `确认查验 ${label} 吗？`;

  box.innerHTML = `
    <p class="status-line">${prompt}</p>
    <div class="choice-grid">
      <button id="confirmChoiceButton" class="choice-card" type="button">确认</button>
      <button id="cancelChoiceButton" class="choice-card" type="button">取消</button>
    </div>
  `;

  document.querySelector("#confirmChoiceButton").addEventListener("click", () => {
    const activeChoice = pendingChoice;
    pendingChoice = null;
    if (!activeChoice) return;

    const activeCandidate = activeChoice.candidate;
    if (activeChoice.kind === "wolf_kill" || activeChoice.kind === "seer_check" || activeChoice.kind === "hunter_shot") {
      submitAction({ kind: activeChoice.kind, target_id: activeCandidate.id });
    }
  });

  document.querySelector("#cancelChoiceButton").addEventListener("click", () => {
    pendingChoice = null;
    renderWaitingAction();
  });
}

function buildSeerReveal() {
  const myCheck = [...(room.seer_checks || [])].reverse().find((check) => check.seer_id === room.human_id);
  if (!myCheck) return null;
  const target = room.players.find((player) => player.id === myCheck.target_id);
  if (!target) return null;
  return {
    target,
    verdict: myCheck.result_camp === "werewolf" ? "狼人阵营" : "好人阵营",
  };
}

function renderSeerReveal() {
  const reveal = pendingSeerReveal || buildSeerReveal();
  if (!reveal) return;
  const { target, verdict } = reveal;
  const modal = document.querySelector("#seerRevealModal");
  const title = document.querySelector("#seerRevealTitle");
  const text = document.querySelector("#seerRevealText");
  const ackButton = document.querySelector("#seerAckButton");
  if (!modal || !title || !text) return;
  title.textContent = `${target.id}. ${target.name}`;
  text.textContent = `查验结果：${target.name} 是 ${verdict}。`;
  modal.classList.remove("hidden");
  if (!ackButton) return;
  ackButton.onclick = async () => {
    pendingSeerReveal = null;
    modal.classList.add("hidden");
    renderRoom();
    scheduleNightAutoAdvance();
  };
}

function renderPlayers(activeSpeakerId = null) {
  const container = document.querySelector("#players");
  container.innerHTML = "";
  for (const player of room.players) {
    const card = document.createElement("article");
    card.className = "player";
    if (!player.is_alive) card.classList.add("dead");
    if (player.id === activeSpeakerId) card.classList.add("active-speaker");
    const roleLabel = roleNames[visiblePlayerRole(player)] || visiblePlayerRole(player);
    const avatarUrl = avatarForPlayer(player);
    if (avatarUrl) {
      const avatar = document.createElement("img");
      avatar.className = "player-avatar";
      avatar.src = avatarUrl;
      avatar.alt = `${player.name}头像`;
      avatar.loading = "lazy";
      avatar.decoding = "async";
      card.appendChild(avatar);
    } else {
      const fallback = document.createElement("div");
      fallback.className = "player-avatar player-avatar-fallback";
      fallback.textContent = player.name.trim().slice(0, 1) || "?";
      card.appendChild(fallback);
    }

    const name = document.createElement("strong");
    name.textContent = `${player.id}. ${player.name}${player.id === room.human_id ? "（你）" : ""}`;
    const role = document.createElement("span");
    role.textContent = roleLabel;
    const status = document.createElement("span");
    status.textContent = player.is_alive ? "存活" : "出局";
    card.append(name, role, status);
    container.appendChild(card);
  }
}

function visiblePlayerRole(player) {
  if (player.is_human && !roleRevealed) return "pending";
  if (!roleRevealed && player.role === "werewolf" && player.id !== room.human_id) return "hidden";
  return player.role;
}

function renderVoteTargets() {
  const select = document.querySelector("#voteTarget");
  const selectedTargetId = select.value;
  select.innerHTML = "";
  for (const player of room.players) {
    if (!player.is_alive || player.id === room.human_id) continue;
    const option = document.createElement("option");
    option.value = player.id;
    option.textContent = `${player.id}. ${player.name}`;
    select.appendChild(option);
  }
  if (selectedTargetId && select.querySelector(`option[value="${CSS.escape(selectedTargetId)}"]`)) {
    select.value = selectedTargetId;
  }
}

function renderEvents() {
  const container = document.querySelector("#events");
  container.innerHTML = "";
  for (const event of room.events.slice().reverse()) {
    const item = document.createElement("div");
    item.className = "event";
    item.textContent = `[第 ${event.day} 天 | ${phaseLabel(event.phase)}] ${event.content}`;
    container.appendChild(item);
  }
}

function showLocalEvent(text) {
  const container = document.querySelector("#events");
  const item = document.createElement("div");
  item.className = "event";
  item.textContent = text;
  container.prepend(item);
}

function showSeerResult() {
  pendingSeerReveal = buildSeerReveal();
  renderRoom();
}

async function submitSpeech() {
  const input = document.querySelector("#speechInput");
  const content = input.value.trim();
  input.value = "";
  await submitAction({ kind: "speech", content });
}

async function submitVote() {
  const targetId = document.querySelector("#voteTarget").value;
  if (!targetId) return;
  await submitAction({ kind: "vote", target_id: targetId });
}

function resetDiscussionFeed() {
  renderedSpeechKeys = new Set();
  const feed = document.querySelector("#speechFeed");
  if (feed) feed.innerHTML = "";
}

function resetVoteFeed() {
  renderedSpeechKeys = new Set();
  const feed = document.querySelector("#voteFeed");
  if (feed) feed.innerHTML = "";
}

function getActivePlayerId(displayStage = currentStage) {
  if (displayStage === "day_discussion" || displayStage === "day_discussion_done") {
    if (room?.waiting_for?.kind === "speech") {
      return room.waiting_for.speaker_id || room.human_id;
    }
    const speeches = orderedSpeeches(room.speeches || []).filter((speech) => speech.day === room.day && speech.phase === "day_discussion");
    return speeches.length ? speeches[speeches.length - 1].speaker_id : null;
  }

  if (displayStage === "day_vote") {
    if (room?.waiting_for?.kind === "vote") {
      return room.waiting_for.voter_id || room.human_id;
    }
    const votes = orderedVotes(room.votes || []).filter((vote) => vote.day === room.day);
    const votedIds = new Set(votes.map((vote) => vote.voter_id));
    const living = room.players.filter((player) => player.is_alive).sort((a, b) => Number(a.id) - Number(b.id));
    const next = living.find((player) => !votedIds.has(player.id));
    return next ? next.id : null;
  }

  return null;
}

function scheduleDiscussionAutoAdvance() {
  clearTimeout(voteAdvanceTimer);
  voteAdvanceTimer = null;
  voteAdvanceKey = null;
  if (!room || !canDriveRoom() || room.winner || pendingSeerReveal || currentStage !== "day_discussion" || room.waiting_for) {
    clearTimeout(discussionAdvanceTimer);
    discussionAdvanceTimer = null;
    discussionAdvanceKey = null;
    discussionPlaybackRunning = false;
    return;
  }
  const speeches = orderedSpeeches(room.speeches || []).filter((speech) => speech.day === room.day && speech.phase === "day_discussion");
  const latestSpeech = speeches[speeches.length - 1] || null;
  if (!latestSpeech) {
    renderFirstDiscussionWaitPrompt();
  }
  const delay = latestSpeech ? discussionDelayFromText(latestSpeech.content) : 700;
  const advanceKey = `${currentStage}:${room.day}:${speeches.length}:${latestSpeech ? speechKey(latestSpeech) : "none"}`;
  if (discussionAdvanceTimer && discussionAdvanceKey === advanceKey) return;
  clearTimeout(discussionAdvanceTimer);
  discussionAdvanceKey = advanceKey;
  discussionPlaybackRunning = true;
  discussionAdvanceTimer = setTimeout(() => {
    discussionAdvanceTimer = null;
    discussionAdvanceKey = null;
    if (!room || room.winner || pendingSeerReveal || currentStage !== room.stage || currentStage !== "day_discussion" || room.waiting_for) return;
    nextStage();
  }, delay);
}

function renderFirstDiscussionWaitPrompt() {
  const feed = document.querySelector("#speechFeed");
  if (!feed || feed.children.length) return;
  feed.innerHTML = '<div class="speech-bubble wait-bubble">请认真思考自己接下来的发言</div>';
}

function scheduleVoteAutoAdvance() {
  clearTimeout(discussionAdvanceTimer);
  discussionAdvanceTimer = null;
  discussionAdvanceKey = null;
  if (!room || !canDriveRoom() || room.winner || pendingSeerReveal || currentStage !== "day_vote" || room.waiting_for) {
    clearTimeout(voteAdvanceTimer);
    voteAdvanceTimer = null;
    voteAdvanceKey = null;
    votePlaybackRunning = false;
    return;
  }
  const votes = orderedVotes(room.votes || []).filter((vote) => vote.day === room.day);
  const delay = votes.length ? 450 : 250;
  const latestVote = votes[votes.length - 1] || null;
  const advanceKey = `${currentStage}:${room.day}:${votes.length}:${latestVote ? voteKey(latestVote) : "none"}`;
  if (voteAdvanceTimer && voteAdvanceKey === advanceKey) return;
  clearTimeout(voteAdvanceTimer);
  voteAdvanceKey = advanceKey;
  votePlaybackRunning = true;
  voteAdvanceTimer = setTimeout(() => {
    voteAdvanceTimer = null;
    voteAdvanceKey = null;
    if (!room || room.winner || pendingSeerReveal || currentStage !== room.stage || currentStage !== "day_vote" || room.waiting_for) return;
    nextStage();
  }, delay);
}

function scheduleCurrentAutoAdvance() {
  const nightAutoStages = ["night_start", "wolf_action", "seer_action", "witch_action", "hunter_shot"];
  if (nightAutoStages.includes(currentStage)) {
    scheduleNightAutoAdvance();
    return;
  }
  if (currentStage === "day_discussion") {
    scheduleDiscussionAutoAdvance();
    return;
  }
  if (currentStage === "day_vote") {
    scheduleVoteAutoAdvance();
    return;
  }
  clearTimeout(autoAdvanceTimer);
  autoAdvanceTimer = null;
  autoAdvanceStage = null;
  clearTimeout(discussionAdvanceTimer);
  discussionAdvanceTimer = null;
  discussionAdvanceKey = null;
  clearTimeout(voteAdvanceTimer);
  voteAdvanceTimer = null;
  voteAdvanceKey = null;
}

function discussionDelayFromText(text) {
  const length = String(text || "").trim().length;
  return Math.max(1400, Math.min(5200, 900 + length * 40));
}

function renderDiscussionFeedProgress() {
  const feed = document.querySelector("#speechFeed");
  if (!feed) return;
  const speeches = orderedSpeeches(room.speeches || []).filter((speech) => speech.day === room.day && speech.phase === "day_discussion");
  for (const speech of speeches) {
    const key = speechKey(speech);
    if (renderedSpeechKeys.has(key)) continue;
    const player = getPlayer(speech.speaker_id);
    if (!player) continue;
    appendSpeechBubble(speech, player);
    renderedSpeechKeys.add(key);
  }
  feed.scrollTop = feed.scrollHeight;
}

function renderSpeechFeedInstant() {
  const feed = document.querySelector("#speechFeed");
  feed.innerHTML = "";
  renderedSpeechKeys = new Set();
  for (const speech of orderedSpeeches(room.speeches || [])) {
    const player = getPlayer(speech.speaker_id);
    if (!player) continue;
    appendSpeechBubble(speech, player);
    renderedSpeechKeys.add(speechKey(speech));
  }
}

function renderVoteFeedProgress() {
  const feed = document.querySelector("#voteFeed");
  if (!feed) return;
  const votes = orderedVotes(room.votes || []).filter((vote) => vote.day === room.day);
  for (const vote of votes) {
    const key = voteKey(vote);
    if (renderedSpeechKeys.has(key)) continue;
    const voter = getPlayer(vote.voter_id);
    const target = getPlayer(vote.target_id);
    if (!voter || !target) continue;
    appendVoteBubble(vote, voter, target);
    renderedSpeechKeys.add(key);
  }
  feed.scrollTop = feed.scrollHeight;
}

function orderedSpeeches(speeches) {
  return [...speeches].sort((a, b) => (a.day === b.day ? Number(a.speaker_id) - Number(b.speaker_id) : a.day - b.day));
}

function orderedVotes(votes) {
  return [...votes].sort((a, b) => (a.day === b.day ? Number(a.voter_id) - Number(b.voter_id) : a.day - b.day));
}

function appendSpeechBubble(speech, player) {
  const bubble = document.createElement("div");
  bubble.className = "speech-bubble";
  bubble.innerHTML = `<strong>${player.id}. ${player.name}</strong>${speech.content}`;
  document.querySelector("#speechFeed").appendChild(bubble);
}

function appendVoteBubble(vote, voter, target) {
  const bubble = document.createElement("div");
  bubble.className = "speech-bubble vote-bubble";
  bubble.innerHTML = `<strong>${voter.id}. ${voter.name}</strong>投给了 ${target.id}. ${target.name}`;
  document.querySelector("#voteFeed").appendChild(bubble);
}

function speechKey(speech) {
  return `${speech.day}:${speech.speaker_id}:${speech.content}`;
}

function voteKey(vote) {
  return `${vote.day}:${vote.voter_id}:${vote.target_id}`;
}

function getHumanPlayer() {
  return room.players.find((player) => player.id === room.human_id);
}

function getPlayer(playerId) {
  return room.players.find((player) => player.id === playerId);
}

function avatarForPlayer(player) {
  if (player.avatar_id) return avatarImage(player.avatar_id);
  return playerAvatarMap[player.name] || null;
}

function phaseLabel(phase) {
  return { setup: "准备", night: "夜晚", day_discussion: "白天讨论", day_vote: "投票", game_over: "结束" }[phase] || phase;
}

function roleChoiceText(selectorName) {
  if (currentStage === "wolf_action" && selectorName === "wolfAction") {
    return room.human_role === "werewolf" ? "请选择今晚要袭击的目标。" : "狼人正在选择今晚的目标。";
  }
  if (currentStage === "hunter_shot" && selectorName === "hunterAction") {
    return "猎人死亡，请选择一名玩家带走。";
  }
  if (currentStage === "seer_action" && selectorName === "seerAction") {
    return room.human_role === "seer" ? "请选择要查验的玩家，查验后会立即显示身份。" : "预言家正在查验一名玩家的身份。";
  }
  if (currentStage === "witch_action" && selectorName === "witchAction") {
    return room.human_role === "witch"
      ? "请选择是否救人或毒人，点击后会确认。"
      : "女巫正在决定是否使用药剂。";
  }
  return "请稍候。";
}

function nightNarration(stage) {
  if (currentStage !== stage) {
    if (stage === "wolf_action") return "狼人正在选择今晚的目标。";
    if (stage === "seer_action") return "预言家正在查验一名玩家的身份。";
    if (stage === "witch_action") return "女巫正在决定是否使用药剂。";
    return "";
  }
  if (stage === "wolf_action" && room.human_role !== "werewolf") return "狼人正在选择今晚的目标。";
  if (stage === "seer_action" && room.human_role !== "seer") return "预言家正在查验一名玩家的身份。";
  if (stage === "witch_action" && room.human_role !== "witch") return "女巫正在决定是否使用药剂。";
  return roleChoiceText(stage === "wolf_action" ? "wolfAction" : stage === "seer_action" ? "seerAction" : "witchAction");
}

function scheduleNightAutoAdvance() {
  clearTimeout(discussionAdvanceTimer);
  discussionAdvanceTimer = null;
  discussionAdvanceKey = null;
  clearTimeout(voteAdvanceTimer);
  voteAdvanceTimer = null;
  voteAdvanceKey = null;
  const autoStages = ["night_start", "wolf_action", "seer_action", "witch_action", "hunter_shot"];
  if (!room || !canDriveRoom() || room.waiting_for || room.winner || pendingSeerReveal || !autoStages.includes(currentStage)) {
    clearTimeout(autoAdvanceTimer);
    autoAdvanceTimer = null;
    autoAdvanceStage = null;
    return;
  }
  if (autoAdvanceTimer && autoAdvanceStage === currentStage) return;
  clearTimeout(autoAdvanceTimer);
  autoAdvanceStage = currentStage;
  autoAdvanceTimer = setTimeout(() => {
    autoAdvanceTimer = null;
    autoAdvanceStage = null;
    if (!room || room.waiting_for || room.winner || pendingSeerReveal || currentStage !== room.stage) return;
    nextStage();
  }, 1600);
}

function setVisible(selector, visible) {
  const node = document.querySelector(selector);
  if (!node) return;
  node.classList.toggle("hidden", !visible);
}

function canDriveRoom() {
  return Boolean(room && localPlayerId && localPlayerId === room.host_id);
}

function setBusy(isBusy) {
  if (isBusy) {
    document.querySelectorAll("button, textarea, select").forEach((element) => {
      if (element.id !== "startButton") element.disabled = true;
    });
    return;
  }
  document.querySelectorAll("button, textarea, select").forEach((element) => {
    if (element.id !== "startButton") element.disabled = false;
  });
  if (room) {
    renderPanels();
    renderWaitingAction();
  }
}

function setStartButtonState(state) {
  const button = document.querySelector("#startButton");
  if (!button) return;
  const confirmButton = document.querySelector("#confirmNameButton");
  const isStarting = state === "starting";
  button.disabled = isStarting;
  if (confirmButton) confirmButton.disabled = isStarting;
  button.setAttribute("aria-busy", String(isStarting));
  button.textContent = "开始游戏";
  if (confirmButton) confirmButton.textContent = isStarting ? "正在确认..." : "确认身份";
  showStartStatus(isStarting ? "正在准备游戏，请稍候..." : "");
  showNameStatus(isStarting ? "正在准备游戏，请稍候..." : "");
}

function pickHumanSeat() {
  return Math.floor(Math.random() * 9) + 1;
}

function showStartError(message) {
  showStartStatus(message);
  showNameStatus(message);
}

function showStartStatus(message) {
  const status = document.querySelector("#startStatus");
  if (status) {
    status.textContent = message;
  }
}

function showNameStatus(message) {
  const status = document.querySelector("#nameStatus");
  if (status) {
    status.textContent = message;
  }
}

function markPosterLoaded() {
  const startContent = document.querySelector(".start-content");
  if (!startContent) return;
  startContent.classList.remove("poster-loading");
  startContent.classList.add("poster-loaded");
}

const poster = document.querySelector("#openingPoster");
if (poster) {
  if (poster.complete && poster.naturalWidth > 0) {
    markPosterLoaded();
  } else {
    poster.addEventListener("load", markPosterLoaded, { once: true });
    poster.addEventListener("error", markPosterLoaded, { once: true });
  }
}

initializeLobby();

document.querySelector("#startButton").addEventListener("click", showNameModal);
document.querySelector("#confirmNameButton").addEventListener("click", startGame);
document.querySelector("#cancelNameButton").addEventListener("click", hideNameModal);
document.querySelector("#confirmRoleButton")?.addEventListener("click", showRoleModal);
document.querySelector("#closeRoleModalButton")?.addEventListener("click", closeRoleModal);
document.querySelector("#advanceButton")?.addEventListener("click", nextStage);
document.querySelector("#dawnNextButton")?.addEventListener("click", nextStage);
document.querySelector("#nightResultNextButton")?.addEventListener("click", nextStage);
document.querySelector("#discussionNextButton")?.addEventListener("click", nextStage);
document.querySelector("#voteResultNextButton")?.addEventListener("click", nextStage);
document.querySelector("#speechButton")?.addEventListener("click", submitSpeech);
document.querySelector("#voteButton")?.addEventListener("click", submitVote);
