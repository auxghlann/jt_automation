# Job Tracker Automation - Agent Rules & Context

Welcome to the **Job Tracker Automation** project! This document provides essential context, architectural rules, and guidelines for AI agents working in this codebase.

## Architecture Overview

This project is an AI-powered agentic workflow that automates job application tracking by reading Gmail and syncing updates to Google Sheets. 

- **Workflow Engine**: [LangGraph](https://python.langchain.com/docs/langgraph) (located in `app/agent/workflow.py`).
- **LLM Provider**: Google Generative AI (Gemma 4 via LangChain) (located in `app/agent/model.py`).
- **Tooling Interface**: Model Context Protocol (MCP) using `mcp.server.fastmcp` (located in `app/services/mcp_server.py`).
- **Package Manager**: `uv` (blazing fast Python package manager).

## Core Agent Directives

When contributing to this repository, you **MUST** adhere to the following rules:

### 1. Dependency Management
- **ALWAYS** use `uv` for dependency management. 
- Do not use `pip install` or `poetry`.
- To add a package, use `uv add <package_name>`.
- To run scripts, use `uv run <script_path>`.

### 2. LLM / LangGraph Guidelines
- **Google GenAI Quirk**: When initializing a LangGraph state or sending a prompt to the Google GenAI model (`ChatGoogleGenerativeAI`), you **cannot** pass only a `SystemMessage`. The Google API requires `contents`, so you must always pair a `SystemMessage` with at least one `HumanMessage` to avoid a `ValueError: contents are required.` crash.
- **State Management**: LangGraph states (`AgentState`) must use Pydantic `BaseModel` and strict type annotations (e.g., `Annotated[list[AnyMessage], add_messages]`).

### 3. Authentication & Security
- **Never modify OAuth Scopes** without explicit user permission.
- The `google_auth.py` script is tightly coupled to `mcp_server.py`. The `get_credentials()` function handles token refreshing and browser re-authentication flows. Do not bypass this function when requiring Google API credentials.
- **Secrets**: Assume `.env`, `credentials.json`, `token.json`, and `processed_emails.json` are local-only and safely ignored by `.gitignore`. Never write code that attempts to commit these files.

### 4. Data Deduplication & Caching
- **Email Cache**: We use `processed_emails.json` as a local cache to store `Message IDs` of emails we have already processed. This strictly prevents redundant LLM processing and saves tokens. 
- **Google Sheets Deduplication**: When upserting to Google Sheets (`app/services/sheets_service.py`), the logic matches based on `Company Name` and `Job Title`. It only updates the row if the application `status` has actually changed (e.g., from `applied` to `interview`).

