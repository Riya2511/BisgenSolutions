import mysql.connector
from config import SQL_CONFIG
from datetime import datetime

# Connect to SQL database
def connect_to_sql():
    try:
        conn = mysql.connector.connect(**SQL_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print("Error connecting to database:", err)
        return None

# Helper to get full email body
def get_full_body_content(msg):
    plain_text, html_content = None, None
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            charset = part.get_content_charset() or "utf-8"
            if content_type == "text/plain":
                plain_text = part.get_payload(decode=True).decode(charset)
            elif content_type == "text/html":
                html_content = part.get_payload(decode=True).decode(charset)
    else:
        content_type = msg.get_content_type()
        charset = msg.get_content_charset() or "utf-8"
        if content_type == "text/plain":
            plain_text = msg.get_payload(decode=True).decode(charset)
        elif content_type == "text/html":
            html_content = msg.get_payload(decode=True).decode(charset)
    return {"plain_text": plain_text, "html_content": html_content}

# Convert date to SQL format
def convert_to_sql_date(date_str):
    try:
        # First try the original format
        try:
            parsed_date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z (%Z)")
            return parsed_date.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
        
        # Try without timezone name in parentheses
        try:
            # Remove timezone name in parentheses if present
            date_str = date_str.split('(')[0].strip()
            parsed_date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
            return parsed_date.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
        
        # Try without timezone offset
        try:
            date_str = ' '.join(date_str.split()[:-1])  # Remove last part (timezone)
            parsed_date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S")
            return parsed_date.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
            
        # If all attempts fail, raise an error
        raise ValueError(f"Unable to parse date string: {date_str}")
        
    except Exception as e:
        print(f"Error converting date '{date_str}': {str(e)}")
        # Return current timestamp as fallback
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
