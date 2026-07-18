import os
import re
import json
import base64
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

mcp = FastMCP("GmailMCPServer")

PROCESSED_EMAILS_FILE = "processed_emails.json"

def load_processed_ids() -> set:
    """Loads processed IDs, automatically creating the file if it doesn't exist."""
    if not os.path.exists(PROCESSED_EMAILS_FILE):
        # Auto-create the file on the first run
        with open(PROCESSED_EMAILS_FILE, "w") as f:
            json.dump([], f)
        return set()
        
    with open(PROCESSED_EMAILS_FILE, "r") as f:
        return set(json.load(f))

def save_processed_id(msg_id: str):
    processed = load_processed_ids()
    processed.add(msg_id)
    with open(PROCESSED_EMAILS_FILE, "w") as f:
        json.dump(list(processed), f)

def get_email_body(payload):
    """Recursively searches for the HTML body, falling back to plain text."""
    body_data = None
    
    def extract_parts(parts):
        nonlocal body_data
        for part in parts:
            if part['mimeType'] == 'text/html':
                body_data = part['body'].get('data', '')
                return True # Found HTML, stop searching!
            elif part['mimeType'] == 'text/plain' and not body_data:
                # Save plain text as a backup, but keep searching for HTML
                body_data = part['body'].get('data', '')
            elif 'parts' in part:
                if extract_parts(part['parts']):
                    return True
        return False
        
    if 'parts' in payload:
        extract_parts(payload['parts'])
    elif payload.get('mimeType') in ['text/html', 'text/plain']:
        body_data = payload['body'].get('data', '')

    if not body_data:
        return ""
        
    # Decode the base64
    decoded_bytes = base64.urlsafe_b64decode(body_data)
    raw_text = decoded_bytes.decode('utf-8', errors='ignore')
    
    if "<html" in raw_text.lower() or "<body" in raw_text.lower() or "<div" in raw_text.lower() or "<span" in raw_text.lower():
        soup = BeautifulSoup(raw_text, "html.parser")
        # Extract text, separating visual blocks with a newline
        clean_text = soup.get_text(separator=' ', strip=True)
        return clean_text
        
    return raw_text

def get_gmail_service():
    if not os.path.exists("token.json"):
        raise Exception("token.json not found. Run google_auth.py first.")
    creds = Credentials.from_authorized_user_file("token.json")
    return build('gmail', 'v1', credentials=creds)

@mcp.tool()
def get_recent_emails(days_ago: int = 2, limit: int = 7) -> str:
    """Fetch emails from the Primary inbox from the last N days."""
    service = get_gmail_service()
    
    # Query for primary category and newer than X days
    query = f"category:primary newer_than:{days_ago}d"
    results = service.users().messages().list(userId='me', q=query, maxResults=limit).execute()
    messages = results.get('messages', [])
    
    if not messages:
        return "No recent emails found."

    messages.reverse()
        
    email_data = []
    processed_ids = load_processed_ids()
    
    for msg in messages:
        msg_id = msg['id']
        
        if msg_id in processed_ids:
            continue
            
        # Request the 'full' format so we get the body payload
        msg_detail = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        payload = msg_detail.get('payload', {})
        headers = payload.get('headers', [])
        
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown")
        
        # Extract the actual body instead of the snippet!
        body_text = get_email_body(payload)
        
        # Strip massive URLs to save tokens
        body_text = re.sub(r'http[s]?://\S+', '[URL_REMOVED]', body_text)
        
        # Strip invisible formatting characters
        body_text = re.sub(r'[\u200b-\u200f\ufeff\u034f\xad]', '', body_text)
        
        # Clean up excessive newlines and whitespace that eat up tokens
        clean_body = " ".join(body_text.split())
        
        # Truncate LinkedIn's "Similar Jobs" sections
        truncation_phrases = [
            "Explore similar jobs recommended for you",
            "View similar jobs you may be interested in"
        ]
        for phrase in truncation_phrases:
            if phrase in clean_body:
                clean_body = clean_body.split(phrase)[0]
                
        # Take the first 800 characters
        if clean_body:
            snippet = clean_body[:800] + "..." if len(clean_body) > 800 else clean_body
        else:
            raw_snippet = msg_detail.get('snippet', '')
            snippet = raw_snippet[:250] + "..."
        
        email_data.append({
            "message_id": msg_id,
            "subject": subject,
            "sender": sender,
            "snippet": snippet
        })
        
        # Mark as processed so we never read it again!
        save_processed_id(msg_id)
        
    return str(email_data)

if __name__ == "__main__":
    mcp.run()
    # import sys
    
    # # If ran with 'run', start the MCP server as normal
    # if len(sys.argv) > 1 and sys.argv[1] == "run":
    #     mcp.run()
    # else:
    #     print("=== COMPARING EMAIL FETCHING METHODS ===\n")
    #     service = get_gmail_service()
    #     query = "category:primary newer_than:7d"
        
    #     # Grab just 1 email for the test
    #     results = service.users().messages().list(userId='me', q=query, maxResults=1).execute()
    #     messages = results.get('messages', [])
        
    #     if not messages:
    #         print("No recent emails found.")
    #     else:
    #         msg_id = messages[0]['id']
            
    #         # --- 1. OLD WAY (Snippet Only) ---
    #         print("--- 1. OLD WAY (Snippet Only) ---")
    #         old_detail = service.users().messages().get(userId='me', id=msg_id, format='metadata').execute()
    #         old_headers = old_detail.get('payload', {}).get('headers', [])
    #         old_subj = next((h['value'] for h in old_headers if h['name'] == 'Subject'), "No Subject")
            
    #         raw_snippet = old_detail.get('snippet', '')
    #         old_snippet = raw_snippet[:250] + "..." if len(raw_snippet) > 250 else raw_snippet
            
    #         print(f"Subject: {old_subj}")
    #         print(f"Snippet length: {len(old_snippet)}")
    #         print(f"Content: {old_snippet}\n")
            
    #         # --- 2. NEW WAY (Body Extraction) ---
    #         print("--- 2. NEW WAY (Body Extraction) ---")
    #         print("Running get_recent_emails()...")
    #         new_result = get_recent_emails(days_ago=7, limit=1)
            
    #         import pprint
    #         # Safe evaluation just to print it beautifully
    #         try:
    #             parsed_result = eval(new_result)
    #             for email in parsed_result:
    #                 print(f"Subject: {email['subject']}")
    #                 print(f"Snippet length: {len(email['snippet'])}")
    #                 print(f"Content: {email['snippet']}")
    #         except Exception as e:
    #             print(new_result)
