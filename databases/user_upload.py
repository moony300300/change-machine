import csv

def import_users_from_csv(self, file_path, default_balance=2.00):
    """
    CSV format:
    name,pin
    Alice,1234
    Bob,5678
    """

    conn = self.connect()
    cursor = conn.cursor()

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

            try:
                cursor.execute("""
                    INSERT INTO users (name, pin, balance, float, newUser)
                    VALUES (?, ?, ?, ?, 1)
                """, (name, pin, default_balance, default_balance))

                inserted += 1

            except sqlite3.IntegrityError:
                print(f"[CSV IMPORT] Duplicate PIN skipped: {pin}")
                skipped += 1

    conn.commit()
    conn.close()

    print(f"[CSV IMPORT] Done → Inserted: {inserted}, Skipped: {skipped}")

    return {
        "inserted": inserted,
        "skipped": skipped
    }

if __name__ == "__main__":
    filepath = "./users.csv"  # Update this path to your CSV file

    import_users_from_csv(filepath)
