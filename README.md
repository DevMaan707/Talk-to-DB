# Talk to DB (NL2SQL) — Research-Grade Enhancements

This app turns natural-language questions into SQL and executes them against a database. It now includes multiple research-aligned improvements for safety, accuracy, and transparency, plus a full Docker-based test harness.

## What Changed and Why It Matters

New capabilities in this version:

- Ambiguity detection before query generation. The system asks clarifying questions when the request is vague.
- Confidence scoring for each generated SQL query. Users see whether the system is highly confident or uncertain.
- In-session few-shot memory. When a user confirms a correct query, it is reused as a prompt example to improve subsequent outputs.
- Column-level semantic retrieval. Only the most relevant columns are injected into the prompt, reducing noise and hallucination risk.
- Temporal context grounding. The system infers date/time ranges from the database to interpret terms like “recent.”
- Schema drift detection. The app warns if the schema has changed since last run.
- Role-based access control. Queries touching sensitive or financial intents can be blocked by role.
- Semantic result validation. The system flags results that seem inconsistent with the question.

These changes shift the system from a single-shot NL2SQL tool to a more interactive, guardrailed assistant with measurable transparency.

## Latest Research Topics This Maps To

The current research landscape includes these themes:

- Retrieval-augmented generation (RAG) for schema grounding and tool reliability.
- Interactive clarification to resolve ambiguous user intent.
- Uncertainty estimation and confidence signaling to the user.
- Few-shot adaptation using in-session examples.
- Column-level semantic search and schema pruning.
- Safety and access control in LLM-to-database systems.
- Automated validation and verification for LLM outputs.

This repository implements several of these themes directly, with an emphasis on reliability and user trust.

## Technical Implementation (How It Works)

Core flow:

- The app loads schema metadata via SQLAlchemy.
- A column-level embedding index is built using sentence-transformers plus FAISS.
- For each query, the system retrieves the most relevant columns and builds a prompt.
- It optionally asks clarification questions if the request is ambiguous.
- It generates SQL with Groq models via LangChain.
- It computes a confidence score using a second LLM call.
- It runs the query and performs semantic validation against the result preview.
- User feedback can be saved and reused as prompt hints in future sessions.

Key modules:

- LLM and query logic: `llm_agent.py`
- UI flow and user interaction: `app.py`
- Drift detection and feedback storage: `utils.py`

## General Implementation (User Experience)

What users see:

- A clarification step if the query is ambiguous.
- A confidence badge after SQL is generated.
- An explanation of results (optional).
- A warning if results look inconsistent with the question.
- A feedback prompt to mark results as correct or incorrect.

This makes the system more transparent and safer for exploration.

## Does It Give an Edge?

Likely advantages:

- Higher accuracy on ambiguous or schema-complex queries.
- Lower hallucination risk by pruning irrelevant columns.
- Better user trust through confidence signaling and warnings.
- Faster adaptation to a specific schema via in-session examples.

Tradeoffs and risks:

- More latency due to extra LLM calls (ambiguity check, confidence, validation).
- Higher cost for additional model calls.
- Column embedding may leak sensitive values if sample data is sensitive.
- Confidence scoring is still model-based and can be wrong.
- Clarifications may feel slow for expert users.

Bottom line: It is a meaningful edge in reliability and user trust, but it is not perfect. For high-stakes use cases, you should still gate access, audit queries, and validate outputs.

## How to Interpret Good or Bad Results

Good signs:

- Confidence is high and the SQL references the expected tables or columns.
- Result validation says the output aligns with the question.
- User can restate the question and get consistent results.

Bad signs:

- Confidence is low or validation flags the output.
- The query hits unrelated tables or columns.
- The system asks for clarification but the user skips it.

Treat low-confidence or flagged outputs as needs review.

## Test and Docker Setup

The repository includes a Docker seed script and a full test suite.

Commands:

- Start test DB: `python setup_docker_db.py start`
- Check status: `python setup_docker_db.py status`
- Stop DB: `python setup_docker_db.py stop`
- Destroy DB: `python setup_docker_db.py destroy`

Test groups:

- Fast tests: `python run_all_tests.py fast`
- LLM tests: `python run_all_tests.py llm`
- DB tests: `python run_all_tests.py db`
- All tests: `python run_all_tests.py all`

## Notes on Keys and Privacy

Do not commit API keys. Set `GROQ_API_KEY` in your environment or `.env` file. If you pasted a key into any chat, rotate it immediately.
