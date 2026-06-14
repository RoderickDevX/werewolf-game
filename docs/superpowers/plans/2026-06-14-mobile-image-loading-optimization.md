# Mobile Image Loading Optimization 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 让手机端打开狼人杀页面时图片加载更快，重点优化静态资源缓存、大背景图和加菲猫头像。

**架构：** FastAPI 中间件继续禁止 HTML/API 缓存，但对 `/static` 返回长期缓存头。前端引用改为更小的 WebP 资源，旧 PNG 保留以降低兼容风险。测试覆盖缓存策略、资源引用和打包清单。

**技术栈：** Python 3, FastAPI, Starlette StaticFiles, pytest, browser-served static HTML/CSS/JS, macOS `sips`/可用图片工具。

---

## 文件结构

- 修改 `src/werewolf_langgraph/web.py`：调整 `no_cache_middleware`，让 `/static` 使用 cacheable header。
- 修改 `src/werewolf_langgraph/static/styles.css`：游戏背景引用 `game-mobile-character-background.webp`。
- 修改 `src/werewolf_langgraph/static/app.js`：Garfield 头像引用 `garfield.webp`。
- 创建 `src/werewolf_langgraph/static/assets/game-mobile-character-background.webp`：优化后的游戏背景。
- 创建 `src/werewolf_langgraph/static/assets/avatars/garfield.webp`：优化后的加菲猫头像。
- 修改 `tests/test_web_runtime_config.py`：新增缓存策略测试。
- 修改 `tests/test_frontend_start_feedback.py`：更新图片引用断言。
- 修改 `tests/test_package_static_assets.py`：确保新 WebP 资产被打包。

## 任务 1：缓存策略测试和实现

**文件：**
- 修改：`tests/test_web_runtime_config.py`
- 修改：`src/werewolf_langgraph/web.py`

- [ ] **步骤 1：编写失败的缓存策略测试**

在 `tests/test_web_runtime_config.py` 增加测试：

```python
def test_static_assets_are_cacheable_while_html_and_api_remain_no_store():
    client = TestClient(web.create_app())

    html_response = client.get("/", headers={"host": "werewolf.roderickdev.cn"})
    assert "no-store" in html_response.headers["Cache-Control"]

    api_response = client.get("/api/rooms")
    assert "no-store" in api_response.headers["Cache-Control"]

    static_response = client.get("/static/assets/avatars/shinchan.webp")
    assert static_response.status_code == 200
    assert "no-store" not in static_response.headers["Cache-Control"]
    assert "public" in static_response.headers["Cache-Control"]
    assert "max-age=" in static_response.headers["Cache-Control"]
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/test_web_runtime_config.py::test_static_assets_are_cacheable_while_html_and_api_remain_no_store -v`

预期：FAIL，静态资源仍包含 `no-store`。

- [ ] **步骤 3：实现缓存策略**

在 `src/werewolf_langgraph/web.py` 的 `no_cache_middleware` 中按路径分支：

```python
    @app.middleware("http")
    async def no_cache_middleware(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            response.headers.pop("Pragma", None)
            response.headers.pop("Expires", None)
            return response
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/test_web_runtime_config.py::test_static_assets_are_cacheable_while_html_and_api_remain_no_store -v`

预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add tests/test_web_runtime_config.py src/werewolf_langgraph/web.py
git commit -m "fix: cache static image assets"
```

## 任务 2：优化图片资产并更新引用

**文件：**
- 创建：`src/werewolf_langgraph/static/assets/game-mobile-character-background.webp`
- 创建：`src/werewolf_langgraph/static/assets/avatars/garfield.webp`
- 修改：`src/werewolf_langgraph/static/styles.css`
- 修改：`src/werewolf_langgraph/static/app.js`

- [ ] **步骤 1：生成 WebP 资产**

使用本机可用图片工具从现有 PNG 生成 WebP。目标结果：

- `game-mobile-character-background.webp` 明显小于 `game-mobile-character-background.png`。
- `avatars/garfield.webp` 明显小于 `avatars/garfield.png`。
- 图片尺寸保持可用于当前 CSS/头像布局。

可用命令示例：

```bash
sips -s format webp src/werewolf_langgraph/static/assets/game-mobile-character-background.png --out src/werewolf_langgraph/static/assets/game-mobile-character-background.webp
sips -s format webp src/werewolf_langgraph/static/assets/avatars/garfield.png --out src/werewolf_langgraph/static/assets/avatars/garfield.webp
```

- [ ] **步骤 2：更新前端引用**

在 `src/werewolf_langgraph/static/styles.css` 中替换：

```css
url("/static/assets/game-mobile-character-background.png") center top / cover;
```

为：

```css
url("/static/assets/game-mobile-character-background.webp") center top / cover;
```

在 `src/werewolf_langgraph/static/app.js` 中替换 Garfield 分支：

```javascript
if (avatar.id === "garfield") return "/static/assets/avatars/garfield.webp";
```

- [ ] **步骤 3：人工检查资产体积**

运行：`find src/werewolf_langgraph/static/assets -name '*game-mobile-character-background*' -o -name 'garfield.*' -exec ls -lh {} +`

预期：新 WebP 文件存在，且比对应 PNG 小。

- [ ] **步骤 4：Commit**

```bash
git add src/werewolf_langgraph/static/assets/game-mobile-character-background.webp src/werewolf_langgraph/static/assets/avatars/garfield.webp src/werewolf_langgraph/static/styles.css src/werewolf_langgraph/static/app.js
git commit -m "fix: use optimized webp image assets"
```

## 任务 3：更新前端和打包测试

**文件：**
- 修改：`tests/test_frontend_start_feedback.py`
- 修改：`tests/test_package_static_assets.py`

- [ ] **步骤 1：更新失败的引用测试**

在 `tests/test_frontend_start_feedback.py` 中更新旧断言：

```python
assert 'url("/static/assets/game-mobile-character-background.webp")' in css
assert 'if (avatar.id === "garfield") return "/static/assets/avatars/garfield.webp";' in source
```

并将旧的 PNG 引用断言替换为 WebP 引用断言。

- [ ] **步骤 2：更新打包资产测试**

在 `tests/test_package_static_assets.py` 的 expected assets 中加入：

```python
"werewolf_langgraph/static/assets/game-mobile-character-background.webp",
"werewolf_langgraph/static/assets/avatars/garfield.webp",
```

- [ ] **步骤 3：运行相关测试**

运行：

```bash
pytest tests/test_frontend_start_feedback.py tests/test_package_static_assets.py tests/test_web_runtime_config.py -v
```

预期：PASS。

- [ ] **步骤 4：运行更广测试**

运行：`pytest -q`

预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add tests/test_frontend_start_feedback.py tests/test_package_static_assets.py
git commit -m "test: cover optimized image assets"
```
