"""Event Signup Roster Generator
This script reads the event signup data, processes it to create a roster of
volunteers for each booth, and saves the rosters to a CSV file.

The event signup data is a CSV file that includes the shifts, with shift time
and volunteer information (first name, last name, email, and phone number).

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
import sys
import pandas as pd


class Volunteer:
    def __init__(self, first_name, last_name, email, phone):
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.phone = phone
        self.assigned_shifts = []

    def add_shift(self, shift):
        self.assigned_shifts.append(shift)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"Volunteer({self.full_name}, {self.email}, {self.phone})"

    def __del__(self):
        pass


class Booth:
    def __init__(self, name):
        self.name = name


class BoothShift:
    def __init__(self, booth, start_time, end_time):
        self.booth = booth
        self.start_time = start_time
        self.end_time = end_time
        self.volunteers = []


def parse_signup_data(file_path):
    # Build set of volunteers from CSV file
    volunteers = {}
    with open(file_path, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            first_name = row['Volunteer First Name']
            last_name = row['Volunteer Last Name']
            email = row['Email']
            phone = row['Phone']
            shift = row['What']
            if email not in volunteers:
                volunteers[email] = Volunteer(
                    first_name, last_name, email, phone
                )
            volunteers[(first_name, last_name)].add_shift(shift)
    return volunteers


def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <input_csv_file>")
        sys.exit(1)
    input_csv_file = sys.argv[1]



if __name__ == "__main__":
    main()
