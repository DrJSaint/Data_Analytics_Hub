import pandas as pd
import streamlit as st


st.set_page_config(page_title="Survey Data Intake", layout="wide")

st.title("Survey data intake")
st.caption("Upload a survey CSV to inspect its structure before analysis.")

uploaded_file = st.file_uploader(
    "Choose a CSV file",
    type=["csv"],
    help="The current prototype accepts CSV files.",
)

codebook_file = st.file_uploader(
    "Choose a codebook CSV (optional)",
    type=["csv"],
    help="One row per variable. Required columns: variable_name, label, data_type, "
    "measurement_level, value_labels, missing_codes, construct, reverse_coded, role, derived_from.",
)

CODEBOOK_COLUMNS = [
    "variable_name", "label", "data_type", "measurement_level", "value_labels",
    "missing_codes", "construct", "reverse_coded", "role", "derived_from",
]

if uploaded_file is None:
    st.info("Upload a CSV to see its variables, missing values, and a data preview.")
    st.stop()

try:
    data = pd.read_csv(uploaded_file)
except (UnicodeDecodeError, pd.errors.EmptyDataError, pd.errors.ParserError) as error:
    st.error(f"Could not read this CSV: {error}")
    st.stop()

if data.empty:
    st.warning("This CSV has column headers but no data rows.")
    st.stop()

row_count, column_count = data.shape
missing_count = int(data.isna().sum().sum())

st.caption(f"File: {uploaded_file.name}")
summary_columns = st.columns(3)
summary_columns[0].metric("Responses", f"{row_count:,}")
summary_columns[1].metric("Variables", f"{column_count:,}")
summary_columns[2].metric("Missing cells", f"{missing_count:,}")

profile = pd.DataFrame(
    {
        "Variable": data.columns.astype(str),
        "Detected type": data.dtypes.astype(str).to_numpy(),
        "Missing": data.isna().sum().to_numpy(),
        "Distinct values": data.nunique(dropna=True).to_numpy(),
    }
)

st.subheader("Variable profile")
st.dataframe(profile, hide_index=True, use_container_width=True)

if codebook_file is not None:
    try:
        codebook = pd.read_csv(codebook_file, encoding="utf-8-sig", dtype=str)
    except (UnicodeDecodeError, pd.errors.EmptyDataError, pd.errors.ParserError) as error:
        st.error(f"Could not read the codebook: {error}")
        st.stop()

    st.subheader("Codebook check")
    missing_headers = [c for c in CODEBOOK_COLUMNS if c not in codebook.columns]
    if missing_headers:
        st.error(f"Codebook is missing columns: {', '.join(missing_headers)}")
        st.stop()

    data_columns = set(data.columns.astype(str))
    coded = set(codebook["variable_name"])
    problems = []
    for name in sorted(data_columns - coded):
        problems.append(f"'{name}' is in the data but not the codebook.")
    for name in sorted(coded - data_columns):
        problems.append(f"'{name}' is in the codebook but not the data.")
    for name in codebook.loc[codebook["variable_name"].duplicated(), "variable_name"]:
        problems.append(f"'{name}' appears more than once in the codebook.")

    for _, row in codebook.iterrows():
        name = row["variable_name"]
        if name not in data_columns or pd.isna(row["value_labels"]):
            continue
        labels = row["value_labels"].split(";")
        if row["role"] == "item":
            allowed = {label.split("=", 1)[0] for label in labels}
            observed = set(data[name].dropna().astype(str))
        elif row["role"] == "demographic":
            allowed = set(labels)
            observed = set(data[name].dropna().astype(str))
        else:
            continue
        unexpected = sorted(observed - allowed)
        if unexpected:
            problems.append(f"'{name}' has values not in the codebook: {', '.join(unexpected[:5])}")

    if problems:
        st.warning(f"{len(problems)} issue(s) found.")
        for problem in problems:
            st.write(f"- {problem}")
    else:
        st.success("Codebook matches the data.")

    st.dataframe(codebook, hide_index=True, use_container_width=True)

st.subheader("Data preview")
st.dataframe(data.head(25), hide_index=True, use_container_width=True)

st.caption("This prototype keeps the uploaded file in memory for preview; it does not save it to disk or a database.")