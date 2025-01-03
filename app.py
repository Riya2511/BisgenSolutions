import datetime
import json

from flask import (Flask, abort, flash, make_response, redirect,
                   render_template, request, session, url_for)

from config import BATCH_SIZE, FLASK_SECRET_KEY
from helper import connect_to_sql
from security.authenticationValidation import (allowed_user_type,
                                               auth_required, is_authenticated)
from security.authToken import AuthToken

app = Flask(__name__)
app.config["SECRET_KEY"] = FLASK_SECRET_KEY

@app.context_processor
def inject_user_type():
    if 'authToken' in session:
        return dict(user_type=is_authenticated()['user_type'])
    return dict(user_type=None)

@app.route("/", methods=["GET", "POST"])
def index():
    if is_authenticated(): 
        return redirect('/leads')
    return redirect("/signin")

@app.route("/error", methods=["GET"])
def error():
    return render_template("Error.html")

@app.route("/signin", methods=["GET", "POST"])
def sign_in():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        conn = connect_to_sql()
        leads_data = None
        if not conn:
            flash("Failed to connect to the database.")
            return redirect('/signin')
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

@app.route('/signout', methods=["GET"])
def sign_out():
    if 'authToken' in session:
        del session['authToken']
    response = make_response(redirect("/"))
    return response

@app.route("/users", methods=["GET"])
@allowed_user_type(['admin'])
def users(**kwargs):
    conn = connect_to_sql()
    if not conn:
        flash("Failed to connect to the database.")
        return render_template("Users.html", leads=[])
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT * from users where status = 1
        """
        cursor.execute(query)
        leads_data = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return render_template("Users.html", leads=leads_data)

@app.route("/accounts", methods=["GET"])
@allowed_user_type(['admin'])
def accounts(**kwargs):
    conn = connect_to_sql()
    if not conn:
        flash("Failed to connect to the database.")
        return render_template("Accounts.html", leads=[])
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT * from accounts where status = 1
        """
        cursor.execute(query)
        leads_data = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return render_template("Accounts.html", leads=leads_data)

@app.route("/leads", methods=["GET"])
@auth_required()
def leads(**kwargs):
    conn = connect_to_sql()
    if not conn:
        flash("Failed to connect to the database.")
        return render_template("Emails.html", leads=[])
    try:
        cursor = conn.cursor(dictionary=True)
        if is_authenticated()['user_type'] == 'user':
            query = """
            SELECT * from leads where status = 1 and account_id = %s
            """
            cursor.execute(query, (kwargs['current_user']['account_id'],))
        elif is_authenticated()['user_type'] == 'admin':
            query = """
            SELECT * from leads where status = 1
            """
            cursor.execute(query)
        leads_data = cursor.fetchall()
        leads_data.reverse()
    finally:
        cursor.close()
        conn.close()
    return render_template("Leads.html", leads=leads_data)

@app.route("/emails", methods=["GET"])
@auth_required()
def emails(**kwargs):
    conn = connect_to_sql()
    if not conn:
        flash("Failed to connect to the database.")
        return render_template("Emails.html", leads=[])
    try:
        cursor = conn.cursor(dictionary=True)
        if is_authenticated()['user_type'] == "user":
            query = """
            SELECT * from email where account_id = %s
            """
            cursor.execute(query, (kwargs['current_user']['account_id'],))
        elif is_authenticated()['user_type'] == "admin":
            query = """
            SELECT * from email
            """
            cursor.execute(query)
        leads_data = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return render_template("Emails.html", leads=leads_data)

@app.route("/accountemailfilters", methods=["GET"])
@auth_required()
def account_email_filters(**kwargs):
    conn = connect_to_sql()
    if not conn:
        flash("Failed to connect to the database.")
        return render_template("AccountEmailFilters.html", leads=[])
    try:
        cursor = conn.cursor(dictionary=True)
        if is_authenticated()['user_type'] == "user":
            query = """
            SELECT * from account_email_filters where status = 1 and account_id = %s
            """
            cursor.execute(query, (kwargs['current_user']['account_id'],))
        elif is_authenticated()['user_type'] == "admin":
            query = """
            SELECT * from account_email_filters where status = 1
            """
            cursor.execute(query)
        leads_data = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return render_template("AccountEmailFilters.html", leads=leads_data)

