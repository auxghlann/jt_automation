# Job Tracker Automation - Agent Constitution & Project Rules

Welcome to the **Job Tracker Automation** project! This document serves as the workspace constitution for all AI agents contributing to this codebase.

## Absolute Source of Truth
CRITICAL: You MUST refer to the `.spec/` directory for the definitive truth regarding this project's requirements, architecture, API contracts, and data model. Do not guess or hallucinate features; read the specs first.

Start navigation from `.spec/README.md` or the corresponding component index:
- Product Requirements & Scope: `.spec/requirements/README.md`
- Architecture & System Boundaries: `.spec/architecture/README.md`
- System Diagrams & Visual Flows: `.spec/diagrams/README.md`
- API Contracts & Conventions: `.spec/api/README.md`
- Data Model & Persistence: `.spec/data-model/README.md`
- Legal & Compliance Specifications: `.spec/legal-documents/README.md`
- Dev Guide & Commands: `.spec/development/README.md`
- Architectural Decision Log: `.spec/decisions/README.md`
- Active Implementation Plans: `.spec/plans/`

Always align your implementation plans and code changes with the documents in `.spec/` before writing code. Load only the specific subcomponent markdown files needed for your immediate task to avoid unnecessary context bloat.

## Architecture Overview
This project is an AI-powered agentic workflow that automates job application tracking by reading Gmail and syncing updates to Google Sheets.
- **Workflow Engine**: [LangGraph](https://python.langchain.com/docs/langgraph) (`app/agent/workflow.py`).
- **LLM Provider**: Google Generative AI (`gemma-4-31b-it` via LangChain in `app/agent/model.py`).
- **Tooling Interface**: Model Context Protocol (`mcp.server.fastmcp` in `app/services/mcp_server.py`).
- **Package Manager**: `uv` (fast Python package manager).

## Core Directives

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
- **Environment & Secrets Guard**: Assume `.env`, `credentials.json`, `token.json`, and `processed_emails.json` are local-only and safely ignored by `.gitignore`. Never write code that attempts to commit or expose these files.
- **Never read, open, or inspect private environment files** (e.g. `.env`). Strictly rely only on `.env.example`.
- **Non-Interactive Auth**: Automated routines must call `get_credentials(interactive=False)` to fail gracefully rather than attempting to launch a browser session.

### 4. Data Deduplication & Caching
- **Email Cache**: We use `processed_emails.json` as a local cache to store `Message IDs` of emails we have already processed. This strictly prevents redundant LLM processing and saves tokens.
- **Google Sheets Deduplication**: When upserting to Google Sheets (`app/services/sheets_service.py`), the logic matches based on `Company Name` and `Job Title` in range `Sheet1!A:G`. It only updates the row if the application `status` has actually changed (e.g., from `applied` to `interview`) and preserves initial `Date Applied`.

### 5. Codebase Hygiene & Engineering Standards
- **Spec-First & Plan-First**: Create a plan in `.spec/plans/` for significant changes before modifying code.
- **Minimal & Surgical Edits**: Write only the absolute minimum code necessary for the immediate task (Ponytail ladder). Leave unbroken adjacent code untouched.
- **Strict Push & Commit Guard**: Never execute `git push` or `git commit` unless explicitly instructed or approved by the user.
- **Strict Icon & Emoji Rule**: Strictly avoid adding emojis as icons in code or in documentation.
- **Terminal Shell**: Always use PowerShell syntax when proposing terminal commands.

## Consulting SDLC Skills
Refer to the SDLC agent workflow skills (`saw-*`) in `.agents/skills/` or persistent global skills:
- **Project Context Scaffolding**: `saw-init-project`
- **Security & Vulnerability Audit**: `saw-security-check`
- **Pull Request & Commit Flow**: `saw-pr`
- **Specification Drift Sync**: `saw-update-spec`
- **Session Recall & Quiz Generation**: `saw-quiz-me`
- **Workflow Guide & Reference**: `saw-help` (`/saw-help`)

## Companion Optimization Skills
- **Ponytail Suite** (`/ponytail [lite|full|ultra]`): Enforces minimal code and YAGNI ladder.
  - Commands: `/ponytail-help`, `/ponytail-review`, `/ponytail-audit`, `/ponytail-debt`.
- **Caveman Mode** (`/caveman [lite|full|ultra]`): Token-efficient compressed communication. Exempts legal specifications in `.spec/legal-documents/`.
