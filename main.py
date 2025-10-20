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

If a volunteer works for four or five shifts, the last chronological shift
they signed up for should be unassigned so they can have a break.
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


# ---------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------
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
        assigned_booth (str): Name of the booth assigned to this volunteer.
    """
    first_name: str
    last_name: str
    email: str
    phone: str = ""
    shifts: set[int] = field(default_factory=set)

    # shift -> booth name
    booths_per_shift: dict[int, str] = field(default_factory=dict)

    def add_shift(self, shift: int):
        self.shifts.add(shift)

    def remove_shift(self, shift: int):
        self.shifts.discard(shift)
        if shift in self.booths_per_shift:
            del self.booths_per_shift[shift]

    def __repr__(self):
        return f"Volunteer({self.first_name} {self.last_name}, {self.email})"


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


# ---------------------------------------------------------------------
# Parsing & Loading
# ---------------------------------------------------------------------
def load_booths(file_path: str) -> list[Booth]:
    """
    Load booth data from a CSV file.

    Args:
        file_path (str): Path to the CSV file.

    Returns:
        list[Booth]: List of Booth objects.
    """
    booths = []
    try:
        with open(file_path, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                booth_name = row.get('BoothName', '').strip()
                if booth_name:
                    booths.append(Booth(name=booth_name))
    except FileNotFoundError:
        logger.error(f"Booth file not found: {file_path}")
        sys.exit(1)

    if not booths:
        logger.error(f"No booths found in file: {file_path}")
        sys.exit(1)

    logger.info(f"Loaded {len(booths)} booths from {file_path}")
    return booths


def parse_signup_data(file_path: str) -> dict[str, Volunteer]:
    """
    Parse a CSV file of volunteer signups into a dictionary of Volunteer
    objects.

    Args:
        file_path (str): Path to the CSV file.

    Returns:
        volunteers (dict): Dictionary mapping email to Volunteer objects.
    """
    volunteers: dict[str, Volunteer] = {}
    try:
        with open(file_path, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                first_name = row.get('Volunteer First Name', '')
                last_name = row.get('Volunteer Last Name', '')
                email = row.get('Email', '').strip().lower()
                phone = row.get('Phone', '')

                # Skip row if email is missing
                if not re.match(EMAIL_REGEX, email):
                    logger.warning(f"Skipping row: invalid email '{email}'")
                    continue

                # Map 'What' column to shift number (start time)                
                shift_name = row.get('What', '').strip().lower()
                if not shift_name:
                    logger.warning(f"Skipping row: missing shift name in "
                                   f"{file_path}")
                    continue
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
                    logger.debug(f"Added new volunteer: {first_name} "
                                f"{last_name} ({email})")
                volunteers[email].add_shift(shift)
    except FileNotFoundError:
        logger.error(f"Signup file not found: {file_path}")
        sys.exit(1)

    logger.info(f"Total volunteers parsed: {len(volunteers)}")
    return volunteers


# ---------------------------------------------------------------------
# Assignment Logic
# ---------------------------------------------------------------------
def apply_break_rule(volunteers: dict[str, Volunteer]):
    """
    Volunteers working 4 or more shifts get their last shift removed.
    """
    for vol in volunteers.values():
        if len(vol.shifts) >= 4:
            last_shift = max(vol.shifts)
            vol.remove_shift(last_shift)
            logger.info(f"{vol} should take break during "
                        f"{SHIFT_NAMES.get(last_shift, last_shift)}")


def assign_booths(volunteers: dict[str, Volunteer], booths: list[Booth]):
    booth_index = 0
    booth_count = len(booths)

    # Sort volunteers for deterministic assignment (order by last name, first
    # name)
    sorted_volunteers = sorted(
        volunteers.values(),
        key=lambda v: (v.last_name.lower(), v.first_name.lower())
    )

    for shift in ASSIGNED_SHIFTS:
        for vol in sorted_volunteers:
            if shift not in vol.shifts:
                continue  # Volunteer not signed up for this shift

            # Try to assign to the same booth as previous shift if possible
            prev_booth_name = vol.booths_per_shift.get(shift - 1)
            if prev_booth_name:
                booth = next((
                    b
                    for b in booths
                    if b.name == prev_booth_name
                ), None)
                if booth and booth.assign_volunteer(shift, vol.email):
                    vol.booths_per_shift[shift] = booth.name
                    continue

            # Otherwise, find the next available booth
            attempts = 0
            while attempts < booth_count:
                booth = booths[booth_index % booth_count]
                booth_index += 1
                attempts += 1
                if booth.assign_volunteer(shift, vol.email):
                    vol.booths_per_shift[shift] = booth.name
                    break


# ---------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------
def write_roster_csv(
    booths: list[Booth],
    volunteers: dict[str, Volunteer],
    filename="roster.csv"
):
    """
    Writes the booth roster to a CSV file.
    Columns: BoothName, Shift, Volunteer1, Volunteer2
    """
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["BoothName", "Shift", "Volunteer1", "Volunteer2"])
        for booth in booths:
            for shift in sorted(booth.assignments.keys()):
                vols = booth.assignments[shift]
                names = []
                for email in vols:
                    vol_obj = volunteers.get(email)
                    if vol_obj:
                        names.append(f"{vol_obj.first_name} "
                                     f"{vol_obj.last_name}")
                    else:
                        names.append(email)
                while len(names) < 2:
                    names.append("")
                writer.writerow(
                    [booth.name, SHIFT_NAMES.get(shift, shift)] + names
                )
    logger.info(f"Roster written to {filename}")


def write_volunteer_roster_csv(
        volunteers: dict[str, Volunteer],
        filename="volunteer_roster.csv"
):
    """
    Writes a CSV where each row is a volunteer with their assigned shifts and
    booths.
    """
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Determine max number of shifts across all volunteers
        max_shifts = max((len(v.shifts) for v in volunteers.values()), default=0)

        # Write header
        header = ["FirstName", "LastName", "Email", "Phone"]
        for i in range(1, max_shifts + 1):
            header += [f"Shift{i}", f"Booth{i}"]
        writer.writerow(header)

        # Write volunteer rows
        for vol in sorted(volunteers.values(), key=lambda v: (v.last_name.lower(), v.first_name.lower())):
            row = [vol.first_name, vol.last_name, vol.email, vol.phone]

            # Sort shifts chronologically
            sorted_shifts = sorted(vol.shifts)
            for shift in sorted_shifts:
                shift_name = SHIFT_NAMES.get(shift, f"Shift {shift}")
                booth_name = vol.booths_per_shift.get(shift, "Unassigned")
                row += [shift_name, booth_name]

            # Fill remaining shift columns with blanks if fewer than max
            for _ in range(max_shifts - len(sorted_shifts)):
                row += ["", ""]

            writer.writerow(row)

    logger.info(f"Volunteer-oriented roster written to {filename}")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
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

    # Load booths
    booths = load_booths(booths_file)

    # Load and merge volunteers from all files
    volunteers: dict[str, Volunteer] = {}
    for vf in volunteer_files:
        file_vols = parse_signup_data(vf)
        for email, vol in file_vols.items():
            if email in volunteers:
                # Merge shifts for existing volunteer
                logger.info(f"Merging shifts for existing volunteer: {vol}")
                volunteers[email].shifts.update(vol.shifts)
            else:
                # New volunteer
                volunteers[email] = vol

    # Apply break rule before assignment
    apply_break_rule(volunteers)

    # Assign volunteers to booths
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

    # Summary statistics
    total_slots = sum(
        len(b.assignments[s]) for b in booths for s in ASSIGNED_SHIFTS
    )
    logger.info(f"Total filled slots: {total_slots}")

    # Write per-booth CSV
    write_roster_csv(booths, volunteers, filename="roster.csv")
    print("Roster written to roster.csv")

    # Write per-volunteer CSV
    write_volunteer_roster_csv(volunteers, filename="volunteer_roster.csv")


if __name__ == "__main__":
    main()
