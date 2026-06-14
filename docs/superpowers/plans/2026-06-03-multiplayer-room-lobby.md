# Multiplayer Room Lobby 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 添加首页房间列表、创建/加入等待房间、唯一头像、房主开局和 AI 补位到 9 人的联机大厅流程。

**架构：** 后端在现有 `web.py` 内扩展房间生命周期：`waiting` 房间保存真人成员，`playing` 房间保存现有 LangGraph 游戏状态。前端在现有静态页面上增加大厅和等待房间视图，开局后复用当前游戏视图。

**技术栈：** FastAPI、Pydantic、LangGraph、静态 HTML/CSS/JavaScript、pytest。

---

### 任务 1：后端等待房间模型与大厅 API

**文件：**
- 修改：`src/werewolf_langgraph/web.py`
- 测试：`tests/test_multiplayer_lobby.py`

- [ ] **步骤 1：编写失败测试**

覆盖创建房间、列出可加入房间、加入房间、拒绝满员/重复头像/已开始房间。

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/test_multiplayer_lobby.py -v`
预期：失败，因为 API 和模型尚未实现。

- [ ] **步骤 3：实现等待房间**

在 `web.py` 中添加 `RoomMember`、`RoomStatus`，扩展 `Room` 支持 `waiting` 状态，并添加：

- `GET /api/rooms`
- `POST /api/rooms`
- `POST /api/rooms/{room_id}/join`
- `POST /api/rooms/{room_id}/ready`

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/test_multiplayer_lobby.py -v`
预期：通过。

### 任务 2：房主开局与 AI 补位

**文件：**
- 修改：`src/werewolf_langgraph/web.py`
- 测试：`tests/test_multiplayer_lobby.py`

- [ ] **步骤 1：编写失败测试**

覆盖只有房主能开局、开局时补齐 9 人、开局后从可加入列表隐藏。

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/test_multiplayer_lobby.py -v`
预期：失败，因为 start API 尚未实现。

- [ ] **步骤 3：实现开局 API**

添加 `POST /api/rooms/{room_id}/start`。开局时把真人成员固定为 `is_human=True`，空座位用 AI 和未使用头像补齐，随机分配现有 9 人身份池，构建 LangGraph state。

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/test_multiplayer_lobby.py -v`
预期：通过。

### 任务 3：多真人操作归属

**文件：**
- 修改：`src/werewolf_langgraph/web.py`
- 测试：`tests/test_multiplayer_lobby.py`

- [ ] **步骤 1：编写失败测试**

覆盖房间序列化按请求玩家展示自己的身份、非当前行动玩家不能提交行动。

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/test_multiplayer_lobby.py -v`
预期：失败。

- [ ] **步骤 3：实现 viewer/player 参数**

让 `GET /api/rooms/{room_id}`、`next_stage`、`submit_action` 支持 `player_id`，序列化时按该玩家显示 `human_id/human_role`。提交行动时校验等待 payload 中的 `speaker_id`、`voter_id` 或角色行动玩家是否等于请求玩家。

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/test_multiplayer_lobby.py -v`
预期：通过。

### 任务 4：前端大厅与等待房间

**文件：**
- 修改：`src/werewolf_langgraph/static/index.html`
- 修改：`src/werewolf_langgraph/static/app.js`
- 修改：`src/werewolf_langgraph/static/styles.css`
- 测试：`tests/test_site_routing.py`

- [ ] **步骤 1：编写失败测试**

检查游戏页包含大厅、房间列表、创建房间表单、等待房间容器和更新后的脚本版本。

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/test_site_routing.py -v`
预期：失败。

- [ ] **步骤 3：实现前端**

首页显示可加入房间，创建/加入时选择昵称和头像。等待房间显示 9 个座位、准备状态、AI 补位提示。房主显示开始按钮；开局后切换到现有游戏视图。

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/test_site_routing.py -v`
预期：通过。

### 任务 5：回归验证

**文件：**
- 修改：按前面任务结果

- [ ] **步骤 1：运行完整测试**

运行：`pytest -q`
预期：全部通过。

- [ ] **步骤 2：启动本地服务**

运行：`python -m werewolf_langgraph --host 127.0.0.1 --port 8000`
预期：服务启动，浏览器可访问 `http://127.0.0.1:8000`。

- [ ] **步骤 3：浏览器验证**

在浏览器中检查：大厅加载、创建房间、另一个玩家加入、重复头像不可选、房主开局、开局后显示 9 名玩家。
