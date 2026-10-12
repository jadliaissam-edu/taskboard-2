import json
import os
import socket
import time
from contextlib import contextmanager

import pymysql
import redis
from flask import Flask, jsonify, request


def env(name, default=None):
    """Read NAME, or the content of the file pointed by NAME_FILE (Docker secrets)."""
    if path := os.getenv(f"{name}_FILE"):
        with open(path) as f:
            return f.read().strip()
    return os.getenv(name, default)


DB = dict(
    host=env("DB_HOST", "db"),
    port=int(env("DB_PORT", "3306")),
    user=env("DB_USER", "taskboard"),
    password=env("DB_PASSWORD", ""),
    database=env("DB_NAME", "taskboard"),
    cursorclass=pymysql.cursors.DictCursor,
    autocommit=True,
    connect_timeout=3,
)
CACHE_KEY, CACHE_TTL = "tasks:all", 30

app = Flask(__name__)
cache = redis.Redis(host=env("REDIS_HOST", "redis"), port=int(env("REDIS_PORT", "6379")),
                    decode_responses=True, socket_connect_timeout=2)


@contextmanager
def db_cursor(retries=5):
    # The DB may start after the API (Swarm ignores depends_on): retry with backoff.
    for attempt in range(retries):
        try:
            conn = pymysql.connect(**DB)
            break
        except pymysql.err.OperationalError:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt * 0.5)
    try:
        with conn.cursor() as cur:
            yield cur
    finally:
        conn.close()


def invalidate():
    cache.delete(CACHE_KEY)


@app.get("/api/health")
def health():
    status = {}
    try:
        with db_cursor(retries=1) as cur:
            cur.execute("SELECT 1")
        status["db"] = "ok"
    except Exception as e:
        status["db"] = str(e)
    try:
        cache.ping()
        status["redis"] = "ok"
    except Exception as e:
        status["redis"] = str(e)
    healthy = all(v == "ok" for v in status.values()) and not os.getenv("FAIL_HEALTH")
    return jsonify(status=("ok" if healthy else "error"), **status), 200 if healthy else 503


@app.get("/api/info")
def info():
    return jsonify(
        hostname=socket.gethostname(),
        version=os.getenv("APP_VERSION", "dev"),
        hits=cache.incr("hits"),
    )


@app.get("/api/tasks")
def list_tasks():
    if cached := cache.get(CACHE_KEY):
        return jsonify(tasks=json.loads(cached), source="cache")
    with db_cursor() as cur:
        cur.execute("SELECT id, title, done, created_at FROM tasks ORDER BY id DESC")
        tasks = cur.fetchall()
    for t in tasks:
        t["done"], t["created_at"] = bool(t["done"]), t["created_at"].isoformat()
    cache.setex(CACHE_KEY, CACHE_TTL, json.dumps(tasks))
    return jsonify(tasks=tasks, source="db")


@app.post("/api/tasks")
def create_task():
    title = (request.get_json(silent=True) or {}).get("title", "").strip()
    if not title:
        return jsonify(error="title is required"), 400
    with db_cursor() as cur:
        cur.execute("INSERT INTO tasks (title) VALUES (%s)", (title[:255],))
        task_id = cur.lastrowid
    invalidate()
    return jsonify(id=task_id, title=title, done=False), 201


@app.patch("/api/tasks/<int:task_id>")
def toggle_task(task_id):
    with db_cursor() as cur:
        updated = cur.execute("UPDATE tasks SET done = NOT done WHERE id = %s", (task_id,))
    invalidate()
    return ("", 204) if updated else (jsonify(error="not found"), 404)


@app.delete("/api/tasks/<int:task_id>")
def delete_task(task_id):
    with db_cursor() as cur:
        deleted = cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    invalidate()
    return ("", 204) if deleted else (jsonify(error="not found"), 404)
