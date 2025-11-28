import sqlite3

import pandas as pd
import streamlit as st
from streamlit_calendar import calendar

from lib import projects as projects_lib
from lib.constants import DB_PATH


def _time_with_seconds(t: str) -> str:
    # Accept HH:MM or HH:MM:SS, return HH:MM:SS
    if not t:
        return "00:00:00"
    parts = t.split(":")
    if len(parts) == 2:
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:00"
    if len(parts) == 3:
        return f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:{parts[2].zfill(2)}"
    # fallback
    return t


def load_timesheets(conn: sqlite3.Connection) -> pd.DataFrame:
    try:
        df = pd.read_sql_query(
            "SELECT id, date, todo, title, description, start_time, end_time FROM timesheets",
            conn,
        )
    except Exception:
        df = pd.DataFrame()
    return df


def build_resources(projects_df: pd.DataFrame) -> list:
    resources = []
    if projects_df is None or projects_df.empty:
        return resources
    # projects_df has index todo_id and column 'title'
    for todo_id, row in projects_df.iterrows():
        # Show TODO id prominently in the resource column, include project title after it
        project_title = str(row.get("title", ""))
        display_title = (
            f"{todo_id} - {project_title}" if project_title else str(todo_id)
        )
        resources.append({"id": str(todo_id), "group": "todos", "title": display_title})
    return resources


def build_events(times_df: pd.DataFrame) -> list:
    events = []
    if times_df is None or times_df.empty:
        return events
    for _, row in times_df.iterrows():
        date = str(row.get("date", ""))
        start = _time_with_seconds(str(row.get("start_time", "")))
        end = _time_with_seconds(str(row.get("end_time", "")))
        # If date missing or times malformed, skip
        if not date or not start or not end:
            continue
        start_iso = f"{date}T{start}"
        end_iso = f"{date}T{end}"
        # If end is earlier than start assume next day
        try:
            start_dt = pd.to_datetime(start_iso)
            end_dt = pd.to_datetime(end_iso)
            if end_dt <= start_dt:
                end_dt = end_dt + pd.Timedelta(days=1)
                end_iso = end_dt.isoformat()
            else:
                end_iso = end_dt.isoformat()
            start_iso = start_dt.isoformat()
        except Exception:
            # fallback to raw strings
            pass

        resource_id = row.get("todo") or None
        title = row.get("title") or row.get("description") or "Timesheet Entry"
        events.append(
            {
                "title": str(title),
                "start": start_iso,
                "end": end_iso,
                "resourceId": str(resource_id) if resource_id else None,
            }
        )
    # Filter out events without resourceId to avoid mapping issues (optional)
    return [e for e in events if e.get("start")]


if __name__ == "__main__":
    st.set_page_config(page_title="Calendar View", layout="wide")

    # Connect to DB and load data
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    times_df = load_timesheets(conn)
    projects_df = projects_lib.get_projects(conn)

    resources = build_resources(projects_df)
    # include any todos referenced in timesheets that are not in projects
    if not times_df.empty:
        for todo in times_df["todo"].dropna().unique():
            if not any(r["id"] == str(todo) for r in resources):
                resources.append(
                    {"id": str(todo), "group": "todos", "title": str(todo)}
                )

    calendar_options = {
        "editable": False,
        "selectable": True,
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "",
        },
        "slotMinTime": "06:00:00",
        "slotMaxTime": "19:00:00",
        "initialView": "resourceTimelineDay",
        "resources": resources,
        "height": 500,
    }

    calendar_events = build_events(times_df)

    custom_css = """
        .fc-event-past { opacity: 0.8; }
        .fc-event-time { font-style: italic; }
        .fc-event-title { font-weight: 700; }
        .fc-toolbar-title { font-size: 2rem; }
    """

    calendar_widget = calendar(
        events=calendar_events,
        options=calendar_options,
        custom_css=custom_css,
        key="calendar",
    )
    # st.write(calendar_widget)
