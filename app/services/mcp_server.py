import re
import json
import base64
import email.utils
from pathlib import Path
from datetime import date
from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
from googleapiclient.discovery import build
from .google_auth import get_credentials
from app.logger import setup_logging, get_logger

setup_logging()
logger = get_logger("services.mcp_server")

mcp = FastMCP("GmailMCPServer")

PROCESSED_EMAILS_FILE = Path("processed_emails.json")

def format_email_date(raw_date: str) -> str:
    """Parses RFC 2822 email date header into YYYY-MM-DD format."""
    if not raw_date:
        return date.today().isoformat()
    try:
        return email.utils.parsedate_to_datetime(raw_date).date().isoformat()
    except Exception:
        return date.today().isoformat()

def load_processed_ids() -> set:
    """Loads processed IDs, returning an empty set if the file doesn't exist."""
    if not PROCESSED_EMAILS_FILE.exists():
        return set()
    try:
        return set(json.loads(PROCESSED_EMAILS_FILE.read_text(encoding="utf-8")))
    except Exception:
        return set()

def save_processed_ids(msg_ids: list[str]):
    """Persists a collection of processed email IDs to processed_emails.json."""
    if not msg_ids:
        return
    processed = load_processed_ids()
    processed.update(msg_ids)
    PROCESSED_EMAILS_FILE.write_text(json.dumps(list(processed)), encoding="utf-8")
    logger.info("Saved %d message ID(s) to processed cache.", len(msg_ids))

def save_processed_id(msg_id: str):
    """Backwards-compatible helper to save a single processed message ID."""
    save_processed_ids([msg_id])

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
    creds = get_credentials(interactive=False)
    return build('gmail', 'v1', credentials=creds)

@mcp.tool()
def get_recent_emails(days_ago: int = 7, limit: int = 10) -> str:
    """Fetch unprocessed emails from the Primary inbox from the last N days, paginating until limit is reached."""
    # Enforce safe bounds (1-15) to prevent overloading GenAI structured output
    limit = max(1, min(limit, 15))
    days_ago = max(1, min(days_ago, 60))
    logger.info("get_recent_emails tool invoked (days_ago=%d, target_limit=%d).", days_ago, limit)
    service = get_gmail_service()
    
    # Query for primary category and newer than X days
    query = f"category:primary newer_than:{days_ago}d"
    processed_ids = load_processed_ids()
    
    unprocessed_msg_ids = []
    page_token = None
    max_pages = 5  # Scan up to 5 pages (up to 250 stubs) to find new emails
    
    for page in range(max_pages):
        list_kwargs = {"userId": "me", "q": query, "maxResults": 50}
        if page_token:
            list_kwargs["pageToken"] = page_token
            
        results = service.users().messages().list(**list_kwargs).execute()
        messages = results.get("messages", [])
        logger.info("Page %d: Gmail list query returned %d message stubs.", page + 1, len(messages))
        
        if not messages:
            break
            
        for msg in messages:
            msg_id = msg["id"]
            if msg_id not in processed_ids and msg_id not in unprocessed_msg_ids:
                unprocessed_msg_ids.append(msg_id)
                if len(unprocessed_msg_ids) >= limit:
                    break
                    
        if len(unprocessed_msg_ids) >= limit:
            logger.info("Collected target of %d unprocessed email ID(s).", len(unprocessed_msg_ids))
            break
            
        page_token = results.get("nextPageToken")
        if not page_token:
            logger.info("No more pages available in Gmail list query.")
            break

    if not unprocessed_msg_ids:
        logger.info("No unprocessed emails found in the last %d days.", days_ago)
        return "No recent emails found."

    unprocessed_msg_ids.reverse()  # Process oldest to newest within the batch
    email_data = []
    
    for msg_id in unprocessed_msg_ids:
        logger.info("Fetching full details for email ID: %s", msg_id)
        # Request the 'full' format so we get the body payload
        msg_detail = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
        payload = msg_detail.get('payload', {})
        headers = payload.get('headers', [])
        
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown")
        raw_date = next((h['value'] for h in headers if h['name'] == 'Date'), "")
        formatted_date = format_email_date(raw_date)
        
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
            "date": formatted_date,
            "snippet": snippet
        })
        
    logger.info("Processed and returning %d new email(s).", len(email_data))
    return str(email_data)

if __name__ == "__main__":
    mcp.run()