@app.route("/emailsource", methods=["GET"])
@auth_required()
def email_source(**kwargs):
    conn = connect_to_sql()
    if not conn:
        flash("Failed to connect to the database.")
        return render_template("EmailSource.html", leads=[])
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT * from email_source where status = 1
        """
        cursor.execute(query)
        leads_data = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return render_template("EmailSource.html", leads=leads_data)

@app.route("/emailparser", methods=["GET"])
@allowed_user_type(['admin'])
def email_parser(**kwargs):
    conn = connect_to_sql()
    if not conn:
        flash("Failed to connect to the database.")
        return render_template("EmailParser.html", leads=[])
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT * from email_parser where status = 1
        """
        cursor.execute(query)
        leads_data = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return render_template("EmailParser.html", leads=leads_data)

@app.route("/emailparserregex", methods=["GET"])
@allowed_user_type(['admin'])
def email_parser_regex(**kwargs):
    conn = connect_to_sql()
    if not conn:
        flash("Failed to connect to the database.")
        return render_template("EmailParserRegex.html", leads=[])
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT * from email_parser_regexes where status = 1
        """
        cursor.execute(query)
        leads_data = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return render_template("EmailParserRegex.html", leads=leads_data)

@app.route("/emaildetails/<string:email_id>", methods=["GET"])
@auth_required()
def email_details(email_id, **kwargs):
    conn = connect_to_sql()
    if not conn:
        flash("Failed to connect to the database.")
        return render_template("EmailDetails.html", leads=[])
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT * from email where id = %s
        """
        cursor.execute(query, (email_id, ))
        leads_data = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()
    return render_template("EmailDetails.html", leads=leads_data)

@app.route("/leaddetails/<string:lead_id>", methods=["GET"])
@auth_required()
def lead_details(lead_id, **kwargs):
    conn = connect_to_sql()
    if not conn:
        flash("Failed to connect to the database.")
        return render_template("LeadDetails.html", leads=[])
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT * from leads where status = 1 and id = %s
        """
        cursor.execute(query, (lead_id, ))
        leads_data = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()
    return render_template("LeadDetails.html", leads=leads_data)

@app.route("/emailleads/<string:email_id>", methods=["GET"])
@auth_required()
def email_leads(email_id, **kwargs):
    conn = connect_to_sql()
    if not conn:
        flash("Failed to connect to the database.")
        return render_template("Leads.html", leads=[])
    try:
        cursor = conn.cursor(dictionary=True)
        query = """
        SELECT * from leads where status = 1 and email_id = %s
        """
        cursor.execute(query, (email_id, ))
        leads_data = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()
    return render_template("Leads.html", leads=leads_data)

@app.route("/createuser", methods=["GET", "POST"])
@allowed_user_type(['admin'])
def create_user(**kwargs):
    if request.method == "POST":
        account_id = request.form['accountId']
        user_name = request.form['userName']
        user_email = request.form['userEmail']
        user_phone = request.form['userPhone']
        user_password = request.form['userPassword']
        user_type = request.form['userType']
        user_status = request.form['userStatus']
        if not account_id or not user_name or not user_email or not user_phone or not user_password or not user_type or not user_status:
            flash("All fields are required.", "danger")
            return redirect(url_for("create_user"))

        try:
            hashed_password = user_password
            conn = connect_to_sql()
            if not conn:
                flash("Failed to connect to the database.", "danger")
                return render_template("CreateUser.html")
            
            cursor = conn.cursor()
            query = """
            INSERT INTO users (account_id, name, email, phone, password, user_type, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (account_id, user_name, user_email, user_phone, hashed_password, user_type, user_status))
            conn.commit()

            cursor.close()
            conn.close()
            flash("User created successfully.", "success")
            return redirect(url_for('users'))

        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")
            return redirect(url_for("create_user"))
    try:
        conn = connect_to_sql()
        if not conn:
            flash("Failed to connect to the database.", "danger")
            return render_template("CreateUser.html", accounts=[])

        cursor = conn.cursor()
        # Fetch account id and name from the accounts table
        accounts_query = "SELECT id, name FROM accounts"
        cursor.execute(accounts_query)
        accounts = cursor.fetchall()  # Returns a list of tuples (id, name)

        cursor.close()
        conn.close()
    except Exception as e:
        flash(f"An error occurred while fetching accounts: {str(e)}", "danger")
        accounts = []
    return render_template("CreateUser.html", accounts=accounts)

