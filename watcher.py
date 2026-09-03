"""EMU seat watcher — print seat counts for the courses in courses.json."""

import json
import time
from pathlib import Path

import requests

BASE = "https://bannerweb.oci.emich.edu/StudentRegistrationSsb/ssb"


STATE_FILE = Path("state.json")


def load_state():
    """Read the last known seat counts. Returns an empty record on first run."""
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except json.JSONDecodeError:
        # A half-written file should not crash the run.
        return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

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
    state = load_state()
    session = make_session(config["term"])
    opened = []

    for course in config["courses"]:
        try:
            sections = fetch_sections(
                session, config["term"], course["subject"], course["number"]
            )
        except Exception as error:
            print(f"Failed on {course['subject']} {course['number']}: {error}")
            continue

        if not sections:
            print(f"{course['subject']} {course['number']}: no sections found")

        for section in sections:
            crn = section["courseReferenceNumber"]
            seats = open_seats(section)

            if state.get(crn, 0) == 0 and seats > 0:
                opened.append(f"{section['subjectCourse']} CRN {crn}: {seats} seats")

            state[crn] = seats

        time.sleep(2)

    if opened:
        print("OPENED:")
        for line in opened:
            print(f"  {line}")
    else:
        print("No change.")

    save_state(state)