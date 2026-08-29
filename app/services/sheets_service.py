import os
from datetime import datetime
from googleapiclient.discovery import build
from app.services.google_auth import get_credentials
from dotenv import load_dotenv

load_dotenv()

SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
RANGE_NAME = "Sheet1!A:G" # 7 columns (Company, Title, Location, Status, Date Applied, Last Updated, Summary)

def is_valid_date(val: str) -> bool:
    """Helper to verify if a cell string is in valid YYYY-MM-DD date format."""
    if not val or not isinstance(val, str):
        return False
    trimmed = val.strip()
    if len(trimmed) != 10:
        return False
    try:
        datetime.strptime(trimmed, "%Y-%m-%d")
        return True
    except Exception:
        return False

def upsert_to_sheet(rows: list[list[str]]):
    """Updates existing rows if Company+Title match, otherwise appends."""
    creds = get_credentials(interactive=False)
    service = build('sheets', 'v4', credentials=creds)
    
    # 1. READ existing data
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    existing_rows = result.get('values', [])
    
    rows_to_append = []
    
    # 2. MATCH & UPDATE
    for new_row in rows:
        new_company_raw = new_row[0] if len(new_row) > 0 and new_row[0] else ""
        new_title_raw = new_row[1] if len(new_row) > 1 and new_row[1] else ""
        new_location = new_row[2] if len(new_row) > 2 and new_row[2] else ""
        new_status_raw = new_row[3] if len(new_row) > 3 and new_row[3] else ""
        new_date = new_row[4] if len(new_row) > 4 and new_row[4] else ""
        new_summary = new_row[5] if len(new_row) > 5 and new_row[5] else ""

        new_company = new_company_raw.strip().lower()
        new_title = new_title_raw.strip().lower()
        new_status = new_status_raw.strip().lower()
        
        match_found = False
        
        for i, existing_row in enumerate(existing_rows):
            if len(existing_row) < 2:
                continue # Skip empty or malformed rows
            
            existing_company = existing_row[0].strip().lower() if len(existing_row) > 0 and existing_row[0] else ""
            existing_title = existing_row[1].strip().lower() if len(existing_row) > 1 and existing_row[1] else ""
            existing_location = existing_row[2] if len(existing_row) > 2 else ""
            existing_status = existing_row[3].strip().lower() if len(existing_row) > 3 and existing_row[3] else ""
            existing_date_applied = existing_row[4] if len(existing_row) > 4 else ""
            existing_last_updated = existing_row[5] if len(existing_row) > 5 else ""
            existing_summary = existing_row[6] if len(existing_row) > 6 else ""
            
            if new_company == existing_company and new_title == existing_title:
                match_found = True
                row_number = i + 1 # Google Sheets is 1-indexed
                
                if new_status == existing_status:
                    print(f"Skipping row {row_number} for {new_company_raw}. Status is already '{existing_status}'.")
                else:
                    print(f"Updating row {row_number} for {new_company_raw}. Status: '{existing_status}' -> '{new_status}'")
                    
                    # Preserve existing Date Applied if valid, otherwise initialize with new_date
                    date_applied = existing_date_applied if is_valid_date(existing_date_applied) else new_date
                    last_updated = new_date if new_date else (existing_last_updated if is_valid_date(existing_last_updated) else date_applied)
                    location = new_location if new_location else existing_location
                    summary = new_summary if new_summary else existing_summary
                    
                    updated_row = [
                        existing_row[0] if len(existing_row) > 0 else new_company_raw,
                        existing_row[1] if len(existing_row) > 1 else new_title_raw,
                        location,
                        new_status_raw,
                        date_applied,
                        last_updated,
                        summary
                    ]
                    
                    service.spreadsheets().values().update(
                        spreadsheetId=SPREADSHEET_ID,
                        range=f"Sheet1!A{row_number}:G{row_number}",
                        valueInputOption="USER_ENTERED",
                        body={"values": [updated_row]}
                    ).execute()
                break # Stop searching, we handled the match
                
        # 3. APPEND if no match
        if not match_found:
            row_to_append = [
                new_company_raw,
                new_title_raw,
                new_location,
                new_status_raw,
                new_date,
                new_date,
                new_summary
            ]
            rows_to_append.append(row_to_append)
            
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
            ["Test Company", "Test Role", "Test Location", "applied", "2026-08-29", "This is a test summary from the script!"]
        ]
        
        print("Attempting to upsert test row to Google Sheets...")
        try:
            upsert_to_sheet(test_rows)
            print("Success! Row upserted.")
        except Exception as e:
            print(f"Failed to upsert to sheet: {e}")
