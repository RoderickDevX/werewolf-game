# Werewolf Multi-Agent

Goal: use LangGraph to orchestrate multiple AI players for a Werewolf game, and let you join from a web page as the human player.

## Development Roadmap

We followed these five steps:

1. Build the basic environment and connect DeepSeek.
2. Design the global game `State` data structure.
3. Develop independent role agent nodes, `Agents`.
4. Use LangGraph to orchestrate the game flow.
5. Build the Web backend, `FastAPI`, and frontend interaction.

## Current Progress

Current step: Step 5, Web backend and frontend interaction.

Completed:

- Step 1: DeepSeek config loading and connectivity check
- Step 2: core game state structures
- Step 3: independent role agent nodes
- Step 4: LangGraph game flow orchestration
- Step 5: FastAPI backend and browser UI MVP
- Room creation API
- Room status API
- Human speech API
- Human vote API
- LangGraph run API
- Static frontend page

## Run

Install dependencies:

```powershell
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -e .
```

Configure `.env`:

```powershell
cp .env.example .env
```

```env
DEEPSEEK_API_KEY=your DeepSeek API key
DEEPSEEK_MODEL=deepseek-v4-flash
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

Start the web app:

```powershell
python -m werewolf_langgraph
```

Open:

```text
http://127.0.0.1:8000
```

## Test

Install development dependencies:

```powershell
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements-dev.txt
pip install -e .
```

Run the test suite:

```powershell
pytest -q
```

## Deploy With 1Panel

If you want others to visit the game through `werewolf.roderickdev.cn`, run the app on the server and put a reverse proxy in front of it. See `docs/1panel-deploy.md` for the full 1Panel setup.

Recommended setup:

1. Run the app on localhost or in Docker:

```powershell
python -m werewolf_langgraph --host 127.0.0.1 --port 8000
```

2. Point Nginx at it:

```nginx
server {
    listen 80;
    server_name werewolf.roderickdev.cn;

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
}
```

With DNS already set to the server, opening `https://werewolf.roderickdev.cn` will reach this game after you reload Nginx and add HTTPS.

## Files

- DeepSeek config: `src/werewolf_langgraph/config.py`
- DeepSeek client: `src/werewolf_langgraph/deepseek.py`
- State: `src/werewolf_langgraph/state.py`
- Agents: `src/werewolf_langgraph/agents.py`
- LangGraph flow: `src/werewolf_langgraph/game_graph.py`
- Web app: `src/werewolf_langgraph/web.py`
- Frontend: `src/werewolf_langgraph/static/`

## Current Web MVP Limits

The page can create a room, show your role, submit speech, submit vote, and run the LangGraph backend.

Human werewolf, seer, witch, and hunter actions pause for browser input. Rooms are stored in memory, so active rooms disappear when the server restarts; use a persistent store before treating multiplayer rooms as production durable.
