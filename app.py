import json
from datetime import datetime

from flask import Flask, flash, redirect, render_template, request, url_for

from config import BATCH_SIZE
from helper import connect_to_sql

app = Flask(__name__)
app.secret_key = "your_secret_key"


# route everytime to signin first time
@app.route("/", methods=["GET", "POST"])
def index():
    conn = connect_to_sql()
    if not conn:
        flash("Failed to connect to the database.")
        return render_template("index.html", accounts=[], rules=[])

    cursor = conn.cursor(dictionary=True)

    # Fetch accounts and rules for dropdowns
    cursor.execute("SELECT id, name FROM accounts where status = 1")
    accounts = cursor.fetchall()

    cursor.execute("SELECT id, rule FROM account_email_filters where status = 1")
    rules = cursor.fetchall()

    cursor.close()
    conn.close()

    if request.method == "POST":
        account_id = request.form.get("account")
        rule_id = request.form.get("rule")
        since_date = request.form.get("since_date")  # Get the since date from the form

        if not account_id or not rule_id:
            flash("Please select both account and rule.")
            return redirect(url_for("index"))

        # Parse since_date
        try:
            since_date = datetime.strptime(since_date, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.")
            return redirect(url_for("index"))

        # Store job in email_fetch_queue
        add_email_fetch_job(account_id, rule_id, since_date, BATCH_SIZE)
        flash("Job added to fetch emails. They will be processed shortly.")

        return redirect(url_for("index"))

    return render_template("index.html", accounts=accounts, rules=rules)


# Sign - In
@app.route("/signin", methods=["GET"])
def sign_in():
    pass


# - all leads
@app.route("/leads", methods=["GET"])
def leads():
    conn = connect_to_sql()
    cursor = conn.cursor(dictionary=True)

    # Join query to get leads and corresponding email data
    query = """
    SELECT 
        l.*,
        e.mail_regex_applied,
        e.mail_regex_output
    FROM leads l
    LEFT JOIN email e ON l.email_id = e.id
    WHERE l.status = 1
    ORDER BY l.created_by DESC
    """

    cursor.execute(query)
    leads_data = cursor.fetchall()

    # Process the JSON strings
    for lead in leads_data:
        if lead["mail_regex_applied"]:
            try:
                # print(lead['mail_regex_applied'])
                lead["mail_regex_applied"] = json.loads(lead["mail_regex_applied"])
            except:
                lead["mail_regex_applied"] = lead["mail_regex_applied"]

        if lead["mail_regex_output"]:
            try:
                lead["mail_regex_output"] = lead["mail_regex_output"].split("\n")
            except:
                lead["mail_regex_output"] = []

    cursor.close()
    conn.close()

    return render_template("leads.html", leads=leads_data)


# All users
@app.route("/users", methods=["GET"])
def users():
    pass


# All accounts
@app.route("/accounts", methods=["GET"])
def acccounts():
    pass


# - All emails
@app.route("/emails", methods=["GET"])
def emails():
    pass


# - view more of 1 email button
@app.route("/emaildetails/<str:email_id>", methods=["GET"])
def email_details():
    pass


# - view more of 1 lead button
@app.route("/leaddetails/<str:lead_id>", methods=["GET"])
def lead_details():
    pass


# - basic filter to filter all leads from one email
@app.route("/emailleads/<str:email_id>", methods=["GET"])
def email_leads():
    pass


# - create user only admin
@app.route("/createuser", methods=["GET"])
def create_user():
    pass


@app.route("/updateuser/<str:user_id>", methods=["GET"])
def update_user():
    pass


# - create account only admin
@app.route("/createaccount", methods=["GET"])
def create_account():
    pass


# - uodate account only admin
@app.route("/updateaccount/<str:account_id>", methods=["GET"])
def update_account():
    pass


# - ac email filters create/update
@app.route("/createaccountemailfilters", methods=["GET"])
def create_account_email_filters():
    pass


@app.route("/updateaccountemailfilters/<str:account_email_filters_id>", methods=["GET"])
def update_account_email_filters():
    pass


# - email_source  creste/update
@app.route("/createemailsource", methods=["GET"])
def create_email_source():
    pass


@app.route("/updateemailsource/<str:email_source_id>", methods=["GET"])
def update_email_source():
    pass


# - email parser regex create/update
@app.route("/createemailparserregex", methods=["GET"])
def create_email_parser_regex():
    pass


@app.route("/updateemailparserregex/<str:email_parser_regex_id>", methods=["GET"])
def update_email_parser_regex():
    pass


def add_email_fetch_job(account_id, rule_id, since_date, batch_size):
    """Add a new job to email_fetch_queue with pending status."""
    conn = connect_to_sql()
    if not conn:
        print("Database connection failed.")
        return

    cursor = conn.cursor()
    query = """
        INSERT INTO email_fetch_queue (account_id, rule_id, since_date, batch_size, status)
        VALUES (%s, %s, %s, %s, 'pending')
    """
    cursor.execute(query, (account_id, rule_id, since_date, batch_size))
    conn.commit()
    cursor.close()
    conn.close()


if __name__ == "__main__":
    app.run(debug=True)
