#!/bin/bash

echo "Resetting Arcade Bank Database..."

DB_PATH="/home/admin/Documents/project/databases/bank.db"

if [ -f "$DB_PATH" ]; then
  rm "$DB_PATH"
  echo "Database deleted."
else
  echo "No database found to delete."
fi

# Re-create the database tables by running a short Python script
python3 - <<EOF
from databases.bank import BankDB
BankDB()
print("Fresh database created.")
EOF
