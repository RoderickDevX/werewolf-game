FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WEREWOLF_HOST=0.0.0.0 \
    WEREWOLF_PORT=8000

WORKDIR /app

COPY requirements.txt pyproject.toml setup.py README.md ./
COPY src ./src

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir .

EXPOSE 8000

CMD ["python", "-m", "werewolf_langgraph"]
