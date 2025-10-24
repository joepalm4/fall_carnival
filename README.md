# Event Signup Roster Generator

A Python tool to generate volunteer and booth schedules for a fall carnival. 
It reads volunteer signup data from CSV files, assigns volunteers to booths
based on availability, and ensures fair shift distribution.

---

## Features

- Supports multiple CSV files as input.
- Tracks volunteers by email (unique identifier).
- Merges shifts for volunteers appearing in multiple files.
- Validates emails and known shift names.
- Optional phone number support.
- Prints final roster to console for diagnostics.
- Assigns volunteers to booths with 2 volunteers per shift.
- Volunteers working 4+ shifts get a break on their last shift.
- Detects unfilled booths per shift.

---

## Installation

1. Clone this repository:

```bash
git clone https://github.com/yourusername/event-roster-generator.git
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

---

## Usage

```bash
python main.py <booths_csv> <volunteer_csv1> [<volunteer_csv2> ...]
```

Example:
```bash
python main.py booths.csv volunteers1.csv volunteers2.csv
```

This will generate:

- `roster.csv` — Booth-focused roster
- `volunteer_roster.csv` — Volunteer-focused roster
- `volunteer_roster_2x2_landscape_fixed.pdf` — PDF of volunteer schedules
- `booth_roster_2x2_landscape.pdf` — PDF of booth schedules

---

## Assignment Rules

- Each booth needs **2 volunteers per shift**.
- Only **shift1, shift2, and shift3** are assigned to booths.
- Volunteers working **4 or 5 shifts** are given a break on their last shift.
- Volunteers are **assigned to the same booth across shifts** if possible.
- Unassigned shifts are labeled `"Unassigned"` in volunteer PDFs/CSVs.
- **Setup and cleanup** shifts are always listed but not assigned to booths.

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

## Contributing
Contributions are welcome! Please fork the repository and submit a pull request.

## License
MIT License
