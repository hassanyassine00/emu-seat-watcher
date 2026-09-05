"""EMU seat watcher — print seat counts for the courses in courses.json."""

import json
import time
from pathlib import Path
import os
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

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")


def notify(message):
    """Send a message. Falls back to printing if not configured."""
    if not WEBHOOK_URL:
        print(f"[would notify] {message}")
        return
    requests.post(WEBHOOK_URL, json={"content": message}, timeout=10)

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
DAY_KEYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]


def meeting_info(section):
    """Return (days, begin, end) for a section, or None if unscheduled."""
    meetings = section.get("meetingsFaculty") or []
    if not meetings:
        return None
    mt = meetings[0].get("meetingTime") or {}
    if not mt.get("beginTime"):
        return None
    days = [d[:3].upper() for d in DAY_KEYS if mt.get(d)]
    return days, int(mt["beginTime"]), int(mt["endTime"])

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

def credit_hours(section):
    """Credit hours, handling fixed and variable-credit courses."""
    fixed = section.get("creditHours")
    if fixed is not None:
        return str(fixed)
    low = section.get("creditHourLow")
    high = section.get("creditHourHigh")
    if low is not None and high is not None and high != low:
        return f"{low}–{high}"
    return str(low) if low is not None else "—"


def instructor(section):
    for person in section.get("faculty") or []:
        if person.get("primaryIndicator"):
            return person.get("displayName", "—")
    faculty = section.get("faculty") or []
    return faculty[0].get("displayName", "—") if faculty else "Staff"


def delivery(section):
    info = meeting_info(section)
    if info is None:
        return "Online"
    meetings = section.get("meetingsFaculty") or []
    building = (meetings[0].get("meetingTime") or {}).get("building")
    return "In person" if building else "Online"



def location(section):
    """Building and room, or a note when there's no physical space."""
    meetings = section.get("meetingsFaculty") or []
    if not meetings:
        return "—"
    mt = meetings[0].get("meetingTime") or {}
    building = mt.get("buildingDescription") or mt.get("building")
    room = mt.get("room")
    if not building:
        return "—"
    return f"{building} {room}" if room else building


def open_seats(section):
    """Seats you could actually register into, respecting cross-lists."""
    seats = section["seatsAvailable"]
    if section.get("crossList") is not None:
        seats = min(seats, section["crossListAvailable"])
    return seats


def matches_days(section, wanted):
    info = meeting_info(section)
    if info is None:
        return False
    return any(day in wanted for day in info[0])


def matches_time(section, earliest, latest):
    info = meeting_info(section)
    if info is None:
        return False
    return info[1] >= earliest and info[2] <= latest



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
        notify("Seats opened:\n" + "\n".join(opened))
    else:
        print("No change.")

    save_state(state)