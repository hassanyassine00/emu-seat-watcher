"""app.py — browser UI for the class search. Run: streamlit run app.py"""

import streamlit as st

from watcher import (
    make_session,
    fetch_sections,
    open_seats,
    meeting_info,
)

TERM = "202710"      # Fall 2026
REGISTER_URL = "https://bannerweb.oci.emich.edu/StudentRegistrationSsb/ssb/registration"

DAY_LETTERS = {
    "Monday": "MON",
    "Tuesday": "TUE",
    "Wednesday": "WED",
    "Thursday": "THU",
    "Friday": "FRI",
}

st.title("EMU Class Search")

col1, col2 = st.columns(2)
subject = col1.text_input("Subject", "COSC").strip().upper()
number = col2.text_input("Course number", "411").strip().upper()

chosen_days = st.multiselect("Days (leave empty for any)", list(DAY_LETTERS))
earliest, latest = st.select_slider(
    "Time range",
    options=list(range(600, 2300, 100)),
    value=(600, 2200),
    format_func=lambda t: f"{t // 100}:00",
)

if st.button("Search"):
    wanted = [DAY_LETTERS[d] for d in chosen_days]

    with st.spinner("Asking Banner..."):
        try:
            session = make_session(TERM)
            sections = fetch_sections(session, TERM, subject, number)
        except Exception as error:
            st.error(f"Search failed: {error}")
            sections = []

    rows = []
    for section in sections:
        info = meeting_info(section)

        if info is None:
            days, begin, end, when = [], None, None, "Not scheduled"
        else:
            days, begin, end = info
            when = f"{'/'.join(days)} {begin:04d}-{end:04d}"

        if wanted and not any(d in wanted for d in days):
            continue
        if begin is not None and (begin < earliest or end > latest):
            continue

        rows.append({
            "CRN": section["courseReferenceNumber"],
            "Course": section["subjectCourse"],
            "Open seats": open_seats(section),
            "Meets": when,
        })

    if not sections:
        st.warning("No sections found for that course.")
    elif not rows:
        st.info("No sections match those filters.")
    else:
        st.dataframe(rows, width="stretch")
        st.link_button("Open registration", REGISTER_URL)