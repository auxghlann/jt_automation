import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

load_dotenv()

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
RANGE_NAME = "Sheet1!A:E" # Assumes 5 columns (Company, Title, Location, Status, Summary)

def append_to_sheet(rows: list[list[str]]):
    """Appends a list of rows to the Google Sheet."""
    if not os.path.exists("token.json"):
        raise Exception("token.json not found.")
        
    creds = Credentials.from_authorized_user_file("token.json")
    service = build('sheets', 'v4', credentials=creds)
    
    body = {"values": rows}
    
    result = service.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range=RANGE_NAME,
        valueInputOption="USER_ENTERED", # This ensures text is formatted nicely (dates, etc)
        body=body
    ).execute()
    
    return result

if __name__ == "__main__":
    print(f"Loaded SPREADSHEET_ID: {SPREADSHEET_ID}")
    
    if not SPREADSHEET_ID:
        print("Error: SPREADSHEET_ID is missing or not loaded from .env properly!")
    else:
        # Mock data to test the sheet
        test_rows = [
            ["Test Company", "Test Role", "Test Location", "applied", "This is a test summary from the script!"]
        ]
        
        print("Attempting to append test row to Google Sheets...")
        try:
            response = append_to_sheet(test_rows)
            print("Success! Row appended.")
            print(f"Updated Range: {response.get('updates', {}).get('updatedRange')}")
        except Exception as e:
            print(f"Failed to append to sheet: {e}")
