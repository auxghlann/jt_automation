import os
from datetime import date
from googleapiclient.discovery import build
from app.services.google_auth import get_credentials
from app.logger import get_logger
from dotenv import load_dotenv

load_dotenv()

logger = get_logger("services.sheets")
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")
RANGE_NAME = "Sheet1!A:G" # 7 columns (Company, Title, Location, Status, Date Applied, Last Updated, Summary)

def is_valid_date(val: str) -> bool:
    """Helper to verify if a cell string is in valid YYYY-MM-DD date format."""
    if not val or not isinstance(val, str):
        return False
    try:
        date.fromisoformat(val.strip())
        return True
    except ValueError:
        return False

def upsert_to_sheet(rows: list[list[str]]):
    """Updates existing rows if Company+Title match, otherwise appends."""
    creds = get_credentials(interactive=False)
    service = build('sheets', 'v4', credentials=creds)
    
    # 1. READ existing data
    result = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
    existing_rows = result.get('values', [])
    logger.info("Retrieved %d existing row(s) from Google Sheet.", len(existing_rows))
    
    # Build in-memory lookup index: (company_lower, title_lower) -> (row_number, existing_row)
    # Using 1-based indexing for Google Sheets ranges
    existing_index = {}
    for i, existing_row in enumerate(existing_rows):
        if len(existing_row) >= 2:
            comp = existing_row[0].strip().lower() if existing_row[0] else ""
            title = existing_row[1].strip().lower() if existing_row[1] else ""
            if comp and title:
                existing_index[(comp, title)] = (i + 1, existing_row)
    
    rows_to_append = []
    batch_update_data = []
    appended = []
    updated = []
    skipped = []
    
    # 2. MATCH & PREPARE UPDATES
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
        
        match = existing_index.get((new_company, new_title))
        
        if match:
            row_number, existing_row = match
            existing_location = existing_row[2] if len(existing_row) > 2 else ""
            existing_status = existing_row[3].strip().lower() if len(existing_row) > 3 and existing_row[3] else ""
            existing_date_applied = existing_row[4] if len(existing_row) > 4 else ""
            existing_last_updated = existing_row[5] if len(existing_row) > 5 else ""
            existing_summary = existing_row[6] if len(existing_row) > 6 else ""
            
            if new_status == existing_status:
                logger.info("Skipping row %d for %s. Status is already '%s'.", row_number, new_company_raw, existing_status)
                skipped.append({
                    "company": existing_row[0] if len(existing_row) > 0 else new_company_raw,
                    "title": existing_row[1] if len(existing_row) > 1 else new_title_raw,
                    "location": existing_location,
                    "status": existing_status,
                    "date": new_date or existing_last_updated,
                    "summary": new_summary or existing_summary
                })
            else:
                logger.info("Updating row %d for %s. Status: '%s' -> '%s'", row_number, new_company_raw, existing_status, new_status)
                
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
                
                batch_update_data.append({
                    "range": f"Sheet1!A{row_number}:G{row_number}",
                    "values": [updated_row]
                })
                updated.append({
                    "company": updated_row[0],
                    "title": updated_row[1],
                    "location": updated_row[2],
                    "old_status": existing_status,
                    "new_status": new_status_raw,
                    "date": last_updated,
                    "summary": summary
                })
        else:
            # APPEND if no match
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
            appended.append({
                "company": new_company_raw,
                "title": new_title_raw,
                "location": new_location,
                "status": new_status_raw,
                "date": new_date,
                "summary": new_summary
            })
            
    # 3. DISPATCH BATCH UPDATE IF ANY MODIFICATIONS
    if batch_update_data:
        logger.info("Submitting batchUpdate for %d row(s) to Google Sheets...", len(batch_update_data))
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "valueInputOption": "USER_ENTERED",
                "data": batch_update_data
            }
        ).execute()

    # 4. DISPATCH BATCH APPEND IF ANY NEW ROWS
    if rows_to_append:
        logger.info("Appending %d new row(s) to Google Sheet...", len(rows_to_append))
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=RANGE_NAME,
            valueInputOption="USER_ENTERED",
            body={"values": rows_to_append}
        ).execute()

    report = {
        "appended": appended,
        "updated": updated,
        "skipped": skipped
    }
    logger.info(
        "Successfully finished sheet sync. Appended: %d, Updated: %d, Skipped/Unchanged: %d",
        len(appended), len(updated), len(skipped)
    )
    return report
