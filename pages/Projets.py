import sqlite3
from pathlib import Path

import streamlit as st

from lib.constants import DB_PATH
from lib.projects import add_project, get_projects


def ensure_db_parent():
    p = Path(DB_PATH)
    if not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)


def get_conn():
    ensure_db_parent()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn


def init_projects_table(conn: sqlite3.Connection):
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            todo_id TEXT UNIQUE,
            title TEXT
        )
        """
    )
    conn.commit()


def projects():
    st.title("Projects")

    conn = get_conn()
    init_projects_table(conn)

    st.header("Add Project")
    col1, col2 = st.columns([2, 4])
    with col1:
        todo_id = st.text_input("TODO id (e.g. TODO-123)")
    with col2:
        title = st.text_input("Project title")

    if st.button("Add Project"):
        if not todo_id.strip():
            st.error("Please provide a TODO id.")
        elif not title.strip():
            st.error("Please provide a project title.")
        else:
            try:
                add_project(conn, todo_id.strip(), title.strip())
                st.success("Project added")
            except sqlite3.IntegrityError:
                st.error("A project with that TODO id already exists.")
            except Exception as e:
                st.error(f"Error adding project: {e}")

    st.header("All Projects")
    df = get_projects(conn)
    if df.empty:
        st.info("No projects added yet.")
    else:
        st.dataframe(df[["title"]])


if __name__ == "__main__":
    projects()
