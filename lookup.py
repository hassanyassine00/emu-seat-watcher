"""lookup.py — one-off interactive class search."""

import webbrowser

from watcher import (
    make_session,
    fetch_sections,
    open_seats,
    meeting_info,
    matches_days,
    matches_time,
)

TERM = "202710"      # Fall 2026
REGISTER_URL = "https://bannerweb.oci.emich.edu/StudentRegistrationSsb/ssb/registration"

# Standard scheduling shorthand: R is Thursday, since T is taken by Tuesday.
DAY_LETTERS = {
    "M": "MON",
    "T": "TUE",
    "W": "WED",
    "R": "THU",
    "F": "FRI",
}


def parse_days(text):
    """Turn 'MW' or 'TR' into ['MON', 'WED']. Blank means no preference."""
    text = text.strip().upper()
    if not text:
        return None
    days = [DAY_LETTERS[c] for c in text if c in DAY_LETTERS]
    return days or None


def parse_time(text, default):
    """Turn '9', '900', or '9:00' into 900. Blank returns the default."""
    text = text.strip().replace(":", "")
    if not text:
        return default
    value = int(text)
    return value * 100 if value < 24 else value


if __name__ == "__main__":
    subject = input("Subject (e.g. COSC): ").strip().upper()
    number = input("Course number (e.g. 411): ").strip().upper()
    wanted_days = parse_days(
        input("Preferred days (M T W R F, blank for any): ")
    )
    earliest = parse_time(input("Earliest start (e.g. 900, blank for any): "), 0)
    latest = parse_time(input("Latest end (e.g. 1700, blank for any): "), 2359)

    session = make_session(TERM)
    sections = fetch_sections(session, TERM, subject, number)

    if not sections:
        print("No sections found.")

    shown = 0
    for section in sections:
        if wanted_days and not matches_days(section, wanted_days):
            continue
        if not matches_time(section, earliest, latest):
            continue

        shown += 1
        info = meeting_info(section)
        when = "no scheduled meeting" if info is None else (
            f"{'/'.join(info[0])} {info[1]:04d}-{info[2]:04d}"
        )
        print(
            f"{section['subjectCourse']} "
            f"CRN {section['courseReferenceNumber']}: "
            f"{open_seats(section)} open — {when}"
        )

    if sections and shown == 0:
        print("No sections match those filters.")

    if shown and input("\nOpen registration? (y/n): ").strip().lower() == "y":
        webbrowser.open(REGISTER_URL)