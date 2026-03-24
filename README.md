# Talk to DB

Talk to DB is a governed NL-to-SQL system built for real database use, not just text-to-query generation. It converts natural-language questions into SQL, shows the reasoning and evidence behind the SQL, validates the query against the live schema, and only executes after user approval.

The project is designed for a BTech major project setting where the goal is to demonstrate both AI capability and engineering rigor.

## What This Project Uses

- `Streamlit` for the UI
- `SQLAlchemy` and `psycopg2` for database access
- `Groq` via `langchain-groq` for SQL generation, confidence scoring, ambiguity detection, and result validation
- `sentence-transformers` for schema embeddings
- `FAISS` for column-level semantic retrieval
- `Docker` + `PostgreSQL` for the demo database and repeatable tests

## Why This Project Is Better Than a Basic NL2SQL Demo

Most NL2SQL demos stop at:

- user asks a question
- model generates SQL
- query runs

This project adds the missing controls that make the system defensible in a real-world setting:

- `Interactive ambiguity resolution`
  - If a query is vague, the system asks for clarification before generating SQL.
- `Schema-grounded retrieval`
  - It retrieves only the most relevant columns instead of dumping the entire schema into the prompt.
- `Evidence panel`
  - The UI shows why the SQL was generated: retrieved columns, tables considered, relationships, and temporal bounds.
- `Preview before execution`
  - SQL is shown first. Execution happens only after approval.
- `Static SQL validation`
  - The query is checked against the actual schema before it hits the database.
- `Runtime safety`
  - Non-`SELECT` statements are blocked.
- `Confidence scoring`
  - The system reports whether the generated SQL looks high, medium, or low confidence.
- `Semantic result validation`
  - After execution, the system checks whether the result appears to answer the original question.
- `Role-based access control`
  - Different user roles can be blocked from sensitive or financial queries.
- `Feedback and memory`
  - User corrections and approved examples are reused to improve future prompts.
- `Schema drift detection`
  - The system warns when the schema changes and older prompt memory may be stale.

## How We Position It Against Existing Papers

This project should be presented as stronger in `practical deployment`, `runtime governance`, and `user trust`, not as universally more accurate than every paper.

### Compared with DBPal

DBPal focuses on natural-language to SQL generation. This project goes further in deployment behavior:

- asks clarifying questions instead of blindly guessing
- shows SQL before execution
- validates SQL against the actual live schema
- blocks unsafe statements
- provides confidence and semantic result checks

### Compared with RAG-based Text-to-SQL work

RAG-based systems improve grounding by retrieving schema context. This project adds:

- column-level retrieval instead of only broad schema context
- persistent embedding cache
- relationship-aware schema context
- evidence display in the UI
- schema drift warnings
- feedback-based adaptation across sessions

### Compared with TAG-style architectural work

TAG-style work is useful conceptually, but this repository is a working product with:

- a live UI
- a repeatable demo database
- role-based controls
- preview-and-approve execution
- testing for retrieval, validation, drift detection, and database flow

## Main Contributions

These are the strongest points to emphasize in a project report or viva:

1. `Governed NL2SQL workflow`
   - generation is not the end; the system verifies, explains, and gates execution
2. `Explainable schema grounding`
   - retrieval results are exposed to the user through the evidence panel
3. `Adaptive database-specific behavior`
   - embeddings, feedback, and few-shot memory make the system improve for a given schema
4. `Safer execution model`
   - static validation, role checks, and preview-before-run reduce hallucination damage

## Feature List

### Core Query Flow

- Natural-language to SQL generation
- Multi-dialect SQL prompting
- Read-only query enforcement
- SQL preview and explicit execution approval
- Result explanation

### Grounding and Accuracy

- Column-level semantic retrieval with FAISS
- Persistent embedding cache on disk
- Relationship-aware schema expansion
- Temporal context extraction from database data ranges
- In-session few-shot memory
- Stored correction annotations

### Trust and Safety

- Ambiguity detection
- Confidence scoring
- Semantic result validation
- Role-based access control
- Schema drift detection
- Static SQL validation
- Deterministic schema inspection for schema-style questions

### Demo and Testing Support

- Dockerized PostgreSQL test database
- Seeded sample data
- Fast tests, LLM tests, and live DB tests

## System Flow

This is the actual runtime flow of the application:

