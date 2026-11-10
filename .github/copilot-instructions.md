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

## Current state
- `app.py` is a Streamlit prototype. It takes a survey CSV and an optional codebook CSV, and shows a variable profile and a data preview. Nothing is saved to disk or a database yet.
- Example files in `data/examples/`: `marketing_purchase_intention_survey.csv` (raw items only, no composite scores) and `marketing_purchase_intention_codebook.csv`.

## Codebook format
- One row per variable, UTF-8 CSV, with columns: `variable_name, label, data_type, measurement_level, value_labels, missing_codes, construct, reverse_coded, role, derived_from`.
- `role` is `id`, `demographic`, `item` or `derived`. Items use `code=label` pairs in `value_labels`. Demographics list allowed categories. Use `;` as the separator inside cells, and quote cells that contain commas.
- `variable_name` must match the data header exactly.
- Composite scores (`role = derived`) are not in the raw data. The app computes each as the mean of the items in `derived_from`, in memory only, and offers a CSV download. Do not overwrite a derived column that already exists in the upload.
- The app validates that data and codebook variables match, and that observed values are allowed by the codebook.
- Items marked `reverse_coded = TRUE` are flipped (min + max - value, using the codes in `value_labels`) before computing derived means and Cronbach's alpha.
- A "Scale reliability" table reports Cronbach's alpha per `construct` (complete cases only) with alpha-if-item-dropped.
- A "Descriptives" section (plotly charts in tabs) covers construct score summaries and histograms, group comparison by categorical demographics (those with `value_labels`, ordered as in the codebook), item response distributions per construct, and a sample profile.

## Working style
- Keep changes small and focused. Update the data dictionary when the schema changes.
- Do not commit secrets. Keep API keys in `.env` (loaded via python-dotenv), which is git-ignored.
- Add new dependencies to `requirements.txt`.
