"""EMU seat watcher — Session 3: fetch and print seat counts for one course."""

import requests

BASE = "https://bannerweb.oci.emich.edu/StudentRegistrationSsb/ssb"
TERM = "202710"      # Fall 2026
SUBJECT = "COSC"
COURSE_NUMBER = "411"


def make_session(term):
    """Open a session and tell Banner which term we're looking at."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "emu-seat-watcher (student project)"
    })
    # Banner won't return results until a term is selected on the session.
    session.post(
        f"{BASE}/term/search",
        params={"mode": "search"},
        data={"term": term},
        timeout=20,
    )
    return session


def fetch_sections(session, term, subject, course_number):
    """Return the list of section records for one course."""
    session.get(f"{BASE}/classSearch/resetDataForm", timeout=20)
    response = session.get(
        f"{BASE}/searchResults/searchResults",
        params={
            "txt_subject": subject,
            "txt_courseNumber": course_number,
            "txt_term": term,
            "pageOffset": 0,
            "pageMaxSize": 50,
        },
        timeout=20,
    )
    response.raise_for_status()
    return response.json().get("data", [])


def open_seats(section):
    """Seats you could actually register into, respecting cross-lists."""
    seats = section["seatsAvailable"]
    if section.get("crossList") is not None:
        seats = min(seats, section["crossListAvailable"])
    return seats


if __name__ == "__main__":
    session = make_session(TERM)
    sections = fetch_sections(session, TERM, SUBJECT, COURSE_NUMBER)

    if not sections:
        print("No sections returned — the term selection probably didn't take.")

    for section in sections:
        crn = section["courseReferenceNumber"]
        print(
            f"{section['subjectCourse']} CRN {crn}: "
            f"{open_seats(section)} open "
            f"(section {section['seatsAvailable']}, "
            f"cross-list {section['crossListAvailable']})"
        )