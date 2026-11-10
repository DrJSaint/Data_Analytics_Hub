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

st.subheader("Data preview")
st.dataframe(data.head(25), hide_index=True, use_container_width=True)

st.caption("This prototype keeps the uploaded file in memory for preview; it does not save it to disk or a database.")