@app.route("/updateuser/<string:user_id>", methods=["GET", "POST"])
@allowed_user_type(['admin'])
def update_user(user_id, **kwargs):
    conn = connect_to_sql()
    if not conn:
        flash("Failed to connect to the database.", "danger")
        return redirect(url_for('users'))
    try:
        cursor = conn.cursor(dictionary=True)
        if request.method == "GET":
            query = """
            SELECT account_id, name, email, phone, password, user_type, status
            FROM users
            WHERE id = %s
            """
            cursor.execute(query, (user_id,))
            user = cursor.fetchone()
            cursor1 = conn.cursor()
            accounts_query = "SELECT id, name FROM accounts"
            cursor1.execute(accounts_query)
            accounts = cursor1.fetchall()  
            cursor1.close()
            if user and accounts:
                return render_template("UpdateUser.html", user=user, accounts=accounts)
            else:
                flash("User not found.", "danger")
                return redirect(url_for('users'))
        elif request.method == "POST":
            account_id = request.form['accountId']
            user_name = request.form['userName']
            user_email = request.form['userEmail']
            user_phone = request.form['userPhone']
            user_password = request.form['userPassword']
            user_type = request.form['userType']
            user_status = request.form['userStatus']
            if user_password:
                hashed_password = user_password
            else:
                hashed_password = user['password']
            update_query = """
            UPDATE users
            SET account_id = %s, name = %s, email = %s, phone = %s, password = %s, user_type = %s, status = %s
            WHERE id = %s
            """
            cursor.execute(update_query, (account_id, user_name, user_email, user_phone, hashed_password, user_type, user_status, user_id))
            conn.commit()
            flash("User updated successfully.", "success")
            return redirect(url_for('users'))
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('users')) 
    finally:
        cursor.close()
        conn.close()

