"""
Almacenamiento de listas de tareas por chat (SQLite).
La lista es compartida por todos los que están en el mismo chat (grupo o privado).
"""
import sqlite3
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

DB_PATH = Path(__file__).parent / "todos.db"


LIST_TYPE_HACER = "hacer"
LIST_TYPE_COMPRAR = "comprar"
LIST_TYPE_WISHLIST = "wishlist"


@dataclass
class TodoItem:
    id: int
    chat_id: int
    user_id: int
    text: str
    done: bool
    list_type: str = LIST_TYPE_HACER

    def display(self, index: int) -> str:
        mark = "✅" if self.done else "⬜"
        return f"{index}. {mark} {self.text}"


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Crea la tabla de tareas si no existe. chat_id = lista compartida por chat (grupo o privado)."""
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                list_type TEXT NOT NULL DEFAULT 'hacer',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Migración: añadir list_type si la tabla ya existía sin ella
        try:
            conn.execute("ALTER TABLE todos ADD COLUMN list_type TEXT NOT NULL DEFAULT 'hacer'")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        # Migración: añadir chat_id para listas compartidas por chat (grupo = compartido, privado = personal)
        try:
            conn.execute("ALTER TABLE todos ADD COLUMN chat_id INTEGER")
            conn.commit()
            conn.execute("UPDATE todos SET chat_id = user_id WHERE chat_id IS NULL")
            conn.commit()
        except sqlite3.OperationalError:
            pass
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_todos_chat ON todos(chat_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_todos_chat_list ON todos(chat_id, list_type)"
        )


def add_todo(chat_id: int, user_id: int, text: str, list_type: str = LIST_TYPE_HACER) -> TodoItem:
    """Añade una tarea al chat. list_type: 'hacer' o 'comprar'. user_id = quien la añadió."""
    with _get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO todos (chat_id, user_id, text, done, list_type) VALUES (?, ?, ?, 0, ?)",
            (chat_id, user_id, text.strip(), list_type),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id, chat_id, user_id, text, done, list_type FROM todos WHERE id = ?",
            (cur.lastrowid,),
        ).fetchone()
    return TodoItem(**dict(row))


def list_todos(
    chat_id: int,
    include_done: bool = True,
    list_type: str | None = None,
) -> list[TodoItem]:
    """Lista las tareas del chat. list_type: 'hacer', 'comprar' o None (todas)."""
    with _get_connection() as conn:
        sel = "SELECT id, chat_id, user_id, text, done, list_type FROM todos WHERE chat_id = ?"
        params: list = [chat_id]
        if list_type is not None:
            sel += " AND list_type = ?"
            params.append(list_type)
        if include_done:
            sel += " ORDER BY done, id"
        else:
            sel += " AND done = 0 ORDER BY id"
        rows = conn.execute(sel, params).fetchall()
    return [TodoItem(**dict(r)) for r in rows]


def toggle_todo(chat_id: int, todo_id: int) -> Optional[TodoItem]:
    """Marca o desmarca una tarea. Solo si pertenece al chat."""
    with _get_connection() as conn:
        conn.execute(
            "UPDATE todos SET done = NOT done WHERE id = ? AND chat_id = ?",
            (todo_id, chat_id),
        )
        conn.commit()
        if conn.total_changes == 0:
            return None
        row = conn.execute(
            "SELECT id, chat_id, user_id, text, done, list_type FROM todos WHERE id = ?",
            (todo_id,),
        ).fetchone()
    return TodoItem(**dict(row)) if row else None


def delete_todo(chat_id: int, todo_id: int) -> bool:
    """Elimina una tarea. Devuelve True si existía y era de ese chat."""
    with _get_connection() as conn:
        conn.execute("DELETE FROM todos WHERE id = ? AND chat_id = ?", (todo_id, chat_id))
        conn.commit()
        return conn.total_changes > 0


def get_todo(chat_id: int, todo_id: int) -> Optional[TodoItem]:
    """Obtiene una tarea por id si pertenece al chat."""
    with _get_connection() as conn:
        row = conn.execute(
            "SELECT id, chat_id, user_id, text, done, list_type FROM todos WHERE id = ? AND chat_id = ?",
            (todo_id, chat_id),
        ).fetchone()
    return TodoItem(**dict(row)) if row else None
