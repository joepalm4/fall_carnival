# Event Signup Roster Generator

This Python project generates a volunteer roster for an event with multiple booths and shifts. It reads volunteer signup data from CSV files and assigns volunteers to booths based on their availability while ensuring fair shift distribution.

---

## Features

- Supports multiple CSV files as input.
- Tracks volunteers by email (unique identifier).
- Merges shifts for volunteers appearing in multiple files.
- Validates emails and known shift names.
- Optional phone number support.
- Prints final roster to console for diagnostics.
- Assigns volunteers to booths (26 booths total) with 2 volunteers per shift.
- Volunteers working 4+ shifts get a break on their last shift.
- Detects unfilled booths per shift.

---

## Shifts

| Shift   | Time  |
|---------|-------|
| setup   | 4-5 PM |
| shift1  | 5-6 PM |
| shift2  | 6-7 PM |
| shift3  | 7-8 PM |
| cleanup | 8-9 PM |

Only **shift1, shift2, and shift3** are assigned to booths.  

---

## CSV Input Formats

### Booths CSV

- Must include a header row with a `BoothName` column.
- Example:

```csv
BoothName
Booth1
Booth2
Bake Sale
Pumpkin Patch