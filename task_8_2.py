import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
 
DB_PATH = "todos.db"
 
app = FastAPI(title="Task 8.2 — Todo CRUD")
 
 
# ── DB setup ──────────────────────────────────────────────────────────────────
 
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
 
 
def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            description TEXT    NOT NULL DEFAULT '',
            completed   INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
 
 
init_db()
 
 
# ── Models ────────────────────────────────────────────────────────────────────
 
class TodoCreate(BaseModel):
    title: str
    description: str = ""
 
 
class TodoUpdate(BaseModel):
    title: str
    description: str
    completed: bool
 
 
class TodoOut(BaseModel):
    id: int
    title: str
    description: str
    completed: bool
 
 
def row_to_todo(row) -> TodoOut:
    return TodoOut(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        completed=bool(row["completed"]),
    )
 
 
# ── CRUD endpoints ────────────────────────────────────────────────────────────
 
@app.post("/todos", status_code=201, response_model=TodoOut)
def create_todo(data: TodoCreate):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO todos (title, description) VALUES (?, ?)",
        (data.title, data.description),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM todos WHERE id = ?", (cursor.lastrowid,)).fetchone()
    conn.close()
    return row_to_todo(row)
 
 
@app.get("/todos/{todo_id}", response_model=TodoOut)
def get_todo(todo_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Todo not found")
    return row_to_todo(row)
 
 
@app.put("/todos/{todo_id}", response_model=TodoOut)
def update_todo(todo_id: int, data: TodoUpdate):
    conn = get_db()
    row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Todo not found")
    conn.execute(
        "UPDATE todos SET title=?, description=?, completed=? WHERE id=?",
        (data.title, data.description, int(data.completed), todo_id),
    )
    conn.commit()
    updated = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    conn.close()
    return row_to_todo(updated)
 
 
@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int):
    conn = get_db()
    row = conn.execute("SELECT id FROM todos WHERE id = ?", (todo_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Todo not found")
    conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    conn.commit()
    conn.close()
    return {"message": f"Todo {todo_id} deleted successfully"}
 