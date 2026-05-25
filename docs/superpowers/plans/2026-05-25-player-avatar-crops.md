# Player Avatar Crops 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 从用户提供的整图裁出 8 个角色头像，并在游戏开始后的玩家卡片中按名字显示。

**架构：** 头像作为静态资源保存在 `static/assets/avatars/`。前端在 `app.js` 中使用名字到文件名的映射，`renderPlayers()` 生成图片节点，CSS 控制统一的圆角卡片头像尺寸。

**技术栈：** Python/Pillow 图像裁剪、FastAPI 静态资源、原生 HTML/CSS/JavaScript、pytest 源码测试。

---

### 任务 1：测试头像映射和玩家卡片渲染

**文件：**
- 修改：`tests/test_frontend_start_feedback.py`
- 修改：`src/werewolf_langgraph/static/app.js`
- 修改：`src/werewolf_langgraph/static/styles.css`

- [ ] **步骤 1：编写失败的测试**

```python
def test_player_avatar_mapping_and_rendering_exist():
    source = APP_JS.read_text(encoding="utf-8")
    css = APP_JS.with_name("styles.css").read_text(encoding="utf-8")
    for name in ["柯南", "哆啦A梦", "蜡笔小新", "海绵宝宝", "小猪佩奇", "猪猪侠", "懒羊羊", "奶龙"]:
        assert name in source
    assert "function avatarForPlayer(player)" in source
    assert 'className = "player-avatar"' in source
    assert ".player-avatar" in css
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/test_frontend_start_feedback.py::test_player_avatar_mapping_and_rendering_exist -q`
预期：FAIL，原因是头像映射和样式尚不存在。

- [ ] **步骤 3：实现最少前端代码**

在 `app.js` 中添加 `playerAvatarMap`、`avatarForPlayer()`，并在 `renderPlayers()` 中渲染 `<img class="player-avatar">`。在 `styles.css` 中添加 `.player-avatar` 尺寸、圆角和边框样式。

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/test_frontend_start_feedback.py::test_player_avatar_mapping_and_rendering_exist -q`
预期：PASS。

### 任务 2：裁剪并验证头像资源

**文件：**
- 创建：`src/werewolf_langgraph/static/assets/avatars/conan.webp`
- 创建：`src/werewolf_langgraph/static/assets/avatars/doraemon.webp`
- 创建：`src/werewolf_langgraph/static/assets/avatars/shinchan.webp`
- 创建：`src/werewolf_langgraph/static/assets/avatars/spongebob.webp`
- 创建：`src/werewolf_langgraph/static/assets/avatars/peppa.webp`
- 创建：`src/werewolf_langgraph/static/assets/avatars/ggbond.webp`
- 创建：`src/werewolf_langgraph/static/assets/avatars/lazy-yangyang.webp`
- 创建：`src/werewolf_langgraph/static/assets/avatars/nailong.webp`
- 修改：`tests/test_frontend_start_feedback.py`

- [ ] **步骤 1：编写失败的资源存在测试**

```python
def test_player_avatar_assets_exist():
    avatar_dir = APP_JS.with_name("assets") / "avatars"
    for filename in ["conan.webp", "doraemon.webp", "shinchan.webp", "spongebob.webp", "peppa.webp", "ggbond.webp", "lazy-yangyang.webp", "nailong.webp"]:
        assert (avatar_dir / filename).exists()
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/test_frontend_start_feedback.py::test_player_avatar_assets_exist -q`
预期：FAIL，原因是资源文件尚不存在。

- [ ] **步骤 3：裁剪源图**

使用 Pillow 从 `C:/Users/27127/Downloads/IMG_20260525_121359.jpg` 按 2 行 4 列裁出 8 张头像，保留每张卡片的白色圆角边框，输出 WebP 到头像资源目录。

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/test_frontend_start_feedback.py::test_player_avatar_assets_exist -q`
预期：PASS。

### 任务 3：整体验证

**文件：**
- 修改：`src/werewolf_langgraph/static/app.js`
- 修改：`src/werewolf_langgraph/static/styles.css`
- 创建：`src/werewolf_langgraph/static/assets/avatars/*.webp`

- [ ] **步骤 1：运行相关测试**

运行：`pytest tests/test_frontend_start_feedback.py tests/test_room_setup.py -q`
预期：全部通过。

- [ ] **步骤 2：本地浏览器验证**

启动 Web 应用，打开本地页面，创建房间后检查玩家卡片头像显示、文字不溢出、九宫格布局在桌面宽度下稳定。
