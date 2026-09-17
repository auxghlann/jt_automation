import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from app.errors.exceptions import AuthRequiredError
from app.logger import get_logger

logger = get_logger("services.auth")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/spreadsheets"
]


def get_credentials(interactive: bool = False):
    """Authenticates the user and returns the Google OAuth Credentials object."""
    creds = None
    
    # Load previously saved token if it exists
    if os.path.exists("token.json"):
        logger.debug("Loading existing credentials from token.json")
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        
    # If no valid credentials, run the login flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("Attempting to refresh expired Google OAuth token.")
                creds.refresh(Request())
                logger.info("OAuth token successfully refreshed.")
            except Exception as e:
                logger.warning("Token refresh failed: %s. Re-authenticating...", e)
                if os.path.exists("token.json"):
                    os.remove("token.json")
                if not interactive:
                    logger.warning("Auth token expired and interactive mode is disabled.")
                    raise AuthRequiredError("Google authentication token is expired. Please run auth.")
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)
        else:
            if not interactive:
                logger.warning("No valid credentials found and interactive mode is disabled.")
                raise AuthRequiredError("Google authentication is required. Please run auth.")
            logger.info("Launching browser for interactive Google authentication.")
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
            
        # Save credentials for future use
        with open("token.json", "w") as token_file:
            token_file.write(creds.to_json())
        logger.info("Saved updated credentials to token.json.")
            
    # Return the Credentials object
    return creds

