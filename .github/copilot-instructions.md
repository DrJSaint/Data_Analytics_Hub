# Copilot instructions: Data Analytics Hub

## Project
A single-user hub for analysing survey data. Projects hold conceptual frameworks (constructs, paths), datasets, hypotheses, analysis plans, and reproducible analysis runs. See [data dictionary.md](../data%20dictionary.md) for the metadata schema; it is the source of truth for the data model.

## Stack
- Python, Streamlit UI (`app.py`), pandas/numpy, plotly/matplotlib/seaborn, scikit-learn.
- DuckDB is the single persistent metadata database. Dependencies are in `requirements.txt`.
- Example data lives in `data/examples/`. Run the app with `streamlit run app.py`.

## Data model conventions
- UUID primary keys; `TIMESTAMPTZ` stored in UTC; `snake_case` table and column names.
- Use foreign keys to tie records to their project and analysis context.
- Datasets, framework versions, analysis plans, and completed runs are immutable snapshots. Create a new version or run instead of updating in place.
- Store uploaded source files outside the database in project-specific storage. The database holds only the relative path and a SHA-256 checksum.
- Never store respondent-level survey answers in the metadata tables.
- Use `JSON` columns only for method-specific settings. Keep common searchable fields as regular columns.
- Record the lineage of results: run -> dataset, framework version, and plan.

## Working style
- Keep changes small and focused. Update the data dictionary when the schema changes.
- Do not commit secrets. Keep API keys in `.env` (loaded via python-dotenv), which is git-ignored.
- Add new dependencies to `requirements.txt`.
