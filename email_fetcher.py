import imaplib
import email
from email.header import decode_header
import json
from datetime import datetime
from helper import connect_to_sql, get_full_body_content, convert_to_sql_date


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
    conn = connect_to_sql()
    if not conn:
        print("Database connection failed.")
        return
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM email_fetch_queue WHERE status = 'pending' OR status = 'in_progress' LIMIT 1")
    job = cursor.fetchone()
    if not job:
        print("No pending or in-progress jobs found.")
        return

    try:
        # Update job status to in_progress if it's pending
        if job['status'] == 'pending':
            cursor.execute("UPDATE email_fetch_queue SET status = 'in_progress' WHERE id = %s", (job['id'],))
            conn.commit()

        # Use `last_fetched_date` if available, otherwise use `since_date`
        since_date = job['last_fetched_date'] or job['since_date']
        
        # Ensure `since_date` is compatible with IMAP's SINCE format (date only)
        if isinstance(since_date, datetime):
            since_date = since_date.date()  # Extract just the date part if it's a datetime

        batch_size = job['batch_size']
        # Fetch one batch of emails and check if there are more
        emails, is_final_batch = fetch_emails_by_rule(job['rule_id'], since_date, batch_size)
        if emails:
            store_emails_in_db(emails)
            
            # Update progress for the batch
            last_email = emails[-1]
            cursor.execute("""
                UPDATE email_fetch_queue
                SET fetched_count = fetched_count + %s,
                    last_fetched_date = %s,
                    last_fetched_id = %s
                WHERE id = %s
            """, (len(emails), last_email["imap_created_date"], last_email["imap_message_id"], job['id']))
            conn.commit()

        # Only mark as completed if this was the final batch
        if is_final_batch:
            cursor.execute("UPDATE email_fetch_queue SET status = 'completed' WHERE id = %s", (job['id'],))
            conn.commit()
            print("Job completed successfully")
        else:
            print("Batch processed successfully, more emails remaining")

    except Exception as e:
        print("Error processing job:", e)
        cursor.execute("UPDATE email_fetch_queue SET status = 'failed' WHERE id = %s", (job['id'],))
        conn.commit()
    finally:
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