@app.route("/createaccount", methods=["GET", "POST"])
@allowed_user_type(['admin'])
def create_account(**kwargs):
    if request.method == "POST":
        account_name = request.form['accountName']
        smtp_host = request.form['smtpHost']
        smtp_username = request.form['smtpUsername']
        smtp_password = request.form['smtpPassword']
        smtp_encryption = request.form['smtpEncryption']
        smtp_port = request.form['smtpPort']
        try:
            conn = connect_to_sql()

            cursor = conn.cursor()

            query = """
            INSERT INTO accounts (name, smtp_host, smtp_username, smtp_password, smtp_encryption, smtp_port)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (account_name, smtp_host, smtp_username, smtp_password, smtp_encryption, smtp_port))
            conn.commit()

            flash("Account created successfully!", "success")
            return redirect(url_for('accounts')) 
        except Exception as err:
            flash(f"Error: {err}", "danger")
            return redirect(url_for('create_account'))
        finally:
            cursor.close()
            conn.close()

    return render_template("CreateAccount.html", leads=[])

@app.route("/updateaccount/<string:account_id>", methods=["GET", "POST"])
@allowed_user_type(['admin'])
def update_account(account_id, **kwargs):
    conn = connect_to_sql()
    cursor = conn.cursor()
    if request.method == "GET":
        cursor.execute("SELECT * FROM accounts WHERE id = %s", (account_id,))
        account_data = cursor.fetchone()

        if account_data:
            account = {
                'account_name': account_data[1],
                'smtp_host': account_data[2],
                'smtp_username': account_data[3],
                'smtp_password': account_data[4],
                'smtp_encryption': account_data[5],
                'smtp_port': account_data[6]
            }
            return render_template("UpdateAccount.html", account=account)

        flash("Account not found", "danger")
        return redirect(url_for('accounts'))
    elif request.method == "POST":
        account_name = request.form['accountName']
        smtp_host = request.form['smtpHost']
        smtp_username = request.form['smtpUsername']
        smtp_password = request.form['smtpPassword']
        smtp_encryption = request.form['smtpEncryption']
        smtp_port = request.form['smtpPort']
        try:
            query = """
            UPDATE accounts
            SET name = %s, smtp_host = %s, smtp_username = %s,
                smtp_password = %s, smtp_encryption = %s, smtp_port = %s
            WHERE id = %s
            """
            cursor.execute(query, (account_name, smtp_host, smtp_username, smtp_password, smtp_encryption, smtp_port, account_id))
            conn.commit()

            flash("Account updated successfully!", "success")
            return redirect(url_for('accounts')) 

        except Exception as err:
            flash(f"Error: {err}", "danger")
            return redirect(url_for('update_account', account_id=account_id)) 

        finally:
            cursor.close()
            conn.close()

@app.route("/createaccountemailfilters", methods=["GET", "POST"])
@auth_required()
def create_account_email_filters(**kwargs):
    if request.method == "POST":
        try:
            form_data = {
                'rule': request.form.get('filterRule', ''),
                'filters_on_subject': request.form.get('filtersOnSubject', ''),
                'filters_on_from': request.form.get('filtersOnFrom', ''),
                'filters_on_body': request.form.get('filtersOnBody', ''),
                'account_id': request.form.get('accountId', ''),
                'email_source_id': request.form.get('emailSourceId', ''),
                'status': request.form.get('filterStatus', '')
            }
            if not all(form_data.values()):
                flash("All fields are required.", "danger")
                return redirect(url_for("create_account_email_filters"))
            conn = connect_to_sql()
            if not conn:
                flash("Failed to connect to the database.", "danger")
                return render_template("CreateAccountEmailFilter.html")
            
            cursor = conn.cursor()
            query = """
            INSERT INTO account_email_filters 
            (rule, filters_on_subject, filters_on_from, filters_on_body, 
             account_id, email_source_id, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(query, (
                form_data['rule'],
                form_data['filters_on_subject'],
                form_data['filters_on_from'],
                form_data['filters_on_body'],
                form_data['account_id'],
                form_data['email_source_id'],
                form_data['status']
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            flash("Email filter created successfully.", "success")
            return redirect(url_for("account_email_filters"))

        except Exception as e:
            print(e)
            flash(f"An error occurred: {str(e)}", "danger")
            return redirect(url_for("create_account_email_filters"))
    try:
        conn = connect_to_sql()
        if not conn:
            flash("Failed to connect to the database.", "danger")
            return render_template("CreateAccountEmailFilter.html", accounts=[])

        cursor = conn.cursor()
        # Fetch account id and name from the accounts table
        accounts_query = "SELECT id, name FROM accounts"
        cursor.execute(accounts_query)
        accounts = cursor.fetchall()  # Returns a list of tuples (id, name)
        email_source_query = "SELECT id, name FROM email_source"
        cursor.execute(email_source_query)
        email_sources = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f"An error occurred while fetching accounts: {str(e)}", "danger")
        accounts = []            
        email_sources = []
    return render_template("CreateAccountEmailFilter.html", accounts=accounts, email_sources=email_sources)

@app.route("/updateaccountemailfilters/<string:account_email_filters_id>", methods=["GET", "POST"])
@auth_required()
def update_account_email_filters(account_email_filters_id, **kwargs):
    conn = connect_to_sql()
    if not conn:
        flash("Failed to connect to the database.", "danger")
        return redirect(url_for('update_account_email_filters'))

    try:
        cursor = conn.cursor(dictionary=True)
        
        if request.method == "GET":
            query = """
            SELECT rule, filters_on_subject, filters_on_from, filters_on_body, account_id, email_source_id, email_key_colums, status
            FROM account_email_filters
            WHERE id = %s
            """
            cursor.execute(query, (account_email_filters_id,))
            filter_data = cursor.fetchone()
            cursor1 = conn.cursor()
            accounts_query = "SELECT id, name FROM accounts"
            cursor1.execute(accounts_query)
            accounts = cursor1.fetchall() 
            email_source_query = "SELECT id, name FROM email_source"
            cursor1.execute(email_source_query)
            email_sources = cursor1.fetchall()
            cursor1.close()
            if filter_data and accounts and email_sources:
                return render_template("UpdateAccountEmailFilter.html", email_filter=filter_data, accounts=accounts, email_sources=email_sources)

        elif request.method == "POST":
            rule = request.form['filterRule']
            filters_on_subject = request.form['filtersOnSubject']
            filters_on_from = request.form['filtersOnFrom']
            filters_on_body = request.form['filtersOnBody']
            account_id = request.form['accountId']
            email_source_id = request.form['emailSourceId']
            email_key_columns = request.form['emailKeyColumn']
            status = request.form['filterStatus']

            update_query = """
            UPDATE account_email_filters
            SET rule = %s, filters_on_subject = %s, filters_on_from = %s, filters_on_body = %s, account_id = %s, 
                email_source_id = %s, email_key_colums = %s, status = %s
            WHERE id = %s
            """
            cursor.execute(update_query, (rule, filters_on_subject, filters_on_from, filters_on_body, account_id, email_source_id, email_key_columns, status, account_email_filters_id))
            conn.commit()

            flash("Email filter updated successfully.", "success")
            return redirect(url_for("update_account_email_filters", account_email_filters_id=account_email_filters_id))

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('update_account_email_filters', account_email_filters_id=account_email_filters_id))
    finally:
        cursor.close()
        conn.close()

@app.route("/createemailsource", methods=["GET", "POST"])
@auth_required()
def create_email_source(**kwargs):
    if request.method == "POST":
        source_name = request.form['sourceName']
        source_status = request.form['sourceStatus']

        if not source_name or source_status not in ["0", "1"]:
            flash("All fields are required and status must be 0 or 1.", "danger")
            return redirect(url_for("create_email_source"))

        try:
            conn = connect_to_sql()
            if not conn:
                flash("Failed to connect to the database.", "danger")
                return render_template("CreateEmailSource.html")

            cursor = conn.cursor()
            query = """
            INSERT INTO email_source (name, status)
            VALUES (%s, %s)
            """
            cursor.execute(query, (source_name, source_status))
            conn.commit()

            cursor.close()
            conn.close()
            flash("Email source created successfully.", "success")
            return redirect(url_for("email_source"))

        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")
            return redirect(url_for("create_email_source"))

    return render_template("CreateEmailSource.html")

@app.route("/updateemailsource/<string:email_source_id>", methods=["GET", "POST"])
@auth_required()
def update_email_source(email_source_id, **kwargs):
    conn = connect_to_sql()
    if not conn:
        flash("Failed to connect to the database.", "danger")
        return redirect(url_for('update_email_source'))
    try:
        cursor = conn.cursor(dictionary=True)

        if request.method == "GET":
            query = """
            SELECT id, name, status
            FROM email_source
            WHERE id = %s
            """
            cursor.execute(query, (email_source_id,))
            email_source = cursor.fetchone()
            if email_source:
                return render_template("UpdateEmailSource.html", email_source=email_source)
            else:
                flash("Email source not found.", "danger")
                return redirect(url_for('email_source'))

        elif request.method == "POST":
            source_name = request.form['sourceName']
            source_status = request.form['sourceStatus']

            if not source_name or source_status not in ["0", "1"]:
                flash("All fields are required and status must be 0 or 1.", "danger")
                return redirect(url_for("update_email_source", email_source_id=email_source_id))

            query = """
            UPDATE email_source
            SET name = %s, status = %s
            WHERE id = %s
            """
            cursor.execute(query, (source_name, source_status, email_source_id))
            conn.commit()

            flash("Email source updated successfully.", "success")
            return redirect(url_for('email_source'))

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('email_source'))

    finally:
        cursor.close()
        conn.close()

