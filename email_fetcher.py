import imaplib
import email
from email.header import decode_header
import json
from datetime import datetime
from config import BATCH_SIZE, FETCH_SINCE_DATE
from helper import connect_to_sql, get_full_body_content, convert_to_sql_date

def auto_create_email_fetch_queue():
    conn = connect_to_sql()
    if not conn:
        print("Failed to connect to the database.")
        return

    cursor = conn.cursor(dictionary=True)
    try:
        # Fetch all account_email_filters IDs not in email_fetch_queue.rule_id
        query = """
            SELECT aef.id AS rule_id, aef.account_id
            FROM account_email_filters aef
            LEFT JOIN email_fetch_queue efq ON aef.id = efq.rule_id
            WHERE efq.rule_id IS NULL
        """
        cursor.execute(query)
        filters_to_add = cursor.fetchall()

        if not filters_to_add:
            print("No new rules to add to email_fetch_queue.")
            return

        # Prepare data for insertion
        since_date = datetime.strptime(FETCH_SINCE_DATE, "%d-%m-%Y").date()
        batch_size = BATCH_SIZE
        status = 'pending'

        insert_query = """
            INSERT INTO email_fetch_queue (account_id, rule_id, since_date, batch_size, status)
            VALUES (%s, %s, %s, %s, %s)
        """
        for filter_row in filters_to_add:
            cursor.execute(
                insert_query,
                (filter_row["account_id"], filter_row["rule_id"], since_date, batch_size, status)
            )

        conn.commit()
        print(f"Added {len(filters_to_add)} entries to email_fetch_queue.")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        cursor.close()
        conn.close()

