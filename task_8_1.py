import sqlite3
from fastapi import FastAPI
from pydantic import BaseModel
 
DB_PATH = "users_8_1.db"
 
app = FastAPI(title="Task 8.1 — SQLite Register")
 
 
# ── Database helpers ──────────────────────────────────────────────────────────
 
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
 
 
def create_table():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT    NOT NULL,
            password TEXT    NOT NULL
        )
    """)
    conn.commit()
    conn.close()
 
 
# Создаём таблицу при старте приложения
create_table()
 
 
# ── Model ─────────────────────────────────────────────────────────────────────
 
class User(BaseModel):
    username: str
    password: str
 
 
# ── Endpoint ──────────────────────────────────────────────────────────────────
 
@app.post("/register")
def register(user: User):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        (user.username, user.password),
    )
    conn.commit()
    conn.close()
    return {"message": "User registered successfully!"}