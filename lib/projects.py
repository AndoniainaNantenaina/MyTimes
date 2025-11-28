import sqlite3

import pandas as pd


def get_projects(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql_query("SELECT id, todo_id, title FROM projects ORDER BY todo_id", conn)
    if not df.empty:
        df.set_index("todo_id", inplace=True)
    return df


def add_project(conn: sqlite3.Connection, todo_id: str, title: str) -> int:
    c = conn.cursor()
    c.execute("INSERT INTO projects (todo_id, title) VALUES (?, ?)", (todo_id, title))
    conn.commit()
    return c.lastrowid