1. User connects a database.
2. The app loads tables, columns, and relationships from the live schema.
3. The app checks schema drift.
4. The app builds or loads the schema embedding index.
5. The user enters a natural-language question.
6. The system checks role permissions.
7. The system checks whether the question is ambiguous.
8. The retriever selects relevant columns and related schema context.
9. The prompt is built using:
   - SQL dialect rules
   - schema context
   - temporal bounds
   - feedback annotations
   - few-shot memory
10. The LLM generates SQL.
11. The SQL is validated against the schema.
12. The UI shows:
   - generated SQL
   - confidence score
   - evidence panel
13. The user approves execution.
14. The query runs.
15. The result is semantically validated.
16. The user can mark the result as correct or incorrect.

## Prerequisites

Before running the project, make sure these are installed on your machine:

- `Python 3.10+`
- `Docker Desktop`
- `Git`

Quick checks:

```powershell
python --version
docker --version
git --version
```

If `docker --version` fails, install Docker Desktop and start it before continuing.

## First-Time Setup

### 1. Get the Project

If you already have the repo locally, open a terminal in the project folder.

If not:

```powershell
git clone git@github.com:DevMaan707/Talk-to-DB.git
cd Talk-to-DB
```

### 2. Create a Virtual Environment

This is optional, but recommended.

```powershell
python -m venv .venv
.venv\Scripts\activate
```

If activation is blocked in PowerShell, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\activate
```

## Step-by-Step: How to Start Using It

### 1. Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

If you need the retrieval and DB stack manually:

```powershell
python -m pip install psycopg2-binary sqlalchemy sentence-transformers faiss-cpu numpy python-dotenv
```

### 2. Set the Groq API Key

PowerShell:

```powershell
$env:GROQ_API_KEY="YOUR_GROQ_API_KEY"
```

Or create a local `.env` file:

```env
GROQ_API_KEY=YOUR_GROQ_API_KEY
```

`.env` is ignored by git.

### 3. Start the Demo Database

```powershell
python setup_docker_db.py start
```

What this command does:

- creates a PostgreSQL Docker container named `talktodb_pg`
- maps container port `5432` to local port `5433`
- creates a database named `talktodb_test`
- creates sample `employees` and `orders` tables
- inserts demo data automatically

You do not need to manually create the Docker container if you use this script.

To verify the DB is running:

```powershell
python setup_docker_db.py status
```

If you want to stop or remove it later:

```powershell
python setup_docker_db.py stop
python setup_docker_db.py destroy
```

### 3A. Optional: Manual Docker Way

If you want to create the PostgreSQL container manually instead of using the helper script:

```powershell
docker run -d --name talktodb_pg -e POSTGRES_DB=talktodb_test -e POSTGRES_USER=testuser -e POSTGRES_PASSWORD=testpass -p 5433:5432 postgres:15
```

Then seed it using:

```powershell
python setup_docker_db.py seed
```

For most users, `python setup_docker_db.py start` is the correct path.

### 4. Run the App

```powershell
python -m streamlit run app.py
```

Open:

```text
http://127.0.0.1:8501
```

If the app does not open automatically, copy the URL into your browser.

### 5. Connect to the Demo Database

You can either paste the URI directly or use the form and generate it.

Demo URI:

```text
postgresql+psycopg2://testuser:testpass@localhost:5433/talktodb_test
```

This URI means:

- `postgresql+psycopg2` = PostgreSQL driver
- `testuser` = database username
- `testpass` = database password
- `localhost` = database is on your own machine
- `5433` = mapped Docker port
- `talktodb_test` = database name

If you use the generate form, enter:

- Host: `localhost`
- Port: `5433`
- Username: `testuser`
- Password: `testpass`
- Database Name: `talktodb_test`
- Database Type: `PostgreSQL`

### 6. What to Click in the UI

When the app opens:

1. Choose `Yes, I know the URI` if you want to paste the full DB URI.
2. Paste:
   `postgresql+psycopg2://testuser:testpass@localhost:5433/talktodb_test`
3. Or choose `No, generate it for me` and fill the form values shown above.
4. Choose your role from the sidebar.
5. Type a question in the text area.
6. Click the query button.
7. Review the generated SQL and the `Why this SQL?` panel.
8. Click the execute button to run it.

### 7. Choose a Role

