from flask import Flask, render_template_string, request, redirect
from databases.bank import BankDB
import json

bank_db = BankDB()

NAV = """
<div style="margin-bottom:20px;">
    <a href="/users">Users</a> |
    <a href="/transactions">View Transactions</a> |
    <a href="/rfid_cards">RFID Cards</a> |
    <a href="/machine">Machine Stats</a>
</div>
"""

def create_app():
    app = Flask(__name__)

    @app.route("/users", methods=["GET", "POST"])
    def users():
        if request.method == "POST":
            if "add_user" in request.form:
                name = request.form["name"]
                pin = bank_db.generate_unique_pin()
                bank_db.add_user(name, pin, balance=2.00)

            elif "add_balance" in request.form:
                user_id = int(request.form["user_id"])
                user = bank_db.get_user_by_id(user_id)
                amount = float(request.form["amount"])
                bank_db.update_balance(user, amount, 'Admin', 'Web', f'Adjusted Balance by £{amount:.2f} by an Admin')

            elif "delete_user" in request.form:
                user_id = int(request.form["user_id"])
                bank_db.delete_user(user_id)

            elif "set_score" in request.form:
                user_id = int(request.form["user_id"])
                score = float(request.form["score"])

                bank_db.update_user_score(user_id, score)

            return redirect("/users")

        users = bank_db.get_all_users()
        return render_template_string("""
        {{ nav|safe }}
        <h1>Users</h1>

        <h2>Add New User</h2>
        <form method="post">
            Name: <input name="name">
            <button name="add_user">Create User</button>
        </form>

        <h2>Existing Users</h2>
        <table border=1>
        <tr><th>Name</th><th>PIN</th><th>Balance</th><th>Score</th><th>Add Balance</th><th>Delete</th></tr>
        {% for u in users %}
        <tr>
            <td>{{ u['name'] }}</td>
            <td>{{ u['pin'] }}</td>
            <td>£{{ '%.2f'|format(u['balance']) }}</td>
            <td>
                <form method="post">
                    <input type="hidden" name="user_id" value="{{ u['id'] }}">
            
                    <input
                        name="score"
                        value="{{ ((u['balance'] - u['float']) * 100)|int }}"
                        size="6">
            
                    <button name="set_score">Set</button>
                </form>
            </td>
            <td>
                <form method="post">
                    <input type="hidden" name="user_id" value="{{ u['id'] }}">
                    <input name="amount" size=6 placeholder="£">
                    <button name="add_balance">Add</button>
                </form>
            </td>
            <td>
                <form method="post">
                    <input type="hidden" name="user_id" value="{{ u['id'] }}">
                    <button name="delete_user">Delete</button>
                </form>
            </td>
        </tr>
        {% endfor %}
        </table>
        """, users=users, nav=NAV)



    @app.route("/transactions")
    def transactions():
        user_filter = request.args.get("user")
        start = request.args.get("start")
        end = request.args.get("end")
        txns = bank_db.get_transactions(user_filter, start, end)
        return render_template_string("""
            {{ nav|safe }}
            <h1>Transactions</h1>
            <form method="get">
              User ID: <input name="user" value="{{request.args.user}}">
              Start: <input type="date" name="start" value="{{request.args.start}}">
              End: <input type="date" name="end" value="{{request.args.end}}">
              <button type="submit">Filter</button>
            </form>
            <table border=1>
            <tr>
              <th>Date</th>
              <th>User</th>
              <th>Amount</th>
              <th>Type</th>
              <th>Source</th>
              <th>Reference</th>
            </tr>
            
            {% for t in txns %}
            <tr>
              <td>{{ t.timestamp }}</td>
              <td>{{ t.name }}</td>
              <td>£{{ '%.2f'|format(t.amount) }}</td>
              <td>{{ t.type }}</td>
              <td>{{ t.source }}</td>
              <td>{{ t.reference }}</td>
            </tr>
            {% endfor %}
            </table>
        """, txns=txns, nav=NAV)

    @app.route("/rfid_cards", methods=["GET", "POST"])
    def rfid_cards():
        if request.method == "POST":
            card_id = int(request.form["id"])
            card = bank_db.get_rfid_card_by_id(card_id)

            if "delete_card" in request.form:
                bank_db.delete_rfid_card(card_id)
                return redirect("/rfid_cards")

            is_admin = "is_admin" in request.form

            # Update admin flag FIRST
            if card["isAdminKey"] != is_admin:
                bank_db.modify_admin_key(card["rfid"], is_admin)

            # Only update value/active for non-admin cards
            if not is_admin:
                value = float(request.form.get("value", 0))
                active = int("active" in request.form)
                bank_db.update_rfid_card(card_id, value, active)

            return redirect("/rfid_cards")

        cards = bank_db.get_all_rfid_cards()
        return render_template_string("""
        {{ nav|safe }}
        <h1>RFID Cards</h1>

        <table border=1>
        <tr>
            <th>ID</th>
            <th>RFID</th>
            <th>Value</th>
            <th>Active</th>
            <th>Admin Key</th>
            <th>Save</th>
            <th>Delete</th>
        </tr>
        {% for c in cards %}
        <tr>
            <form method="post">
                <td>{{ c['id'] }}</td>
                <td>{{ c['rfid'] }}</td>
                <td>
                    <input name="value" value="{{ c['value'] }}"
                        {% if c['isAdminKey'] %}disabled style="background-color:#ccc;"{% endif %}>
                </td>
                <td>
                    <input type="checkbox" name="active"
                        {% if c['active'] %}checked{% endif %}
                        {% if c['isAdminKey'] %}disabled{% endif %}>
                </td>
                <td>
                    <input type="checkbox" name="is_admin"
                        {% if c['isAdminKey'] %}checked{% endif %}>
                </td>
                <td>
                    <input type="hidden" name="id" value="{{ c['id'] }}">
                    <button name="save_card">Save</button>
                </td>
                <td>
                    <input type="hidden" name="id" value="{{ c['id'] }}">
                    <button name="delete_card">Delete</button>
                </td>
            </form>
        </tr>
        {% endfor %}
        </table>
        """, cards=cards, nav=NAV)

    @app.route("/machine", methods=["GET", "POST"])
    def machine():
        if request.method == "POST":
            action = request.form.get("action")
    
            if action == "adjust_hopper":
                amount = float(request.form["amount"])
                bank_db.adjust_machine_cash("Hoppers", amount)
    
            elif action == "clear_inserter":
                inserter_cash = bank_db.get_machine_cash("Coin_Inserter")
                bank_db.adjust_machine_cash("Coin_Inserter", -inserter_cash)
    
            return redirect("/machine")
    
        hopper_cash = bank_db.get_machine_cash("Hoppers")
        inserter_cash = bank_db.get_machine_cash("Coin_Inserter")
    
        return render_template_string("""
        {{ nav|safe }}
        <h1>Machine Stats</h1>
    
        <h3>Hopper Balance</h3>
        <p><b>Current Cash in Hoppers:</b> £{{ '%.2f'|format(hopper_cash) }}</p>
    
        <h4>Adjust Balance</h4>
        <form method="post">
            <input type="hidden" name="action" value="adjust_hopper">
            Amount (£): <input name="amount">
            <button type="submit">Adjust</button>
        </form>
    
        <hr>
    
        <h3>Coin Inserter Balance</h3>
        <p><b>Current Cash in Coin Inserter:</b> £{{ '%.2f'|format(inserter_cash) }}</p>
    
        <h4>Clear Balance</h4>
        <form method="post">
            <input type="hidden" name="action" value="clear_inserter">
            <button type="submit">Clear</button>
        </form>
        """, hopper_cash=hopper_cash, inserter_cash=inserter_cash, nav=NAV)


    return app
