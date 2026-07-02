import os
from mcp.server.fastmcp import FastMCP
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

mcp = FastMCP("GmailMCPServer")

def get_gmail_service():
    if not os.path.exists("token.json"):
        raise Exception("token.json not found. Run google_auth.py first.")
    creds = Credentials.from_authorized_user_file("token.json")
    return build('gmail', 'v1', credentials=creds)

@mcp.tool()
def get_recent_emails(days_ago: int = 7, limit: int = 5) -> str:
    """Fetch emails from the Primary inbox from the last N days."""
    service = get_gmail_service()
    
    # Query for primary category and newer than X days
    query = f"category:primary newer_than:{days_ago}d"
    results = service.users().messages().list(userId='me', q=query, maxResults=limit).execute()
    messages = results.get('messages', [])
    
    if not messages:
        return "No recent emails found."
        
    email_data = []
    for msg in messages:
        msg_detail = service.users().messages().get(userId='me', id=msg['id'], format='metadata').execute()
        headers = msg_detail.get('payload', {}).get('headers', [])
        
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "No Subject")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "Unknown")
        
        # Grab the snippet, but slice it to max 250 characters!
        raw_snippet = msg_detail.get('snippet', '')
        snippet = raw_snippet[:250] + "..." if len(raw_snippet) > 250 else raw_snippet
        
        email_data.append({
            "message_id": msg['id'],
            "subject": subject,
            "sender": sender,
            "snippet": snippet
        })
        
    return str(email_data)
        
    return str(email_data)

if __name__ == "__main__":
    mcp.run()
