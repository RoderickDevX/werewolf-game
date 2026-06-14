# 手机端联机 MVP 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将联机入口改成手机优先的大厅和等待房，让玩家能清楚地创建/加入房间、查看 9 个座位并开局。

**架构：** 保留现有 FastAPI 房间接口和单页静态前端。先用结构测试锁定大厅/等待房必须存在的 DOM，再增量调整 `index.html`、`app.js` 和 `styles.css`。游戏回合内 UI 本轮尽量不动。

**技术栈：** FastAPI、原生 HTML/CSS/JavaScript、pytest、浏览器手动验证。

---

### 任务 1：补手机端大厅和等待房结构测试

**文件：**
- 修改：`tests/test_site_routing.py`

- [x] **步骤 1：编写失败的测试**

在 `test_localhost_serves_game` 后添加两个测试：

```python
def test_game_page_contains_mobile_lobby_controls():
    client = TestClient(create_app())

    response = client.get("/", headers={"Host": "127.0.0.1:8000"})

    assert response.status_code == 200
    assert 'class="mobile-lobby-topbar"' in response.text
    assert 'id="avatarChoiceGrid"' in response.text
    assert 'id="createAvatarSelect"' in response.text
    assert 'id="roomList"' in response.text
    assert 'id="createRoomButton"' in response.text


def test_game_page_contains_mobile_waiting_room_controls():
    client = TestClient(create_app())

    response = client.get("/", headers={"Host": "127.0.0.1:8000"})

    assert response.status_code == 200
    assert 'id="waitingRoomCode"' in response.text
    assert 'id="copyRoomCodeButton"' in response.text
    assert 'id="waitingSeats"' in response.text
    assert 'id="readyButton"' in response.text
    assert 'id="startRoomButton"' in response.text
    assert 'id="backToLobbyButton"' in response.text
```

- [x] **步骤 2：运行测试验证失败**

运行：`.venv/bin/python -m pytest tests/test_site_routing.py::test_game_page_contains_mobile_lobby_controls tests/test_site_routing.py::test_game_page_contains_mobile_waiting_room_controls -q`

预期：FAIL，缺少 `mobile-lobby-topbar`、`avatarChoiceGrid`、`waitingRoomCode` 或 `copyRoomCodeButton`。

- [x] **步骤 3：暂不实现生产代码**

确认失败后进入任务 2。

### 任务 2：改大厅和等待房 HTML 骨架

**文件：**
- 修改：`src/werewolf_langgraph/static/index.html`

- [x] **步骤 1：调整大厅结构**

将大厅改为手机优先结构：顶部栏、玩家设置区、头像网格、创建按钮、房间列表。

- [x] **步骤 2：调整等待房结构**

加入 `waitingRoomCode`、`copyRoomCodeButton`、状态标签区和底部操作栏。

- [x] **步骤 3：运行任务 1 的测试**

运行：`.venv/bin/python -m pytest tests/test_site_routing.py::test_game_page_contains_mobile_lobby_controls tests/test_site_routing.py::test_game_page_contains_mobile_waiting_room_controls -q`

预期：PASS。

### 任务 3：补头像网格、复制房间码和等待房渲染

**文件：**
- 修改：`src/werewolf_langgraph/static/app.js`
- 测试：`tests/test_frontend_start_feedback.py`

- [x] **步骤 1：编写失败的静态测试**

添加测试，要求存在 `renderAvatarChoices`、`selectedAvatarId`、`copyWaitingRoomCode`、`waiting-seat-grid` 相关逻辑。

- [x] **步骤 2：运行测试验证失败**

运行：`.venv/bin/python -m pytest tests/test_frontend_start_feedback.py -q`

预期：新增测试失败。

- [x] **步骤 3：实现最少 JS**

增加头像按钮渲染；创建/加入房间读取 `selectedAvatarId`；等待房渲染头像、房间码、复制按钮和座位状态。

- [x] **步骤 4：运行相关测试验证通过**

运行：`.venv/bin/python -m pytest tests/test_frontend_start_feedback.py tests/test_site_routing.py -q`

预期：PASS。

### 任务 4：改手机端 CSS 并做浏览器验证

**文件：**
- 修改：`src/werewolf_langgraph/static/styles.css`

- [x] **步骤 1：手机优先样式**

重写大厅和等待房相关 CSS：手机顶部栏、玩家设置、头像网格、房间卡片、等待房 3 x 3 座位、底部固定操作栏。

- [x] **步骤 2：响应式桌面兜底**

在宽屏下让大厅和等待房居中或变成适度双栏，不影响游戏回合内桌面布局。

- [x] **步骤 3：运行完整测试**

运行：`.venv/bin/python -m pytest -q`

预期：全部通过。

- [x] **步骤 4：浏览器验证**

启动本地服务并验证：

- `390 x 844` 手机视口。
- `360 x 740` 小屏手机视口。
- `1280 x 720` 桌面视口。
- 大厅空状态。
- 创建房间后的房主等待房。

预期：大厅和等待房可读、可点，底部操作栏不遮挡座位，现有游戏仍能进入。
