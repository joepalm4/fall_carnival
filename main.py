"""
Event Signup Roster Generator

This script reads event signup data from one or more CSV files, processes it to
create a roster of volunteers with their assigned shifts, and optionally logs
warnings/errors to a file.

Features:
- Supports multiple CSV files as input.
- Tracks volunteers by email (unique).
- Merges shifts for volunteers appearing in multiple files.
- Validates emails and known shift names.
- Optional phone number.
- Temporary diagnostics: prints final roster to console.

There are five shifts:
- setup (4-5pm)
- shift1 (5-6pm)
- shift2 (6-7pm)
- shift3 (7-8pm)
- cleanup (8-9pm)

When a volunteer signs up for a shift, they may be assigned to one booth. If
possible, volunteers should be assigned to the same booth for all their shifts.

There are 26 booths, and each booth needs 2 volunteers per shift.

If a volunteer works for four or five shifts, their last shift should be
unassigned so they can have a break.
"""
import csv
import logging
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more verbose output
    format='%(levelname)s: %(message)s',
    filename='volunteer_roster.log',
    filemode='w'  # Overwrite the log file each run. Use 'a' to append
)
logger = logging.getLogger(__name__)

# Shift mapping (all lowercase to match CSV after .lower())
SHIFT_MAP = {
    "set up": 4,
    "shift #1": 5,
    "shift #2": 6,
    "shift #3": 7,
    "clean up": 8
}
EMAIL_REGEX = r"[^@]+@[^@]+\.[^@]+"
ASSIGNED_SHIFTS = [5, 6, 7]  # Only assign these shifts


@dataclass
class Volunteer:
    """
    Represents a volunteer for the event.

    Attributes:
        first_name (str): Volunteer first name.
        last_name (str): Volunteer last name.
        email (str): Volunteer email (used as unique identifier).
        phone (str): Volunteer phone number (optional).
        shifts (set[int]): Set of integer shifts assigned to this volunteer.
    """
    first_name: str
    last_name: str
    email: str
    phone: str = ""
    shifts: set[int] = field(default_factory=set)

    def add_shift(self, shift: int):
        self.shifts.add(shift)

    def remove_shift(self, shift: int):
        self.shifts.discard(shift)


def parse_signup_data(file_path):
    """
    Parse a CSV file of volunteer signups into a dictionary of Volunteer
    objects.

    Args:
        file_path (str): Path to the CSV file.

    Returns:
        dict[str, Volunteer]: Dictionary mapping email to Volunteer object.
    """
    volunteers: dict[str, Volunteer] = {}
    with open(file_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                first_name = row['Volunteer First Name']
                last_name = row['Volunteer Last Name']
                email = row['Email']
                phone = row.get('Phone', '')

                # Skip row if email is missing
                if not re.match(EMAIL_REGEX, email):
                    logger.warning(f"Skipping row: invalid email '{email}'")
                    continue

                # Map 'What' column to shift number
                shift_name = row['What'].strip().lower()
                shift = SHIFT_MAP.get(shift_name)
                if shift is None:
                    logger.warning(f"Skipping row: unknown shift "
                                   f"'{row['What']}'")
                    continue

                # Lookup or create volunteer
                if email not in volunteers:
                    volunteers[email] = Volunteer(
                        first_name, last_name, email, phone
                    )
                    logger.info(f"Added new volunteer: {first_name} "
                                f"{last_name} ({email})")
                volunteers[email].add_shift(shift)
            except KeyError as e:
                logger.warning(f"Skipping row: missing column {e}")
                continue  # Skip rows with missing fields

    logger.info(f"Total volunteers parsed: {len(volunteers)}")
    return volunteers


def load_booths(file_path):
    booths = []
    with open(file_path, mode='r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if row:  # Skip empty rows
                booths.append(row[0].strip())
    return booths


def assign_booths(volunteers, booths):
    assignments = defaultdict(lambda: defaultdict(list))
    # Track assigned booth per volunteer
    for vol in volunteers.values():
        vol.assigned_booth = None

    for shift in ASSIGNED_SHIFTS:
        available = [v for v in volunteers.values() if shift in v.shifts]
        available.sort(key=lambda v: v.assigned_booth or "")
        booth_idx = 0
        for vol in available:
            while True:
                booth = booths[booth_idx % len(booths)]
                if len(assignments[booth][shift]) < 2:
                    assignments[booth][shift].append(vol.email)
                    if vol.assigned_booth is None:
                        vol.assigned_booth = booth
                    break
                booth_idx += 1
    return assignments


def main():
    """
    Main entry point for the script.

    - Accepts one or more CSV files as command line arguments.
    - Merges volunteers from multiple files.
    - Prints the final roster sorted by last name, then first name.
    """
    if len(sys.argv) < 3:
        logger.error("Usage: python main.py <booths_csv> <volunteer_csv1> "
                     "[<volunteer_csv2> ...]")
        sys.exit(1)

    booths_file = sys.argv[1]
    volunteer_files = sys.argv[2:]

    booths = load_booths(booths_file)
    logger.info(f"Loaded booths ({len(booths)}): {booths}")

    volunteers: dict[str, Volunteer] = {}
    for file_path in volunteer_files:
        file_vols = parse_signup_data(file_path)
        for email, vol in file_vols.items():
            if email in volunteers:
                volunteers[email].shifts.update(vol.shifts)
            else:
                volunteers[email] = vol

    assignments = assign_booths(volunteers, booths)

    print("\n--- Booth Assignments ---")
    for booth in booths:
        print(f"\n{booth}:")
        for shift in ASSIGNED_SHIFTS:
            vols = assignments[booth][shift]
            print(f"  Shift {shift}: "
                  f"{', '.join(vols) if vols else 'No volunteers'}")


if __name__ == "__main__":
    main()
