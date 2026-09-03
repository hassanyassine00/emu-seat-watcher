"""EMU seat watcher — print seat counts for the courses in courses.json."""

import json
import time
from pathlib import Path

import requests

BASE = "https://bannerweb.oci.emich.edu/StudentRegistrationSsb/ssb"


def make_session(term, attempts=3):
    """Open a session and tell Banner which term we're looking at."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "emu-seat-watcher (student project)"
    })

    # The campus network drops lookups occasionally, so retry before failing.
    for attempt in range(1, attempts + 1):
        try:
            session.post(
                f"{BASE}/term/search",
                params={"mode": "search"},
                data={"term": term},
                timeout=20,
            )
            return session
        except requests.exceptions.ConnectionError:
            if attempt == attempts:
                raise
            print(f"Connection failed (attempt {attempt}), retrying...")
            time.sleep(5)


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
    config = json.loads(Path("courses.json").read_text())
    session = make_session(config["term"])

    for course in config["courses"]:
        sections = fetch_sections(
            session, config["term"], course["subject"], course["number"]
        )

        if not sections:
            print(f"{course['subject']} {course['number']}: no sections found")

        for section in sections:
            print(
                f"{section['subjectCourse']} "
                f"CRN {section['courseReferenceNumber']}: "
                f"{open_seats(section)} open"
            )

        time.sleep(2)