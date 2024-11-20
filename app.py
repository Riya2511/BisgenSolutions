from flask import Flask, abort, flash, redirect, render_template, request, url_for, make_response, session
import json
import datetime
from security.authToken import AuthToken
from config import FLASK_SECRET_KEY, BATCH_SIZE
from helper import connect_to_sql
from security.authenticationValidation import auth_required, allowed_user_type, is_authenticated

app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_SECRET_KEY

@app.route("/", methods=["GET", "POST"])
def index():
    if is_authenticated(): 
        return redirect('/leads')
    return redirect("/signin")

@app.route("/signin", methods=["GET", "POST"])
def sign_in():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        conn = connect_to_sql()
        leads_data = None
        if not conn:
            flash("Failed to connect to the database.")
            return render_template("leads.html", leads=[])
        try:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT * FROM users WHERE email = %s AND password = %s"
            cursor.execute(query, (email, password))
            leads_data = cursor.fetchall()
            if not leads_data:
                return redirect(url_for("sign_in"))
        finally:
            cursor.close()
            conn.close()
        if leads_data:
            userData = {
                "email": leads_data[0]['email'],
                "user_type": leads_data[0]['user_type'],
                "password": leads_data[0]['password'],
                "account_id": leads_data[0]['account_id']
            }
            authToken = AuthToken().encode(userData)
            session['authToken'] = authToken[0]
            response = make_response(redirect("/leads"))
            return response
    return render_template("SignIn.html")




@app.route("/leads", methods=["GET"])
@auth_required()
def leads(**kwargs):
    conn = connect_to_sql()
    if not conn:
        flash("Failed to connect to the database.")
        return render_template("leads.html", leads=[])
    try:
        cursor = conn.cursor(dictionary=True)
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
        for lead in leads_data:
            if lead["mail_regex_applied"]:
                try:
                    lead["mail_regex_applied"] = json.loads(lead["mail_regex_applied"])
                except json.JSONDecodeError:
                    pass
            if lead["mail_regex_output"]:
                lead["mail_regex_output"] = lead["mail_regex_output"].split("\n")
    finally:
        cursor.close()
        conn.close()
    return render_template("Leads.html", leads=leads_data)

@app.route("/users", methods=["GET"])
@allowed_user_type(['admin'])
def users(**kwargs):
    leads_data = []
    return render_template("Users.html", leads=leads_data)

@app.route("/accounts", methods=["GET"])
@allowed_user_type(['admin'])
def accounts(**kwargs):
    leads_data = []
    return render_template("Accounts.html", leads=leads_data)

@app.route("/emails", methods=["GET"])
@auth_required()
def emails(**kwargs):
    leads_data = []
    return render_template("Emails.html", leads=leads_data)

@app.route("/emaildetails/<string:email_id>", methods=["GET"])
@auth_required()
def email_details(email_id, **kwargs):
    leads_data = []
    return render_template("EmailDetails.html", leads=leads_data)

@app.route("/leaddetails/<string:lead_id>", methods=["GET"])
@auth_required()
def lead_details(lead_id, **kwargs):
    leads_data = []
    return render_template("LeadDetails.html", leads=leads_data)

@app.route("/emailleads/<string:email_id>", methods=["GET"])
@auth_required()
def email_leads(email_id, **kwargs):
    leads_data = []
    return render_template("Leads.html", leads=leads_data)

@app.route("/createuser", methods=["GET", "POST"])
@allowed_user_type(['admin'])
def create_user(**kwargs):
    leads_data = []
    return render_template("CreateUser.html", leads=leads_data)

@app.route("/updateuser/<string:user_id>", methods=["GET", "POST"])
@allowed_user_type(['admin'])
def update_user(user_id, **kwargs):
    return f"Update user ID: {user_id}"

@app.route("/createaccount", methods=["GET", "POST"])
@allowed_user_type(['admin'])
def create_account(**kwargs):
    leads_data = []
    return render_template("CreateAccount.html", leads=leads_data)

@app.route("/updateaccount/<string:account_id>", methods=["GET", "POST"])
@allowed_user_type(['admin'])
def update_account(account_id, **kwargs):
    return f"Update account ID: {account_id}"

@app.route("/createaccountemailfilters", methods=["GET", "POST"])
@auth_required()
def create_account_email_filters(**kwargs):
    leads_data = []
    return render_template("CreateAccountEmailFilter.html", leads=leads_data)

@app.route("/updateaccountemailfilters/<string:account_email_filters_id>", methods=["GET", "POST"])
@auth_required()
def update_account_email_filters(account_email_filters_id, **kwargs):
    return f"Update account email filters ID: {account_email_filters_id}"

@app.route("/createemailsource", methods=["GET", "POST"])
@auth_required()
def create_email_source(**kwargs):
    leads_data = []
    return render_template("CreateEmailSource.html", leads=leads_data)

@app.route("/updateemailsource/<string:email_source_id>", methods=["GET", "POST"])
@auth_required()
def update_email_source(email_source_id, **kwargs):
    return f"Update email source ID: {email_source_id}"

@app.route("/createemailparserregex", methods=["GET", "POST"])
@auth_required()
def create_email_parser_regex(**kwargs):
    leads_data = []
    return render_template("CreateEmailParserRegex.html", leads=leads_data)

@app.route("/updateemailparserregex/<string:email_parser_regex_id>", methods=["GET", "POST"])
@auth_required()
def update_email_parser_regex(email_parser_regex_id, **kwargs):
    return f"Update email parser regex ID: {email_parser_regex_id}"

@app.route("/createemailparser", methods=["GET", "POST"])
@auth_required()
def create_email_parser(**kwargs):
    leads_data = []
    return render_template("CreateEmailParser.html", leads=leads_data)

@app.route("/updateemailparser/<string:email_parser_id>", methods=["GET", "POST"])
@auth_required()
def update_email_parser(email_parser_id, **kwargs):
    return f"Update email parser ID: {email_parser_id}"

@app.route("/createemailfetchqueue", methods=["GET", "POST"])
@auth_required()
def create_email_fetch_queue(**kwargs):
    conn = connect_to_sql()
    if not conn:
        flash("Failed to connect to the database.")
        return render_template("index.html", accounts=[], rules=[])
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM accounts where status = 1")
    accounts = cursor.fetchall()
    cursor.execute("SELECT id, rule FROM account_email_filters where status = 1")
    rules = cursor.fetchall()
    cursor.close()
    conn.close()
    if request.method == "POST":
        account_id = request.form.get("account")
        rule_id = request.form.get("rule")
        since_date = request.form.get("since_date")
        if not account_id or not rule_id:
            flash("Please select both account and rule.")
            return redirect(url_for("index"))
        try:
            since_date = datetime.datetime.strptime(since_date, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.")
            return redirect(url_for("index"))
        conn = connect_to_sql()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            query = """
                INSERT INTO email_fetch_queue (account_id, rule_id, since_date, batch_size, status)
                VALUES (%s, %s, %s, %s, 'pending')
            """
            cursor.execute(query, (account_id, rule_id, since_date, BATCH_SIZE))
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        flash("Job added to fetch emails. They will be processed shortly.")
        return redirect('/createemailfetchqueue')
    return render_template("CreateEmailFetchQueue.html", accounts=accounts, rules=rules)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
