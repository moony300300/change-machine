# Change Machine (Raspberry Pi)

A GPIO-driven coin machine application for a Raspberry Pi Zero 2 W.

This project combines:
- **Kivy touchscreen UI** for in-person use.
- **Flask web admin** panel for user/card/machine management.
- **SQLite database** for users, RFID cards, transactions, and machine balances.
- **GPIO hardware interfaces** for RFID scanning, coin insertion, hopper control, and status LEDs.

---

## Features

- User login via **PIN keypad** or **RFID card**.
- User balance management with transaction logging.
- Coin deposit via coin inserter pulse input.
- Coin payout and coin munching via two hopper controllers.
- Admin override RFID behavior.
- Live machine cash tracking (`Hoppers` and `Coin_Inserter`).
- Browser-based admin pages:
  - `/users`
  - `/transactions`
  - `/rfid_cards`
  - `/machine`

---

## Hardware / GPIO Mapping

Defined in `config/gpio_pins.py`:

| Logical Name | BCM Pin | Direction |
|---|---:|---|
| `DISPENSER_MOTOR` | 14 | Output |
| `DISPENSER_SENSOR` | 12 | Input |
| `DISPENSER_LOW` | 4 | Input |
| `MUNCHER_MOTOR` | 15 | Output |
| `MUNCHER_SENSOR` | 27 | Input |
| `MUNCHER_LOW` | 22 | Input |
| `INSERTER_SENSOR` | 6 | Input |
| `MUNCH_LED` | 5 | Output |
| `DISPENSER_LED` | 24 | Output |
| `CHANGE_LED` | 23 | Output |

Some sensor inputs are inverted in software (`GPIO_INVERTED`).

---

## Software Architecture

- `main.py` initializes GPIO, starts Flask in a background thread, and launches the Kivy app.
- `ui/` contains screen logic:
  - waiting screen
  - user screen
  - PIN entry screen
  - admin screen
- `interfaces/` contains hardware integration classes:
  - `rfid.py` (`pirc522`)
  - `coin_inserter.py`
  - `hopper.py`
  - `led_light.py`
  - `gpio_manager.py`
- `databases/bank.py` is the data layer over SQLite (`databases/bank.db`).
- `web_admin.py` is the Flask admin interface.

---

## Setup

> The project is intended for Raspberry Pi OS with GPIO/SPI access.

### 1) Clone and enter repo

```bash
git clone <your-repo-url>
cd change-machine
```

### 2) Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3) Enable Pi interfaces (if not already)

Use `raspi-config` to enable:
- **SPI** (required for RC522 RFID module)
- Any additional interfaces your specific hardware wiring requires.

### 4) Run the app

```bash
python3 main.py
```

- Kivy UI runs fullscreen on the Pi display.
- Flask admin server listens on `0.0.0.0:5000`.

Open from another device on the same network:

```text
http://<raspberry-pi-ip>:5000/users
```

---

## Database

SQLite database path:

```text
databases/bank.db
```

Tables are auto-created on startup by `BankDB.create_tables()`:
- `users`
- `transactions`
- `rfid_cards`
- `machine_balance`

### Reset helpers

- Full DB reset script: `databases/reset_db.sh`
- RFID table reset script: `reset_rfid_db.py`

> Note: `databases/reset_db.sh` currently contains a hardcoded DB path. Update it for your deployment path if needed.

---

## Operational Notes

- New, unknown RFID cards are auto-registered with zero value.
- Admin RFID cards can:
  - open the admin screen
  - apply a +£1.00 adjustment to a logged-in user on the user screen
- Change LED indicates whether hopper balance and low-level status allow change payout.

---

## Useful Commands

Run hardware test script:

```bash
python3 test_hardware.py
```

Run the web admin app alone (for debug/testing):

```bash
python3 -c "from web_admin import create_app; create_app().run(host='0.0.0.0', port=5000, debug=True)"
```

---

## Deployment Tips (Pi Zero 2 W)

- Prefer running with a service manager (`systemd`) for auto-restart on boot.
- Ensure the runtime user has access to GPIO/SPI peripherals.
- Consider isolating UI and admin logs for easier diagnostics.

---

## License

No license file is currently included. Add one if you plan to distribute this project.
