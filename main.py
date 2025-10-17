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
SHIFT_NAMES = {
    4: "setup",
    5: "shift1",
    6: "shift2",
    7: "shift3",
    8: "cleanup"
}


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
    assigned_booth: str = ""

    def add_shift(self, shift: int):
        self.shifts.add(shift)

    def remove_shift(self, shift: int):
        self.shifts.discard(shift)

    def __repr__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


@dataclass
class Booth:
    name: str
    capacity_per_shift: int = 2
    assignments: dict[int, list[str]] = field(
        default_factory=lambda: defaultdict(list)
    )  # shift -> list of volunteer emails

    def assign_volunteer(self, shift: int, volunteer_email: str) -> bool:
        if len(self.assignments[shift]) < self.capacity_per_shift:
            self.assignments[shift].append(volunteer_email)
            return True
        return False

    def has_space(self, shift: int) -> bool:
        return len(self.assignments[shift]) < self.capacity_per_shift

    def formatted(self, volunteers: dict[str, "Volunteer"]) -> str:
        """
        Return a human-readable string showing volunteer *names* instead of
        emails.
        """
        output = [f"{self.name}:"]
        for shift in sorted(self.assignments.keys()):
            vols = ", ".join(
                f"{volunteers[email].first_name} {volunteers[email].last_name}"
                for email in self.assignments[shift]
                if email in volunteers
            ) or "No volunteers"
            shift_name = SHIFT_NAMES.get(shift, f"Shift {shift}")
            output.append(f"  {shift_name}: {vols}")
        return "\n".join(output)

    def __str__(self):
        output = [f"{self.name}:"]
        for shift in sorted(self.assignments.keys()):
            vols = ", ".join(self.assignments[shift]) or "No volunteers"
            shift_name = SHIFT_NAMES.get(shift, f"Shift {shift}")
            output.append(f"  {shift_name}: {vols}")
        return "\n".join(output)


def load_booths(file_path: str) -> list[Booth]:
    booths = []
    with open(file_path, mode='r', newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            booth_name = row.get('BoothName', '').strip()
            if booth_name:
                booths.append(Booth(name=booth_name))
    logger.info(f"Loaded {len(booths)} booths from {file_path}")
    return booths


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
    with open(file_path, mode='r', newline='', encoding='utf-8-sig') as file:
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


def apply_break_rule(volunteers: dict[str, Volunteer]):
    """
    Volunteers working 4 or more shifts get their last shift removed.
    """
    for vol in volunteers.values():
        if len(vol.shifts) >= 4:
            last_shift = max(vol.shifts)
            vol.remove_shift(last_shift)
            logger.info(f"{vol} assigned break — removed "
                        f"{SHIFT_NAMES.get(last_shift, last_shift)}")


def assign_booths(volunteers: dict[str, Volunteer], booths: list[Booth]):
    booth_index = 0
    booth_count = len(booths)

    # Sort volunteers for deterministic assignment
    sorted_volunteers = sorted(
        volunteers.values(),
        key=lambda v: (v.last_name.lower(), v.first_name.lower())
    )

    for shift in ASSIGNED_SHIFTS:
        for vol in sorted_volunteers:
            if shift not in vol.shifts:
                continue  # Volunteer not signed up for this shift

            # Try to assign to the same booth as before
            if vol.assigned_booth:
                booth = next((
                    b
                    for b in booths
                    if b.name == vol.assigned_booth
                ), None)
                if booth and booth.assign_volunteer(shift, vol.email):
                    continue

            # Otherwise, find the next available booth
            attempts = 0
            while attempts < booth_count:
                booth = booths[booth_index % booth_count]
                booth_index += 1
                attempts += 1
                if booth.assign_volunteer(shift, vol.email):
                    vol.assigned_booth = booth.name
                    break


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
    logger.info(f"Loaded booths ({len(booths)}): {[b.name for b in booths]}")

    volunteers: dict[str, Volunteer] = {}
    for vf in volunteer_files:
        file_vols = parse_signup_data(vf)
        for email, vol in file_vols.items():
            if email in volunteers:
                volunteers[email].shifts.update(vol.shifts)
            else:
                volunteers[email] = vol

    # Apply break rule before assignment
    apply_break_rule(volunteers)

    assign_booths(volunteers, booths)

    print("\n=== FINAL BOOTH ROSTER ===")
    for booth in sorted(booths, key=lambda b: b.name):
        print(booth.formatted(volunteers))
        print()

    print(f"Total volunteers: {len(volunteers)}")

    print("=== UNFILLED BOOTHS ===")
    for shift in ASSIGNED_SHIFTS:
        unfilled = [b.name for b in booths if b.has_space(shift)]
        if unfilled:
            print(f"{SHIFT_NAMES[shift]}: {len(unfilled)} booths need"
                  f" volunteers")


if __name__ == "__main__":
    main()
