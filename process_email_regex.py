import re
from typing import List, Dict, Tuple
from config import EMAIL_PROCESS_BATCH_SIZE
from helper import connect_to_sql
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extract_number(text):
    if not text:
        return None
    text = str(text).lower().strip()
    match = re.match(r'^(\d+(?:\.\d+)?)', text)
    if match:
        number = float(match.group(1))
        return number
    return None

def parsing_name(text):
    text = re.findall(r'>[^<]+<|>([^<]+)$', text)
    cleaned_text = ' '.join([t.strip() for t in text if t.strip()])
    cleaned_text = cleaned_text.replace('\\r', '').replace('\\n', '').replace('\\', '').replace('&nbsp;', ' ').strip()
    return cleaned_text[1:].strip() if cleaned_text.startswith(',') else cleaned_text

def parsing_email(text):
    return text.replace('mailto:', '').replace('\r', '').replace('\\', '').replace('\n', '').replace('&nbsp;', ' ').strip()

def parsing_member_since(text):
    return text.replace('Member Since:', '').replace('\\r', '').replace('\\n', '').replace('\\', '').replace('&nbsp;', ' ').strip()

def parse_table_data(text):
    pattern = r'<td[^>]*>([^<]+)</td>[^<]*(?!.*<td)'
    match = re.search(pattern, text)
    if match:
        return match.group(1).strip()
    return None

def get_contact_details(text):
    print(text)
    pass

def parse_location_instant(text):
    # Extract product name
    product_pattern = r'font-weight: bold;padding-left:26px">([^<]+)</span>'
    product_match = re.search(product_pattern, text)
    product_name = product_match.group(1) if product_match else None

    # Extract location - match any city and state
    location_pattern = r'&nbsp;([^,]+),&ensp;([^<]+)</td>'
    location_match = re.search(location_pattern, text)
    if location_match:
        city = location_match.group(1)
        state = location_match.group(2)
        location = f"{city}, {state}"
    else:
        location = None

    if product_name and location:
        return product_name, location.strip().replace('&ensp;', ' ')
    return None, None

def fetch_emails_to_process(batch_size: int) -> List[Dict]:
    """
    Fetch emails that need processing, with regex patterns fetched separately
    """
    conn = connect_to_sql()
    if not conn:
        return []
    
    cursor = conn.cursor(dictionary=True)
    
    # First get the emails
    email_query = """
        SELECT DISTINCT
            e.id, 
            e.imap_body,
            e.account_id
        FROM 
            email e
        JOIN 
            email_parsing_view v ON e.account_email_filters_id = v.rule_id
        WHERE 
            e.status = 'TO_BE_PROCESSED'
        LIMIT %s    
    """
    cursor.execute(email_query, (batch_size,))
    emails = cursor.fetchall()
    
    # Then get regex patterns and column mappings for each email
    for email in emails:
        pattern_query = """
            SELECT email_regex, rule_id, email_column_mapped
            FROM email_parsing_view v
            WHERE v.rule_id = (
                SELECT account_email_filters_id 
                FROM email 
                WHERE id = %s
            )
        """
        cursor.execute(pattern_query, (email['id'],))
        patterns = cursor.fetchall()
        
        email['regex_patterns'] = [p['email_regex'] for p in patterns]
        email['rule_ids'] = [p['rule_id'] for p in patterns]
        email['column_mappings'] = [p['email_column_mapped'] for p in patterns]
    
    cursor.close()
    conn.close()
    
    return emails

