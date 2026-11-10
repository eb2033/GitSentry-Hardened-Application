"""Minimal items API. All configuration comes from environment variables."""
import os
import sys
from contextlib import contextmanager

import psycopg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

REQUIRED_ENV = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD")


def load_config() -> dict:
    missing = [k for k in REQUIRED_ENV if not os.environ.get(k)]
    if missing:
        sys.exit(f"Missing required environment variables: {', '.join(missing)}")
    return {k: os.environ[k] for k in REQUIRED_ENV}


CONFIG = load_config()


@contextmanager
def connect():
    with psycopg.connect(
        host=CONFIG["DB_HOST"],
        port=CONFIG["DB_PORT"],
        dbname=CONFIG["DB_NAME"],
        user=CONFIG["DB_USER"],
        password=CONFIG["DB_PASSWORD"],
        connect_timeout=5,
    ) as conn:
        yield conn


def init_db() -> None:
    with connect() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS items ("
            "id SERIAL PRIMARY KEY, name TEXT NOT NULL)"
        )


class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)


app = FastAPI(title="GitSentry items API")


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/items")
def list_items() -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT id, name FROM items ORDER BY id").fetchall()
    return [{"id": r[0], "name": r[1]} for r in rows]


@app.post("/items", status_code=201)
def create_item(item: ItemIn) -> dict:
    with connect() as conn:
        row = conn.execute(
            "INSERT INTO items (name) VALUES (%s) RETURNING id, name", (item.name,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=500, detail="insert failed")
    return {"id": row[0], "name": row[1]}