def fetch_emails_by_rule(rule_id, since_date, batch_size):
    conn = connect_to_sql()
    if not conn:
        print("Database connection failed.")
        return []

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT filters_on_subject, filters_on_from, filters_on_body, account_id
            FROM account_email_filters WHERE id = %s AND status = 1
        """, (rule_id,))
        rule = cursor.fetchone()
        if not rule:
            print(f"No active rule found with ID: {rule_id}")
            return [], True  # Return empty list and completion flag

        subject_filters = json.loads(rule['filters_on_subject'] or "[]")
        from_filters = json.loads(rule['filters_on_from'] or "[]")
        body_filters = json.loads(rule['filters_on_body'] or "[]")
        account_id = rule['account_id']

        cursor.execute("SELECT smtp_host, smtp_username, smtp_password, smtp_port FROM accounts WHERE id = %s", (account_id,))
        account = cursor.fetchone()
        if not account:
            print(f"No email account found with ID: {account_id}")
            return [], True

        mail = imaplib.IMAP4_SSL(account['smtp_host'], int(account['smtp_port']))
        mail.login(account['smtp_username'], account['smtp_password'])
        print("IMAP Login successful")

        mail.select("inbox")
        search_criteria = []
        if since_date:
            since_formatted = datetime.strptime(str(since_date), '%Y-%m-%d').strftime('%d-%b-%Y')
            search_criteria.append(f"SINCE {since_formatted}")

        matched_emails = []
        has_more_emails = False
        if from_filters:
            for from_filter in from_filters:
                criteria = search_criteria + [f'FROM "{from_filter}"']
                status, messages = mail.search(None, *criteria)
                if status == 'OK':
                    email_ids = messages[0].split()
                    if len(email_ids) > batch_size:
                        has_more_emails = True
                    batch_ids = email_ids[:batch_size]
                    matched_emails.extend(process_emails(mail, batch_ids, subject_filters, body_filters, rule_id, account_id))
        else:
            status, messages = mail.search(None, *search_criteria)
            if status == 'OK':
                email_ids = messages[0].split()
                if len(email_ids) > batch_size:
                    has_more_emails = True
                batch_ids = email_ids[:batch_size]
                matched_emails.extend(process_emails(mail, batch_ids, subject_filters, body_filters, rule_id, account_id))


        mail.logout()
        cursor.close()
        return matched_emails, not has_more_emails  # Return emails and whether this is the final batch

    except Exception as e:
        print("Error:", e)
        return [], True  # On error, return empty list and mark as complete to avoid infinite loops
    finally:
        conn.close()

def process_email_fetch_jobs():
    auto_create_email_fetch_queue()
    conn = connect_to_sql()
    if not conn:
        print("Database connection failed.")
        return
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM email_fetch_queue WHERE status = 'pending' OR status = 'in_progress'")
    jobs = cursor.fetchall()
    if not jobs:
        print("No pending or in-progress jobs found.")
        return

    for job in jobs:
        try:
            since_date = job['last_fetched_date'] or job['since_date']
            if isinstance(since_date, str):
                since_date = datetime.strptime(since_date, "%Y-%m-%d").date()
            elif isinstance(since_date, datetime):
                since_date = since_date.date()

            batch_size = job['batch_size']

            emails, is_final_batch = fetch_emails_by_rule(job['rule_id'], since_date, batch_size)
            filtered_emails = []
            for email in emails:
                email_date = datetime.strptime(email["imap_created_date"], "%Y-%m-%d %H:%M:%S").date()
                if email_date > since_date:
                    filtered_emails.append(email)

            if filtered_emails:
                store_emails_in_db(filtered_emails)
                last_email = filtered_emails[-1]
                cursor.execute("""
                    UPDATE email_fetch_queue
                    SET fetched_count = fetched_count + %s,
                        last_fetched_date = %s,
                        last_fetched_id = %s,
                        status = "in_progress"
                    WHERE id = %s
                """, (len(filtered_emails), last_email["imap_created_date"], last_email["imap_message_id"], job['id']))
                conn.commit()

                print(f"Batch processed successfully for job ID {job['id']}.")
            else:
                print(f"No new emails found beyond the last fetched date for job ID {job['id']}.")

        except Exception as e:
            print(f"Error processing job ID {job['id']}: {e}")
            cursor.execute("UPDATE email_fetch_queue SET status = 'failed' WHERE id = %s", (job['id'],))
            conn.commit()

    cursor.close()
    conn.close()

def process_emails(mail, email_ids, subject_filters, body_filters, rule_id, account_id):
    emails = []
    for email_id in email_ids:
        try:
            _, msg_data = mail.fetch(email_id, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])

            # Handle potential None or missing Subject
            subject = "No Subject"
            if msg["Subject"]:
                decoded_subject = decode_header(msg["Subject"])[0]
                subject = decoded_subject[0]
                if isinstance(subject, bytes):
                    encoding = decoded_subject[1] or "utf-8"
                    try:
                        subject = subject.decode(encoding)
                    except UnicodeDecodeError:
                        subject = subject.decode(encoding, errors='replace')

            from_ = msg.get("From", "No Sender")
            headers = str(msg)
            body = get_full_body_content(msg)
            date = msg.get("Date")

            if (not subject_filters or any(f.lower() in subject.lower() for f in subject_filters)) and \
               (not body_filters or any(f.lower() in str(body).lower() for f in body_filters)):
                
                try:
                    imap_created_date = convert_to_sql_date(date) if date else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    print(f"Date conversion error for email ID {email_id}: {str(e)}")
                    imap_created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                emails.append({
                    "imap_message_id": msg.get("Message-ID", f"NO_ID_{email_id}"),
                    "imap_from": from_,
                    "imap_subject": subject,
                    "imap_body": body,
                    "imap_headers": headers,
                    "imap_created_date": imap_created_date,
                    "account_id": account_id,
                    "account_email_filters_id": rule_id,
                })
        except Exception as e:
            print(f"Error processing email ID {email_id}: {str(e)}")
            continue
    return emails

def store_emails_in_db(emails):
    conn = connect_to_sql()
    if not conn:
        print("Database connection failed.")
        return

    try:
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO email (account_id, account_email_filters_id, imap_message_id, imap_from, imap_subject, imap_body, imap_created_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        for email_data in emails:
            cursor.execute(insert_query, (
                email_data["account_id"],
                email_data["account_email_filters_id"],
                email_data["imap_message_id"],
                email_data["imap_from"],
                email_data["imap_subject"],
                str(email_data["imap_body"]),
                email_data['imap_created_date']
            ))
        
        conn.commit()
        print(f"Inserted {len(emails)} emails into the database.")

    except Exception as e:
        print("Error while inserting emails:", e)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    process_email_fetch_jobs()
