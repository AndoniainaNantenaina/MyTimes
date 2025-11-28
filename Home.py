import datetime
import os
import sqlite3
from typing import Optional

import pandas as pd
import streamlit as st

from lib import projects as projects_lib
from lib.constants import DB_PATH

# Ensure the directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db(path: str = DB_PATH):
    conn = sqlite3.connect(path, check_same_thread=False)
    c = conn.cursor()
    c.execute(
        """
		CREATE TABLE IF NOT EXISTS timesheets (
			id INTEGER PRIMARY KEY,
			date TEXT,
            todo TEXT,
			title TEXT,
			description TEXT,
			start_time TEXT,
			end_time TEXT,
			duration TEXT
		)
		"""
    )
    conn.commit()
    return conn


def parse_time(tstr: str) -> datetime.time:
    tstr = (tstr or "").strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.datetime.strptime(tstr, fmt).time()
        except Exception:
            continue
    raise ValueError(f"Time '{tstr}' is not in a supported format")


def compute_duration(start_str: str, end_str: str) -> str:
    start_t = parse_time(start_str)
    end_t = parse_time(end_str)
    base = datetime.date(2000, 1, 1)
    start_dt = datetime.datetime.combine(base, start_t)
    end_dt = datetime.datetime.combine(base, end_t)
    if end_dt < start_dt:
        # assume end on next day
        end_dt += datetime.timedelta(days=1)
    delta = end_dt - start_dt
    total_seconds = int(delta.total_seconds())
    hours, rem = divmod(total_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def add_entry(
    conn: sqlite3.Connection,
    date: str,
    todo: str,
    title: str,
    description: str,
    start: str,
    end: str,
):
    duration = compute_duration(start, end)
    c = conn.cursor()
    c.execute(
        "INSERT INTO timesheets (date, todo, title, description, start_time, end_time, duration) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (date, todo, title, description, start, end, duration),
    )
    conn.commit()
    return c.lastrowid


def get_entries(conn: sqlite3.Connection, date: Optional[str] = None) -> pd.DataFrame:
    if date:
        df = pd.read_sql_query(
            "SELECT id, date, todo, title, description, start_time, end_time, duration FROM timesheets WHERE date = ? ORDER BY start_time",
            conn,
            params=(date,),
        )
    else:
        df = pd.read_sql_query(
            "SELECT id, date, todo, title, description, start_time, end_time, duration FROM timesheets ORDER BY date, start_time",
            conn,
        )
    return df


def sum_durations(duration_series: pd.Series) -> str:
    total_seconds = 0
    for d in duration_series.dropna():
        try:
            h, m, s = [int(x) for x in d.split(":")]
            total_seconds += h * 3600 + m * 60 + s
        except Exception:
            continue
    h, rem = divmod(total_seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def main():
    st.set_page_config(page_title="Daily Timesheet", layout="wide")
    st.title("Daily Timesheet")

    conn = init_db()

    st.header("Add Timesheet Entry")
    entry_date = st.date_input("Date", value=datetime.date.today())

    # Load projects and provide a dropdown to pick an existing project.
    # When a project is selected, autofill the TODO and title fields.
    try:
        projects_df = projects_lib.get_projects(sqlite3.connect(DB_PATH, check_same_thread=False))
    except Exception:
        projects_df = pd.DataFrame()

    project_options = ["(new project)"]
    if not projects_df.empty:
        # `get_projects` sets index to `todo_id`
        project_options += list(projects_df.index.astype(str))

    selected_project = st.selectbox("Select project (choose to autofill TODO/title)", project_options)

    if selected_project != "(new project)" and not projects_df.empty:
        todo_default = selected_project
        # safe access in case of single-row Series
        try:
            title_default = projects_df.loc[selected_project, "title"]
        except Exception:
            # if loc returns a Series when reset_index wasn't used
            title_default = projects_df.loc[selected_project]["title"]
    else:
        todo_default = ""
        title_default = ""

    col1, col2, col3, col4, col5 = st.columns([1, 2, 3, 1, 1])
    with col1:
        todo = st.text_input("TODO", value=todo_default, max_chars=200, placeholder="TODO-123")
    with col2:
        title = st.text_input("Task Title", value=title_default, max_chars=200)
    with col3:
        description = st.text_input("Task Description", max_chars=500)
    with col4:
        start_time = st.text_input("Start Time (HH:MM)", value="08:00")
    with col5:
        end_time = st.text_input("End Time (HH:MM)", value="09:00")

    # show computed duration live
    try:
        duration_preview = compute_duration(start_time, end_time)
        st.markdown(f"**Duration:** {duration_preview}")
    except Exception as e:
        st.markdown(f"**Duration:** — (enter valid start and end times) (`{e}`)")

    if st.button("Add Entry", disabled=not all([todo, title, start_time, end_time])):
        if not title.strip():
            st.error("Please enter a task title.")
        else:
            try:
                iso_date = entry_date.isoformat()
                add_entry(
                    conn,
                    iso_date,
                    todo.strip(),
                    title.strip(),
                    description.strip(),
                    start_time.strip(),
                    end_time.strip(),
                )
                st.success("Entry added")
            except Exception as e:
                st.error(f"Failed to add entry: {e}")

    st.header("View Timesheets")
    view_col1, view_col2 = st.columns([1, 3])
    with view_col1:
        filter_date = st.date_input(
            "Filter by date", value=datetime.date.today(), key="filter_date"
        )
        show_all = st.checkbox("Show all dates")
        if st.button("Refresh"):
            st.rerun()

    with view_col2:
        if show_all:
            df = get_entries(conn, None)
        else:
            df = get_entries(conn, filter_date.isoformat())

        if df.empty:
            st.info("No entries found for the selected date")
        else:
            display_df = df.copy()
            display_df["date"] = pd.to_datetime(display_df["date"]).dt.date
            st.dataframe(display_df.reset_index(drop=True))
            total = sum_durations(display_df["duration"])
            st.markdown(f"**Total time:** {total}")


if __name__ == "__main__":
    main()
