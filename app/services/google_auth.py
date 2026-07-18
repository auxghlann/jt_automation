import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets"
]


def get_mcp_token():
    """Authenticates the user and returns the OAuth 2.0 Access Token string."""
    creds = None
    
    # Load previously saved token if it exists
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        
    # If no valid credentials, run the login flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Token refresh failed: {e}. Re-authenticating...")
                if os.path.exists("token.json"):
                    os.remove("token.json")
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save credentials for future use
        with open("token.json", "w") as token_file:
            token_file.write(creds.to_json())
            
    # Return the raw token string
    return creds.token

if __name__ == "__main__":
    print("Starting Google Authentication flow...")
    get_mcp_token()
    print("Authentication successful! token.json has been generated.")