def process_email_regex(email_id: int, imap_body: str, regex_patterns: List[str], column_mappings: List[str]) -> List[List[Tuple]]:
    all_results = []
    
    for pattern, column_mapping in zip(regex_patterns, column_mappings):
        try:
            compiled_pattern = re.compile(pattern)
            
            if 'instant' in column_mapping.lower():
                # Handle instant patterns - find all matches
                matches = list(compiled_pattern.finditer(imap_body))
                temp_results = []
                if len(matches) == 0:
                    temp_results.append((pattern, column_mapping, None, 'PARSING_ERROR'))

                for match in matches:
                    try:
                        # Extract the first capturing group if it exists, otherwise use whole match
                        regex_output = match.group(1).strip() if match.groups() else match.group(0).strip()
                        parsing_status = 'PARSING_DONE' if regex_output else 'PARSING_ERROR'
                        temp_results.append((pattern, column_mapping, regex_output, parsing_status))
                        
                        logger.debug(f"Instant Pattern: {pattern}, Column: {column_mapping}, "
                                   f"Output: {regex_output}, Status: {parsing_status}")
                    
                    except Exception as e:
                        logger.error(f"Error processing instant match for pattern {pattern}: {str(e)}")
                        temp_results.append((pattern, column_mapping, None, 'PARSING_ERROR'))

                # Initialize all_results if empty
                if not all_results:
                    all_results = [[result] for result in temp_results]
                else:
                    # Ensure all_results and temp_results have the same length
                    while len(all_results) < len(temp_results):
                        all_results.append(all_results[-1][:])  # Copy the last result set
                    
                    # Add new results to existing groups
                    for i, result in enumerate(temp_results):
                        if i < len(all_results):
                            all_results[i].append(result)
            
            else:
                # Handle non-instant patterns - find single match
                match = compiled_pattern.search(imap_body)
                regex_output = match.group(0).strip() if match else None
                parsing_status = 'PARSING_DONE' if regex_output else 'PARSING_ERROR'
                
                result = (pattern, column_mapping, regex_output, parsing_status)
                
                logger.debug(f"Pattern: {pattern}, Column: {column_mapping}, "
                           f"Output: {regex_output}, Status: {parsing_status}")
                
                # If all_results is empty, create new list with single result
                if not all_results:
                    all_results = [[result]]
                else:
                    # Add result to each existing group
                    for group in all_results:
                        group.append(result)
            
        except re.error as e:
            logger.error(f"Invalid regex pattern {pattern}: {str(e)}")
            error_result = (pattern, column_mapping, None, 'PARSING_ERROR')
            
            if not all_results:
                all_results = [[error_result]]
            else:
                for group in all_results:
                    group.append(error_result)
                    
        except Exception as e:
            logger.error(f"Error processing pattern {pattern}: {str(e)}")
            error_result = (pattern, column_mapping, None, 'PARSING_ERROR')
            
            if not all_results:
                all_results = [[error_result]]
            else:
                for group in all_results:
                    group.append(error_result)
    
    return all_results

