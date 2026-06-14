# 1Panel 部署 Werewolf 项目

目标：

- 主站继续使用 `https://roderickdev.cn`
- 狼人杀项目使用 `https://werewolf.roderickdev.cn`
- 由 1Panel 管理容器、反向代理和 HTTPS

## 1. DNS

在域名服务商添加一条解析：

```text
类型: A
主机记录: werewolf
记录值: 你的服务器公网 IP
```

如果主站已经在这台服务器上，记录值通常和 `roderickdev.cn` 相同。

## 2. 上传项目

在 1Panel 的「文件」里创建目录，例如：

```text
/opt/werewolf-game
```

把本项目上传到该目录，确保目录里包含：

```text
Dockerfile
docker-compose.yml
pyproject.toml
setup.py
requirements.txt
src/
```

## 3. 配置环境变量

在项目目录新建 `.env`：

```env
DEEPSEEK_API_KEY=你的 DeepSeek API Key
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

不要把 `.env` 提交到 Git。

## 4. 创建编排项目

进入 1Panel：

1. 打开「容器」->「编排」。
2. 新建编排，选择项目目录 `/opt/werewolf-game`。
3. 使用项目里的 `docker-compose.yml`。
4. 启动编排。

启动后容器会监听服务器本机的 `8000` 端口。

## 5. 创建网站

进入 1Panel：

1. 打开「网站」。
2. 新建网站，域名填写 `werewolf.roderickdev.cn`。
3. 类型选择「反向代理」。
4. 代理地址填写：

```text
http://127.0.0.1:8000
```

5. 保存后申请 SSL 证书，并开启 HTTPS。

## 6. 反向代理配置

如果需要手动检查 Nginx 代理配置，核心配置应类似：

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

## 7. 验证

打开：

```text
https://werewolf.roderickdev.cn
```

应该直接进入狼人杀游戏页。`https://roderickdev.cn` 仍由你的主页网站负责。
