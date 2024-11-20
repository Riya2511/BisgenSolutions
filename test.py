import imaplib
import email
from helper import connect_to_sql
import json
import re

def fetch_test_email():
    # Connect to SQL database to get IMAP server details
    conn = connect_to_sql()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch IMAP server configuration
    cursor.execute("SELECT smtp_host, smtp_username, smtp_password, smtp_encryption, smtp_port FROM accounts where id = 2 LIMIT 1")
    server_config = cursor.fetchone()
    
    if not server_config:
        raise ValueError("No IMAP server configuration found")
    
    # IMAP connection parameters
    imap_host = server_config['smtp_host']
    username = server_config['smtp_username']
    password = server_config['smtp_password']
    port = int(server_config['smtp_port'])
    
    # Connect to IMAP server
    try:
        # Use SSL/TLS connection
        if server_config['smtp_encryption'].lower() in ['ssl', 'tls', 'ssl/tls']:
            imap_server = imaplib.IMAP4_SSL(imap_host, port)
        else:
            imap_server = imaplib.IMAP4(imap_host, port)
        
        # Login to the server
        imap_server.login(username, password)
        
        # Select the inbox
        imap_server.select('INBOX')
        
        # Search for emails 
        _, message_numbers = imap_server.search(None, 'ALL')
        
        # Find first email with 'name' and 'email'
        found_emails = []
        for email_number in message_numbers[0].split():
            # Fetch email content
            _, msg_data = imap_server.fetch(email_number, '(RFC822)')
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # Check if email contains 'name' and 'email' in subject or body
            is_name_email_email = False
                        
            # Check email body (case-insensitive)
            if not is_name_email_email:
                body_text = ''
                if email_message.is_multipart():
                    for part in email_message.walk():
                        if part.get_content_type() in ['text/plain', 'text/html']:
                            try:
                                body_text += part.get_payload(decode=True).decode()
                            except:
                                pass
                else:
                    try:
                        body_text = email_message.get_payload(decode=True).decode()
                    except:
                        body_text = ''
                
                # Check for 'name' and 'email' in body
                if re.search(r'name', body_text, re.IGNORECASE) and re.search(r'email', body_text, re.IGNORECASE):
                    is_name_email_email = True
            
            # If contains 'name' and 'email', save details
            if is_name_email_email:
                email_details = {
                    'subject': email_message['Subject'] or 'No Subject',
                    'from': email_message['From'] or 'Unknown',
                    'to': email_message['To'] or 'Unknown',
                    'date': email_message['Date'] or 'Unknown',
                    'body': body_text if 'body_text' in locals() else ''
                }
                found_emails.append(email_details)
                
                # Limit to first 5 name and email emails
                if len(found_emails) >= 50:
                    break
        
        # Save to test file if emails found
        if found_emails:
            with open('name_email_emails.json', 'w') as f:
                json.dump(found_emails, f, indent=4)
            
            print(f"{len(found_emails)} name and email email(s) fetched and saved to name_email_emails.json")
            return found_emails
        else:
            print("No emails found with 'name' and 'email'")
            return None
        
        # Close the connection
        imap_server.close()
        imap_server.logout()
    
    except Exception as e:
        print(f"Error fetching email: {e}")
        return None

# Run the function
if __name__ == "__main__":
    fetch_test_email()