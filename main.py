import streamlit as st

pg = st.navigation(
    {
        "Timesheet": [
            st.Page(
                title="Home",
                page="pages/Home.py",
                icon=":material/home:",
            ),
            st.Page(
                title="Projects",
                page="pages/Projects.py",
                icon=":material/folder:",
            ),
            st.Page(
                title="Calendar",
                page="pages/Calendar.py",
                icon=":material/calendar_today:",
            ),
        ],
    },
)

pg.run()
