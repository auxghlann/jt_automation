<div align="center">

# Job Tracker Automation

![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_Workflow-FF6F00)
![Groq](https://img.shields.io/badge/Groq-Llama_3-000000)
![MCP](https://img.shields.io/badge/MCP-Google_Integration-4285F4)

> An AI-powered agentic workflow that automates job application tracking. It uses LangGraph to autonomously fetch Gmail updates via MCP, extract application statuses, and  sync them to Google Sheets.

</div>

## Key Features
- **MCP Gmail Integration**: Connects securely to your Gmail inbox via the Model Context Protocol (MCP) to read emails locally.
- **Google Sheets Sync**: Updates existing rows when a job application progresses (e.g., from `applied` to `interview`) instead of creating duplicates.
- **Token Optimization**: Employs aggressive Regex & BeautifulSoup cleaning to vaporize invisible characters, tracking URLs, and LinkedIn footers before they ever reach the LLM.
- **Caching**: Automatically ignores previously processed emails to save thousands of tokens on every run.

## Prerequisites

1. **Python 3.11+** installed on your system.
2. **`uv` Package Manager**: Install `uv` for blazing-fast dependency resolution.
3. **Google Cloud Console**: You need a `credentials.json` file with OAuth 2.0 Client IDs for:
   - Gmail API (`gmail.readonly`)
   - Google Sheets API

## Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/auxghlann/jt_automation.git
   cd jt_automation
   ```

2. **Install dependencies using `uv`:**
   ```bash
   uv sync
   ```

3. **Set up Google Sheets:**
   - Open your browser and create a new Google Sheet.
   - Set up the first row (headers) with these columns: `Company | Title | Location | Status | Summary`. (Ensure your tab is named `Sheet1`).
   - Find your **Spreadsheet ID** in the URL. It is the long string of random characters between `/d/` and `/edit`.
     - Example URL: `https://docs.google.com/spreadsheets/d/`**`1SzD9gNRZqlb_xomEI7mYn1HADS5vahV1pKydqtSFhOg`**`/edit`

4. **Configure Environment Variables:**
   Create a `.env` file in the root directory and add your Groq API key and the Spreadsheet ID you just found:
   ```env
   GROQ_API_KEY="gsk_your_groq_api_key_here"
   SPREADSHEET_ID="your_google_spreadsheet_id_here"
   ```

5. **Set up Google Authentication:**
   - Download your `credentials.json` from the Google Cloud Console and place it in the root of the project.
   - Run the authentication script to generate your OAuth token:
   ```bash
   uv run app/services/google_auth.py
   ```
   - *Note: A browser window will open asking you to grant permissions. Once completed, a `token.json` file will be generated locally.*

## Usage

Once your environment is set up and authenticated, you can run the automation script:

```bash
uv run main.py
```

The script will:
1. Connect to your Gmail via MCP.
2. Fetch recent emails.
3. Skip emails it has already processed in previous runs.
4. Parse and extract job updates (Applied, Viewed, Interview, Rejected, Accepted).
5. Connect to your Google Sheet and perform smart deduplication/updates.
6. Print a summary to the console!

## Security
- Your `token.json`, `credentials.json`, `processed_emails.json`, and `.env` are safely ignored by `.gitignore`. They will never be pushed to version control.
