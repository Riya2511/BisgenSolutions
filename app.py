from flask import Flask, abort, flash, redirect, render_template, request, url_for,make_response,session
import json

from security.authToken import AuthToken
from config import FLASK_SECRET_KEY,JWT_SECRET_KEY
from helper import connect_to_sql
from security.authenticationValidation import auth_required,allowed_user_type

app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_SECRET_KEY

@app.route("/", methods=["GET", "POST"])
def index():
    """Redirects users to the sign-in page."""
    return redirect(url_for("sign_in"))

@app.route("/signin", methods=["GET", "POST"])
def sign_in():
    """Handles user sign-in."""
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        print(f"Email: {email}, Password: {password}")
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
                    "email" : leads_data[0]['email'],
                    "user_type" : leads_data[0]['user_type'],
                    "password" : leads_data[0]['password'],
                    "account_id": leads_data[0]['account_id']
                }
            print(userData)
            authToken = AuthToken().encode(userData)
            session['authToken']  = authToken[0]
            response = make_response(redirect("/leads"))
            return response
        
    return render_template("SignIn.html")


@app.route("/leads", methods=["GET"])
# @auth_required()
@allowed_user_type(['admin'])
def leads(**kwargs):
    print(kwargs['current_user'])
    # print("jererere")
    # print(validateCurrentUser())
    """Displays all leads."""
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

    return render_template("leads.html", leads=leads_data)

@app.route("/users", methods=["GET"])
def users(**kwargs):
    """Displays all users."""
    return "All users placeholder."

@app.route("/accounts", methods=["GET"])
def accounts(**kwargs):
    """Displays all accounts."""
    return "All accounts placeholder."

@app.route("/emails", methods=["GET"])
def emails(**kwargs):
    """Displays all emails."""
    return "All emails placeholder."

@app.route("/emaildetails/<string:email_id>", methods=["GET"])
def email_details(email_id,**kwargs):
    """Displays details of a specific email."""
    return f"Details for email ID: {email_id}"

@app.route("/leaddetails/<string:lead_id>", methods=["GET"])
def lead_details(lead_id,**kwargs):
    """Displays details of a specific lead."""
    return f"Details for lead ID: {lead_id}"

@app.route("/emailleads/<string:email_id>", methods=["GET"])
def email_leads(email_id,**kwargs):
    """Filters leads for a specific email."""
    return f"Leads for email ID: {email_id}"

@app.route("/createuser", methods=["GET", "POST"])
def create_user(**kwargs):
    """Allows admin to create a new user."""
    return "Create user placeholder."

@app.route("/updateuser/<string:user_id>", methods=["GET", "POST"])
def update_user(user_id,**kwargs):
    """Allows admin to update an existing user."""
    return f"Update user ID: {user_id}"

@app.route("/createaccount", methods=["GET", "POST"])
def create_account(**kwargs):
    """Allows admin to create a new account."""
    return "Create account placeholder."

@app.route("/updateaccount/<string:account_id>", methods=["GET", "POST"])
def update_account(account_id,**kwargs):
    """Allows admin to update an existing account."""
    return f"Update account ID: {account_id}"

@app.route("/createaccountemailfilters", methods=["GET", "POST"])
def create_account_email_filters(**kwargs):
    """Allows admin to create email filters for an account."""
    return "Create account email filters placeholder."

@app.route("/updateaccountemailfilters/<string:account_email_filters_id>", methods=["GET", "POST"])
def update_account_email_filters(account_email_filters_id,**kwargs):
    """Allows admin to update email filters for an account."""
    return f"Update account email filters ID: {account_email_filters_id}"

@app.route("/createemailsource", methods=["GET", "POST"])
def create_email_source(**kwargs):
    """Allows admin to create a new email source."""
    return "Create email source placeholder."

@app.route("/updateemailsource/<string:email_source_id>", methods=["GET", "POST"])
def update_email_source(email_source_id,**kwargs):
    """Allows admin to update an email source."""
    return f"Update email source ID: {email_source_id}"

@app.route("/createemailparserregex", methods=["GET", "POST"])
def create_email_parser_regex(**kwargs):
    """Allows admin to create a new email parser regex."""
    return "Create email parser regex placeholder."

@app.route("/updateemailparserregex/<string:email_parser_regex_id>", methods=["GET", "POST"])
def update_email_parser_regex(email_parser_regex_id,**kwargs):
    """Allows admin to update an email parser regex."""
    return f"Update email parser regex ID: {email_parser_regex_id}"

@app.route("/createemailparser", methods=["GET", "POST"])
def create_email_parser(**kwargs):
    """Allows admin to create a new email parser regex."""
    return "Create email parser regex placeholder."

@app.route("/updateemailparser/<string:email_parser_id>", methods=["GET", "POST"])
def update_email_parser(email_parser_id,**kwargs):
    """Allows admin to update an email parser"""
    return f"Update email parser ID: {email_parser_id}"

@app.route("/createemailfetchqueue", methods=["GET", "POST"])
def create_email_fetch_queue(**kwargs):
    """Allows admin to create a new email fetch queue."""
    return "Create email fetch queue placeholder."

@app.route("/updateemailfetchqueue/<string:email_fetch_queue_id>", methods=["GET", "POST"])
def update_email_fetch_queue(email_fetch_queue_id,**kwargs):
    """Allows admin to update an email fetch queue"""
    return f"Update email fetch queue ID: {email_fetch_queue_id}"

def add_email_fetch_job(account_id, rule_id, since_date, batch_size):
    """Adds a new job to the email fetch queue."""
    conn = connect_to_sql()
    if not conn:
        print("Database connection failed.")
        return
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO email_fetch_queue (account_id, rule_id, since_date, batch_size, status)
            VALUES (%s, %s, %s, %s, 'pending')
        """
        cursor.execute(query, (account_id, rule_id, since_date, batch_size))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    app.run(debug=True,host="0.0.0.0")