- `viewer`
  - basic lookup and aggregation only
- `analyst`
  - includes financial queries
- `admin`
  - full query intent access

Use `admin` for the most complete demo, because some financial or sensitive queries are blocked for other roles.

### 8. Ask a Query

Recommended demo prompts:

- `show all employees`
- `show total revenue by product`
- `list employees created recently`
- `show me the schema`
- `show top products`

### 9. If Ambiguity Is Detected

The app may ask for clarification. Type the clarification and submit it. The system then rebuilds the query with the clarified intent.

Example:

- user asks: `show top products`
- app asks: top by what metric?
- user clarifies: `top by total revenue`

### 10. Review the Query Preview

Before execution, the app shows:

- generated SQL
- confidence score
- `Why this SQL?` evidence panel

The evidence panel shows:

- tables considered
- retrieved columns and why they matched
- join evidence
- temporal ranges used

### 11. Approve and Execute

Click the execute button after reviewing the SQL.

After execution, the app shows:

- result table
- downloadable CSV
- explanation section
- semantic validation warning if needed
- feedback section for corrections

## Quick Start for Demo Day

If you only want the shortest working path:

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
$env:GROQ_API_KEY="YOUR_GROQ_API_KEY"
python setup_docker_db.py start
python -m streamlit run app.py
```

Then open `http://127.0.0.1:8501` and use:

```text
postgresql+psycopg2://testuser:testpass@localhost:5433/talktodb_test
```

## Step-by-Step: How to Test It

### Fast Tests

These do not need a live DB or live LLM access.

```powershell
python run_all_tests.py fast
```

### LLM Tests

These require `GROQ_API_KEY`.

```powershell
python run_all_tests.py llm
```

### Database Tests

These require the Docker database to be running.

```powershell
python run_all_tests.py db
```

### Full Test Run

```powershell
python run_all_tests.py all
```

### Check or Reset the Demo DB

```powershell
python setup_docker_db.py status
python setup_docker_db.py stop
python setup_docker_db.py destroy
```

## Troubleshooting

### Docker Is Not Running

Symptom:

- `python setup_docker_db.py start` fails

Fix:

- open Docker Desktop
- wait until Docker reports it is running
- run the start command again

### Port 5433 Is Already In Use

Symptom:

- the DB fails to start or the app connects to the wrong PostgreSQL server

Fix:

- stop the existing service using port `5433`
- or change the port in `setup_docker_db.py` and the URI you use in the app

### Streamlit Does Not Start

Symptom:

- `python -m streamlit run app.py` fails

Fix:

- make sure dependencies are installed
- run `python -m pip install -r requirements.txt`

### The App Says the API Key Is Missing

Symptom:

- query generation fails before SQL is produced

Fix:

- set `GROQ_API_KEY` in PowerShell or `.env`
- restart Streamlit after changing the key

### The App Cannot Connect to PostgreSQL

Symptom:

- connection refused or password/authentication failure

Fix:

- run `python setup_docker_db.py status`
- if broken, run:

```powershell
python setup_docker_db.py destroy
python setup_docker_db.py start
```

## Suggested Viva Demo Flow

Use this sequence if you need a clean and convincing demo:

1. Start the demo database.
2. Run the app.
3. Connect using the seeded PostgreSQL URI.
4. Ask `show top products`.
5. Let the ambiguity detector ask what `top` means.
6. Clarify the metric.
7. Show the confidence badge.
8. Open `Why this SQL?`.
9. Approve the SQL and execute it.
10. Show explanation, validation, and feedback flow.
11. Switch roles and show a blocked sensitive query.
12. Ask `show me the schema` and show deterministic schema output.

## Current Limitations

This project is stronger than a basic NL2SQL demo, but it is not magic. These are valid limitations to state openly:

- Confidence scoring is model-based, so it can still be wrong.
- Extra LLM calls increase latency and token cost.
- Semantic retrieval quality depends on schema naming and sample values.
- Relationship evidence is most useful on schemas that actually define foreign keys.
- The demo database is intentionally small and simple.

## Why This Still Gives an Edge

For a major project, the edge is not only better SQL generation. The edge is that the system is:

- more explainable
- safer to execute
- better grounded in the actual schema
- interactive when intent is unclear
- testable and reproducible

That is a stronger project story than a plain chatbot that generates SQL and hopes it is correct.
