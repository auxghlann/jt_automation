import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

load_dotenv()

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
RANGE_NAME = "Sheet1!A:E" # Assumes 5 columns (Company, Title, Location, Status, Summary)

def upsert_to_sheet(rows: list[list[str]]):
    """Updates existing rows if Company+Title match, otherwise appends."""
    if not os.path.exists("token.json"):
        raise Exception("token.json not found.")
        
    creds = Credentials.from_authorized_user_file("token.json")
    service = build('sheets', 'v4', credentials=creds)
    
    # 1. READ existing data
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    existing_rows = result.get('values', [])
    
    rows_to_append = []
    
    # 2. MATCH & UPDATE
    for new_row in rows:
        new_company = new_row[0].strip().lower() if len(new_row) > 0 and new_row[0] else ""
        new_title = new_row[1].strip().lower() if len(new_row) > 1 and new_row[1] else ""
        
        match_found = False
        
        for i, existing_row in enumerate(existing_rows):
            if len(existing_row) < 2: continue # Skip empty or malformed rows
            
            existing_company = existing_row[0].strip().lower()
            existing_title = existing_row[1].strip().lower()
            
            if new_company == existing_company and new_title == existing_title:
                match_found = True
                row_number = i + 1 # Google Sheets is 1-indexed
                
                print(f"Updating existing row {row_number} for {new_company} - {new_title}")
                service.spreadsheets().values().update(
                    spreadsheetId=SPREADSHEET_ID,
                    range=f"Sheet1!A{row_number}:E{row_number}",
                    valueInputOption="USER_ENTERED",
                    body={"values": [new_row]}
                ).execute()
                break # Stop searching, we updated it
                
        # 3. APPEND if no match
        if not match_found:
            rows_to_append.append(new_row)
            
    if rows_to_append:
        print(f"Appending {len(rows_to_append)} new rows...")
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME,
            valueInputOption="USER_ENTERED",
            body={"values": rows_to_append}
        ).execute()

if __name__ == "__main__":
    print(f"Loaded SPREADSHEET_ID: {SPREADSHEET_ID}")
    
    if not SPREADSHEET_ID:
        print("Error: SPREADSHEET_ID is missing or not loaded from .env properly!")
    else:
        # Mock data to test the sheet
        test_rows = [
            ["Test Company", "Test Role", "Test Location", "applied", "This is a test summary from the script!"]
        ]
        
        print("Attempting to upsert test row to Google Sheets...")
        try:
            upsert_to_sheet(test_rows)
            print("Success! Row upserted.")
        except Exception as e:
            print(f"Failed to upsert to sheet: {e}")
