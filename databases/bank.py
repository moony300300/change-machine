import sqlite3
from datetime import datetime
import random

DB_PATH = "databases/bank.db"

class BankDB:
    def __init__(self):
        self.create_tables()

    def connect(self):
        """Establish a database connection."""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # To access columns by name
        return conn

    def create_tables(self):
        conn = self.connect()
        cursor = conn.cursor()
    
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                pin TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0.00,
                float REAL DEFAULT 0.00,
                newUser BOOL DEFAULT 1
            )
        """)
    
        # type: deposit | withdrawal | redemption | admin
        # source: coin_inserter | hopper | rfid | web
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL NOT NULL,
                type TEXT NOT NULL,
                source TEXT NOT NULL,
                reference TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rfid_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rfid TEXT UNIQUE NOT NULL,
                value REAL NOT NULL,
                active INTEGER DEFAULT 0,
                isAdminKey BOOL DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS machine_balance (
                name TEXT UNIQUE NOT NULL,
                balance REAL DEFAULT 0
            )
        """)
        cursor.execute("""
            INSERT OR IGNORE INTO machine_balance (name, balance)
            VALUES
                ('Hoppers', 0),
                ('Coin_Inserter', 0)
        """)
    
        conn.commit()
        conn.close()
    
    def log_transaction(self, user, amount, type, source, reference=''):
        """Log a transaction for a user."""
        conn = self.connect()
        cursor = conn.cursor()

        if not user:
            conn.close()
            raise ValueError("User with not found")

        user_id = user['id']

        cursor.execute(
            "INSERT INTO transactions (user_id, amount, type, source, reference) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, type, source, reference)
        )
        conn.commit()
        conn.close()

    def add_user(self, name, pin, balance=0.00, newUser=True):
        """Add a new user to the database."""
        conn = self.connect()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (name, pin, balance, float, newUser) VALUES (?, ?, ?, ?, ?)", 
                           (name, pin, balance, balance, newUser))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            print("Error: PIN already assigned to another user.")
            return False
        finally:
            conn.close()

    def get_user_by_pin(self, pin):
        """Retrieve user details by PIN."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, pin, balance, float, newUser FROM users WHERE pin = ?", (pin,))
        user = cursor.fetchone()
        conn.close()
        if user:
            return dict(user)
        return None
    
    def get_user_by_id(self, user_id):
        """Retrieve user details by ID."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, pin, balance, float, newUser FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        if user:
            return dict(user)
        return None

    def update_balance(self, user, amount, type, source, reference=''):
        """Update a user's balance (add or subtract)."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, user['id']))
        if source == 'Coin Inserter' or type == 'Admin':
            cursor.execute("UPDATE users SET float = float + ? WHERE id = ?", (amount, user['id']))
        conn.commit()
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user['id'],))
        new_balance = cursor.fetchone()[0]
        conn.close()

        self.log_transaction(user, amount, type, source, reference)

        return new_balance

    def get_user_balance(self, user):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT balance FROM users WHERE id = ?", (user['id'],))
        result = cursor.fetchone()
        conn.close()
        if result:
            return result[0]
        else:
            return None  # or raise an error if user not found

    def delete_user(self, user):
        """Delete a user from the database."""
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user['id'],))
        conn.commit()
        conn.close()
    
    def get_all_users(self):
        conn = self.connect()

        c = conn.cursor()
        c.execute("SELECT id, name, balance, float, pin FROM users ORDER BY name")
        res = c.fetchall()

        conn.close()
        return res

    def update_user(self, user, name, balance, pin):
        conn = self.connect()

        c = conn.cursor()
        c.execute("UPDATE users SET name=?, balance=?, pin=? WHERE id=?", (name, balance, pin, user['id']))
        conn.commit()
        conn.close()

    def get_transactions(self, user_id=None, start=None, end=None):
        conn = self.connect()
        cur = conn.cursor()

        query = """
            SELECT
                t.timestamp,
                u.name,
                t.amount,
                t.type,
                t.source,
                t.reference
            FROM transactions t
            JOIN users u ON t.user_id = u.id
            WHERE 1=1
        """
        params = []

        if user_id:
            query += " AND t.user_id = ?"
            params.append(user_id)
        if start:
            query += " AND date(t.timestamp) >= date(?)"
            params.append(start)
        if end:
            query += " AND date(t.timestamp) <= date(?)"
            params.append(end)

        query += " ORDER BY t.timestamp ASC"

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        return self._aggregate_transactions(rows)

    def _aggregate_transactions(self, rows, window_seconds=60):
        aggregated = []
        current = None
    
        for row in rows:
            ts = datetime.fromisoformat(row["timestamp"])
            amount = row["amount"]
    
            if current is None:
                current = {
                    "timestamp": ts,
                    "name": row["name"],
                    "amount": amount,
                    "type": row["type"],
                    "source": row["source"],
                    "reference": row["reference"],
                }
                continue
    
            same_user = row["name"] == current["name"]
            same_type = row["type"] == current["type"]
            same_source = row["source"] == current["source"]
            same_ref = row["reference"] == current["reference"]
            close_in_time = (ts - current["timestamp"]).total_seconds() <= window_seconds
    
            if all([same_user, same_type, same_source, same_ref, close_in_time]):
                current["amount"] += amount
            else:
                aggregated.append(current)
                current = {
                    "timestamp": ts,
                    "name": row["name"],
                    "amount": amount,
                    "type": row["type"],
                    "source": row["source"],
                    "reference": row["reference"],
                }
    
        if current:
            aggregated.append(current)
    
        # Return newest first (matches your original UI expectation)
        aggregated.reverse()
        return aggregated

    def get_leaderboard(self):
        conn = self.connect()
        cur = conn.cursor()
        cur.execute("""
            SELECT u.name, ROUND(SUM(t.amount), 2) as net
            FROM transactions t
            JOIN users u ON t.user_id = u.id
            GROUP BY u.id
            ORDER BY net DESC
        """)
        res = cur.fetchall()

        conn.close()
        return res


    def get_trend_data(self):
        conn = self.connect()

        c = conn.cursor()
        c.execute("SELECT timestamp, CASE WHEN amount > 0 THEN 'deposit' ELSE 'withdrawal' END AS type, SUM(amount) FROM transactions GROUP BY timestamp, type")
        res = c.fetchall()

        conn.close()
        return res
    
    def get_rfid_card_by_id(self, card_id):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT * FROM rfid_cards WHERE id=?", (card_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return {
                'id': row[0],
                'rfid': row[1],
                'value': row[2],
                'active': row[3],
                'isAdminKey': bool(row[4])
            }
        return None


    def add_rfid_card(self, rfid, value):
        conn = self.connect()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO rfid_cards (rfid, value) VALUES (?, ?)",
                (rfid, value)
            )
            conn.commit()

            card_id = cursor.lastrowid
            return {
                "id": card_id,
                "rfid": rfid,
                "value": value,
                "active": True,
                "is_admin": False
            }
        except sqlite3.IntegrityError:
            print("Error: RFID tag already registered.")
            return False
        finally:
            conn.close()

    def redeem_rfid_card(self, rfid, user=None):
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, value, active
            FROM rfid_cards WHERE rfid=?
        """, (rfid,))
        card = cursor.fetchone()

        if not card:
            conn.close()
            return False, "Card not Registered"
        elif not card["active"]:
            conn.close()
            return False, "Prize already Redeemed!"

        if user == None:
            return False, "Login to redeem"
        
        self.update_balance(user, card["value"], 'Redemption', 'RFID', f'Redeemed £{card["value"]:.2f}')

        cursor.execute("""
            UPDATE rfid_cards
            SET active = 0
            WHERE id=?
        """, (card["id"],))

        conn.commit()
        conn.close()
        return True, f"Redeemed £{card['value']:.2f}"
    
    def get_rfid_card_by_rfid(self, rfid):
        conn = self.connect()
        c = conn.cursor()
        c.execute("""
            SELECT id, rfid, value, active, isAdminKey
            FROM rfid_cards
            WHERE rfid = ?
        """, (rfid,))
        row = c.fetchone()
        conn.close()

        if not row:
            return None

        return {
            'id': row['id'],
            'rfid': row['rfid'],
            'value': row['value'],
            'active': bool(row['active']),
            'is_admin': bool(row['isAdminKey']),
        }

    def get_all_rfid_cards(self):
        conn = self.connect()
        c = conn.cursor()
        c.execute("""
            SELECT id, rfid, value, active, isAdminKey
            FROM rfid_cards
            ORDER BY id ASC
        """)
        rows = c.fetchall()
        conn.close()
        return rows


    def update_rfid_card(self, card_id, value, active):
        conn = self.connect()
        c = conn.cursor()
        c.execute("""
            UPDATE rfid_cards
            SET value = ?, active = ?
            WHERE id = ?
        """, (value, active, card_id))
        conn.commit()
        conn.close()

    def modify_admin_key(self, rfid, is_admin):
        conn = self.connect()
        c = conn.cursor()
        c.execute("UPDATE rfid_cards SET value = 0, active = 0, isAdminKey = ? WHERE rfid = ?", (1 if is_admin else 0, rfid))
        conn.commit()
        conn.close()

    def is_admin_rfid(self, rfid):
        conn = self.connect()
        c = conn.cursor()
        c.execute(
            "SELECT isAdminKey FROM rfid_cards WHERE rfid = ?",
            (rfid,)
        )
        row = c.fetchone()
        conn.close()

        if row is None:
            return False

        return bool(row["isAdminKey"])
    
    def get_top_users(self, limit=5):
        conn = self.connect()
        c = conn.cursor()
        c.execute("""
            SELECT name, (balance - float) AS score
            FROM users
            ORDER BY score DESC
            LIMIT ?
        """, (limit,))
        rows = c.fetchall()
        conn.close()
        return rows
    
    def get_machine_cash(self, machine):
        conn = self.connect()
        c = conn.cursor()
        c.execute("SELECT balance FROM machine_balance WHERE name = ?", (machine,))
        amount = c.fetchone()[0]
        conn.close()
        return amount
    
    def adjust_machine_cash(self, machine, amount):
        conn = self.connect()
        c = conn.cursor()
        c.execute(
            "UPDATE machine_balance SET balance = balance + ? WHERE name = ?",
            (amount, machine,)
        )
        conn.commit()
        conn.close()

    def generate_unique_pin(self, length=4):
        conn = self.connect()
        c = conn.cursor()

        while True:
            pin = "".join(str(random.randint(0, 9)) for _ in range(length))
            c.execute("SELECT 1 FROM users WHERE pin = ?", (pin,))
            if not c.fetchone():
                conn.close()
                return pin
            
    def delete_user(self, user_id):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
        conn.close()

    def delete_rfid_card(self, card_id):
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rfid_cards WHERE id=?", (card_id,))
        conn.commit()
        conn.close()

    def update_user_pin(self, user, new_pin):
        conn = self.connect()
        c = conn.cursor()
        c.execute("UPDATE users SET pin = ? WHERE id = ?", (new_pin, user['id']))
        conn.commit()
        conn.close()

    def set_user_not_new(self, user):
        conn = self.connect()
        c = conn.cursor()
        c.execute("UPDATE users SET newUser = 0 WHERE id = ?", (user['id'],))
        conn.commit()
        conn.close()
