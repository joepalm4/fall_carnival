import csv
import sys


def count_unique_volunteers(*input_files):
    unique_emails = set()

    for file in input_files:
        with open(file, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                email = row['Email'].strip().lower()
                if email:
                    unique_emails.add(email)

    print(f"✅ Unique volunteers: {len(unique_emails)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python count_volunteers.py input1.csv input2.csv "
              "[input3.csv ...]")
    else:
        count_unique_volunteers(*sys.argv[1:])