def update_email_regex_results(email_id: int, regex_results: List[Tuple], account_id: int):
    """
    Update the email and leads tables with results from multiple regex patterns
    """
    conn = connect_to_sql()
    if not conn:
        return
    
    cursor = conn.cursor()    
    try:
        regex_patterns = []
        regex_outputs = []
        lead_updates = {}
        regex_applications = []
        for pattern, column_mapping, output, status in regex_results:
            regex_patterns.append(pattern)
            regex_outputs.append(output if output else '')
            regex_applications.append({
                'regex': pattern,
                'status': status
            })
            if output and column_mapping:
                if 'name_buyer' in column_mapping:
                    lead_updates['name'] = parsing_name(output)
                elif 'buyer_since_instant' in column_mapping:
                    lead_updates['mail_buyer_since'] = output
                elif 'quantity_instant' in column_mapping:
                    lead_updates['mail_quantity'] = output
                    lead_updates['qty'] = extract_number(output)
                elif 'order_value_instant' in column_mapping:
                    lead_updates['mail_order_value'] = output
                elif 'usage_instant' in column_mapping:
                    lead_updates['mail_usage'] = output
                elif 'why_instant' in column_mapping:
                    lead_updates['reasons'] = output
                    lead_updates['mail_why'] = output
                elif 'location_instant' in column_mapping:
                    lead_updates['requirement'], lead_updates['mail_buyer_location'] = parse_location_instant(output)
                    lead_updates['mail_requirement'] = lead_updates['requirement']
                elif 'email_buyer' in column_mapping:
                    lead_updates['email'] = parsing_email(output)
                elif 'quantity_buyer' in column_mapping:
                    lead_updates['mail_quantity'] = parse_table_data(output)
                    lead_updates['qty'] = extract_number(parse_table_data(output))
                elif 'requirement_buyer' in column_mapping:
                    lead_updates['mail_requirement'] = parse_table_data(output)
                elif 'order_value_buyer' in column_mapping:
                    lead_updates['mail_order_value'] = parse_table_data(output)
                elif 'usage_buyer' in column_mapping:
                    lead_updates['mail_usage'] = parse_table_data(output)
                elif 'buyer_since_buyer' in column_mapping:
                    lead_updates['mail_buyer_since'] = parsing_member_since(output)
                elif 'location_buyer' in column_mapping:
                    lead_updates['mail_buyer_location'] = parsing_name(output)
                elif 'contact_instant' in column_mapping:
                    get_contact_details(output)
                else:
                    lead_updates[column_mapping] = output

        print(lead_updates)

        lead_query = "SELECT id FROM leads WHERE email = %s"
        cursor.execute(lead_query, (lead_updates['email'],))
        lead_result = cursor.fetchone()

        overall_status = 'PARSING_DONE'
        if not any(output for _, _, output, _ in regex_results):
            overall_status = 'PARSING_ERROR'

        # Update email table
        email_update_query = """
            UPDATE email 
            SET 
                status = 'PROCESSED',
                mail_regex_applied = %s,
                mail_regex_output = %s,
                mail_parsing_status = %s
            WHERE 
                id = %s
        """
        cursor.execute(
            email_update_query, 
            (
                (str(regex_applications)),
                '\n'.join(regex_outputs),
                overall_status,
                email_id
            )
        )
        
        # Update or insert leads record
        if lead_updates:
            if lead_result:
                lead_id = lead_result[0]
                update_parts = []
                update_values = []
                
                for column, value in lead_updates.items():
                    update_parts.append(f"{column} = %s")
                    update_values.append(value)
                
                leads_update_query = f"""
                    UPDATE leads 
                    SET {', '.join(update_parts)}
                    WHERE id = %s
                """
                update_values.append(lead_id)
                cursor.execute(leads_update_query, tuple(update_values))
            else:
                # Insert new lead
                lead_updates['email_id'] = email_id
                lead_updates['account_id'] = account_id
                lead_updates['status'] = 1
                
                columns = ', '.join(lead_updates.keys())
                placeholders = ', '.join(['%s'] * len(lead_updates))
                leads_insert_query = f"""
                    INSERT INTO leads ({columns})
                    VALUES ({placeholders})
                """
                cursor.execute(leads_insert_query, tuple(lead_updates.values()))
        
        conn.commit()
        logger.info(f"Successfully updated email {email_id} and its lead record")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error updating results for email {email_id}: {str(e)}")
        # Update email status to FAIL_TO_PROCESS in case of error
        cursor.execute(
            "UPDATE email SET status = 'FAIL_TO_PROCESS' WHERE id = %s",
            (email_id,)
        )
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def main():
    batch_size = EMAIL_PROCESS_BATCH_SIZE
    logger.info(f"Starting email processing with batch size {batch_size}")
    
    # while True:
    emails = fetch_emails_to_process(batch_size)
    
    if not emails:
        logger.info("No more emails to process.")
        # break

    for email in emails:
        email_id = email['id']
        imap_body = email['imap_body']
        regex_patterns = email['regex_patterns']
        column_mappings = email['column_mappings']
        account_id = email['account_id']
        
        logger.info(f"Processing email ID {email_id}")
        
        # Apply all regex patterns to the email body
        regex_results = process_email_regex(email_id, imap_body, regex_patterns, column_mappings)
        print(regex_results)
        # Update the database with all results
        # for regex_result in regex_results:
        #     update_email_regex_results(email_id, regex_result, account_id)
        
        # Log processing summary
        for regex_result in regex_results:
            success_count = sum(1 for _, _, output, _ in regex_result if output is not None)
            total_patterns = len(regex_patterns)
            logger.info(f"Processed email ID {email_id}: {success_count}/{total_patterns} patterns successful")

        logger.info(f"Batch of {len(emails)} emails processed.")

if __name__ == "__main__":
    main()