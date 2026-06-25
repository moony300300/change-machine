import csv
from bank import BankDB

bank_db = BankDB()

def import_users_from_csv(file_path, default_balance=2.00):
    """
    CSV format:
    name,pin
    Alice,1234
    Bob,5678
    """

    inserted = 0
    skipped = 0

    with open(file_path, newline='') as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            name = row.get("name")
            pin = row.get("pin")

            if not name or not pin:
                print(f"[CSV IMPORT] Skipping invalid row: {row}")
                skipped += 1
                continue

            # use your DB method
            success = bank_db.add_user(
                name=name.strip(),
                pin=pin.strip(),
                balance=default_balance
            )

            if success:
                inserted += 1
            else:
                skipped += 1

    print(f"[CSV IMPORT] Done → Inserted: {inserted}, Skipped: {skipped}")

    return {
        "inserted": inserted,
        "skipped": skipped
    }


if __name__ == "__main__":
    filepath = "./users.csv"
    import_users_from_csv(filepath)