@app.route("/createemailparserregex", methods=["GET", "POST"])
@allowed_user_type(['admin'])
def create_email_parser_regex(**kwargs):
    if request.method == "POST":
        form_data = request.form
        email_parser_id = form_data.get("emailParserId")
        regex = form_data.get("regex")
        sample_data = form_data.get("sampleData")
        sample_output = form_data.get("sampleOutput")
        email_column_mapped = form_data.get("emailColumnMapped")
        status = form_data.get("regexStatus")

        # Validate inputs
        if not email_parser_id or not regex or not sample_data or not sample_output or not email_column_mapped or status not in ["0", "1"]:
            flash("Invalid input data. Please check your entries.", "danger")
            return redirect(url_for("create_email_parser_regex"))

        try:
            # Database insertion logic
            with connect_to_sql() as connection:
                cursor = connection.cursor()
                insert_query = """
                    INSERT INTO email_parser_regexes (email_parser_id, regex, sample_data, sample_output, email_column_mapped, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (email_parser_id, regex, sample_data, sample_output, email_column_mapped, int(status)))
                connection.commit()
            flash("Email Parser Regex created successfully!", "success")
            return redirect(url_for("email_parser_regex"))
        except Exception as e:
            connection.rollback()
            flash(f"Failed to create Email Parser Regex. Error: {str(e)}", "danger")
        
        return redirect(url_for("create_email_parser_regex"))
    try:
        conn = connect_to_sql()
        if not conn:
            flash("Failed to connect to the database.", "danger")
            return render_template("CreateEmailParserRegex.html", accounts=[])
        cursor = conn.cursor()
        email_parser_query = "SELECT id, parsing_name FROM email_parser"
        cursor.execute(email_parser_query)
        email_parsers = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f"An error occurred while fetching accounts: {str(e)}", "danger")        
        email_parsers = []
    return render_template("CreateEmailParserRegex.html", email_parsers=email_parsers)

@app.route("/updateemailparserregex/<string:email_parser_regex_id>", methods=["GET", "POST"])
@allowed_user_type(['admin'])
def update_email_parser_regex(email_parser_regex_id, **kwargs):
    conn = connect_to_sql()
    if not conn:
        flash("Failed to connect to the database.", "danger")
        return redirect(url_for('email_parser_regex'))
    try:
        cursor = conn.cursor(dictionary=True)
        if request.method == "GET":
            query = """
            SELECT *
            FROM email_parser_regexes
            WHERE id = %s
            """
            cursor.execute(query, (email_parser_regex_id,))
            email_source = cursor.fetchone()
            cursor1 = conn.cursor()
            email_parser_query = "SELECT id, parsing_name FROM email_parser"
            cursor1.execute(email_parser_query)
            email_parsers = cursor1.fetchall()
            cursor1.close()
            if email_source and email_parsers:
                return render_template("UpdateEmailParserRegex.html", regex=email_source, email_parsers=email_parsers)
            else:
                flash("Email source not found.", "danger")
                return redirect(url_for('email_parser_regex'))
        
        elif request.method == "POST":
            email_parser_id = request.form['emailParserId']
            regex = request.form['regex']
            sampleData = request.form['sampleData']
            sampleOutput = request.form['sampleOutput']
            emailColumnMapped = request.form['emailColumnMapped']
            status = request.form['regexStatus']


            if not email_parser_id or status not in ["0", "1"]:
                flash("All fields are required and status must be 0 or 1.", "danger")
                return redirect(url_for("email_parser_regex", email_source_id=email_parser_regex_id))

            query = """
            UPDATE email_parser_regexes
            SET email_parser_id = %s, regex = %s, sample_data = %s, sample_output = %s, email_column_mapped = %s, status = %s
            WHERE id = %s
            """
            cursor.execute(query, (email_parser_id, regex, sampleData, sampleOutput, emailColumnMapped, status, email_parser_regex_id))
            conn.commit()

            flash("Email source updated successfully.", "success")
            return redirect(url_for('email_parser_regex'))

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('email_parser_regex'))

    finally:
        cursor.close()
        conn.close()

@app.route("/createemailparser", methods=["GET", "POST"])
@allowed_user_type(['admin'])
def create_email_parser(**kwargs):
    if request.method == "POST":
        form_data = request.form
        parsing_name = form_data.get("parsingName")
        email_source_id = form_data.get("emailSourceId")
        status = form_data.get("parserStatus")
        if not parsing_name or not email_source_id or status not in ["0", "1"]:
            flash("Invalid input data. Please check your entries.", "danger")
            return redirect(url_for("create_email_parser"))

        try:
            with connect_to_sql() as connection:
                cursor = connection.cursor()
                insert_query = """
                    INSERT INTO email_parser (parsing_name, email_source_id, status)
                    VALUES (%s, %s, %s)
                """
                cursor.execute(insert_query, (parsing_name, email_source_id, int(status)))
                connection.commit()
            flash("Email Parser created successfully!", "success")
            return redirect(url_for("email_parser"))
        except Exception as e:
            connection.rollback()
            flash(f"Failed to create Email Parser. Error: {str(e)}", "danger")
        
        return redirect(url_for("create_email_parser"))
    try:
        conn = connect_to_sql()
        if not conn:
            flash("Failed to connect to the database.", "danger")
            return render_template("CreateEmailParser.html", accounts=[])
        cursor = conn.cursor()
        email_source_query = "SELECT id, name FROM email_source"
        cursor.execute(email_source_query)
        email_sources = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        flash(f"An error occurred while fetching accounts: {str(e)}", "danger")        
        email_sources = []
    return render_template("CreateEmailParser.html", email_sources = email_sources)

@app.route("/updateemailparser/<string:email_parser_id>", methods=["GET", "POST"])
@allowed_user_type(['admin'])
def update_email_parser(email_parser_id, **kwargs):
    conn = connect_to_sql()
    if not conn:
        flash("Failed to connect to the database.", "danger")
        return redirect(url_for('email_parser')) 
    try:
        cursor = conn.cursor(dictionary=True)
        if request.method == "GET":
            query = """
            SELECT *
            FROM email_parser
            WHERE id = %s
            """
            cursor.execute(query, (email_parser_id,))
            email_source = cursor.fetchone()
            cursor1 = conn.cursor()
            email_source_query = "SELECT id, name FROM email_source"
            cursor1.execute(email_source_query)
            email_sources = cursor1.fetchall()
            cursor1.close()
            if email_source and email_sources:
                return render_template("UpdateEmailParser.html", parser=email_source, email_sources=email_sources)
            else:
                flash("Email source not found.", "danger")
                return redirect(url_for('email_parser'))
        
        elif request.method == "POST":
            parsingName = request.form['parsingName']
            emailSourceId = request.form['emailSourceId']
            parserStatus = request.form['parserStatus']

            query = """
            UPDATE email_parser
            SET parsing_name = %s, email_source_id = %s, status = %s
            WHERE id = %s
            """
            cursor.execute(query, (parsingName, emailSourceId, parserStatus, email_parser_id))
            conn.commit()

            flash("Email source updated successfully.", "success")
            return redirect(url_for('email_parser')) 

    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('email_parser')) 

    finally:
        cursor.close()
        conn.close()

# @app.route("/createemailfetchqueue", methods=["GET", "POST"])
# @allowed_user_type(['admin'])
# def create_email_fetch_queue(**kwargs):
#     conn = connect_to_sql()
#     if not conn:
#         flash("Failed to connect to the database.")
#         return render_template("index.html", accounts=[], rules=[])
#     cursor = conn.cursor(dictionary=True)
#     cursor.execute("SELECT id, name FROM accounts where status = 1")
#     accounts = cursor.fetchall()
#     cursor.execute("SELECT id, rule FROM account_email_filters where status = 1")
#     rules = cursor.fetchall()
#     cursor.close()
#     conn.close()
#     if request.method == "POST":
#         account_id = request.form.get("account")
#         rule_id = request.form.get("rule")
#         since_date = request.form.get("since_date")
#         if not account_id or not rule_id:
#             flash("Please select both account and rule.")
#             return redirect(url_for("create_email_fetch_queue"))
#         try:
#             since_date = datetime.datetime.strptime(since_date, "%Y-%m-%d").date()
#         except ValueError:
#             flash("Invalid date format. Please use YYYY-MM-DD.")
#             return redirect(url_for("create_email_fetch_queue"))
#         conn = connect_to_sql()
#         if not conn:
#             return
#         try:
#             cursor = conn.cursor()
#             query = """
#                 INSERT INTO email_fetch_queue (account_id, rule_id, since_date, batch_size, status)
#                 VALUES (%s, %s, %s, %s, 'pending')
#             """
#             cursor.execute(query, (account_id, rule_id, since_date, BATCH_SIZE))
#             conn.commit()
#         finally:
#             cursor.close()
#             conn.close()
#         flash("Job added to fetch emails. They will be processed shortly.")
#         return redirect('/createemailfetchqueue')
#     return render_template("CreateEmailFetchQueue.html", accounts=accounts, rules=rules)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
