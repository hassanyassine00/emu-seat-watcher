"""lookup.py — one-off interactive class search."""

from watcher import make_session, fetch_sections, open_seats

TERM = "202710"      # Fall 2026

if __name__ == "__main__":
    subject = input("Subject (e.g. COSC): ").strip().upper()
    number = input("Course number (e.g. 411): ").strip().upper()

    session = make_session(TERM)
    sections = fetch_sections(session, TERM, subject, number)

    if not sections:
        print("No sections found.")

    for section in sections:
        print(
            f"{section['subjectCourse']} "
            f"CRN {section['courseReferenceNumber']}: "
            f"{open_seats(section)} open"
        )