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


def scored_items(frame, codebook, names):
    """Return item columns with reverse-coded items flipped using the scale range in value_labels."""
    info = codebook.drop_duplicates("variable_name").set_index("variable_name")
    scored = frame[names].apply(pd.to_numeric, errors="coerce")
    for name in names:
        row = info.loc[name] if name in info.index else None
        if row is None or str(row["reverse_coded"]).strip().upper() != "TRUE" or pd.isna(row["value_labels"]):
            continue
        codes = pd.to_numeric([l.split("=", 1)[0] for l in row["value_labels"].split(";")], errors="coerce")
        codes = codes[~pd.isna(codes)]
        if len(codes):
            scored[name] = codes.min() + codes.max() - scored[name]
    return scored


def cronbach_alpha(items):
    items = items.dropna()
    k = items.shape[1]
    total_variance = items.sum(axis=1).var(ddof=1)
    if k < 2 or len(items) < 2 or total_variance == 0:
        return float("nan")
    return k / (k - 1) * (1 - items.var(ddof=1).sum() / total_variance)


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

codebook = None
computed = set()

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
    derived = codebook[codebook["role"] == "derived"]
    for name in sorted(coded - data_columns - set(derived["variable_name"])):
        problems.append(f"'{name}' is in the codebook but not the data.")

    # Derived scores absent from the upload are computed as the mean of their source items.
    for _, row in derived.iterrows():
        name = row["variable_name"]
        if name in data_columns:
            continue
        sources = [s.strip() for s in str(row["derived_from"]).split(";") if s.strip()]
        if sources and all(s in data_columns for s in sources):
            data[name] = scored_items(data, codebook, sources).mean(axis=1).round(2)
            computed.add(name)
        else:
            problems.append(f"'{name}' cannot be computed: its source items are missing from the data.")
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
    if computed:
        st.info(f"Computed from the codebook: {', '.join(sorted(computed))}")

    st.dataframe(codebook, hide_index=True, use_container_width=True)

profile = pd.DataFrame(
    {
        "Variable": data.columns.astype(str),
        "Detected type": data.dtypes.astype(str).to_numpy(),
        "Missing": data.isna().sum().to_numpy(),
        "Distinct values": data.nunique(dropna=True).to_numpy(),
    }
)

if codebook is not None:
    info = codebook.drop_duplicates("variable_name").set_index("variable_name")
    for column, title in [
        ("label", "Label"),
        ("role", "Role"),
        ("construct", "Construct"),
        ("measurement_level", "Measurement level"),
    ]:
        profile[title] = profile["Variable"].map(info[column])
    profile["Source"] = profile["Variable"].map(lambda v: "Computed" if v in computed else "Uploaded")

st.subheader("Variable profile")
st.dataframe(profile, hide_index=True, use_container_width=True)

st.subheader("Data preview")
st.dataframe(data.head(25), hide_index=True, use_container_width=True)

if codebook is not None:
    items = codebook[(codebook["role"] == "item") & codebook["construct"].notna()]
    rows = []
    for construct, group in items.groupby("construct", sort=False):
        names = [n for n in group["variable_name"] if n in data.columns]
        if len(names) < 2:
            continue
        scored = scored_items(data, codebook, names)
        alpha = cronbach_alpha(scored)
        drop_alpha = {n: cronbach_alpha(scored.drop(columns=n)) for n in names} if len(names) > 2 else {}
        best = max(drop_alpha, key=lambda n: drop_alpha[n]) if drop_alpha else None
        rows.append(
            {
                "Construct": construct,
                "Items": ", ".join(names),
                "Complete cases": int(scored.dropna().shape[0]),
                "Cronbach's alpha": round(alpha, 3),
                "Reading": "Good (>= 0.8)" if alpha >= 0.8 else "Acceptable (>= 0.7)" if alpha >= 0.7
                else "Questionable (< 0.7)" if alpha == alpha else "Not computable",
                "Alpha if item dropped (highest)": f"{best}: {drop_alpha[best]:.3f}" if best else "",
            }
        )
    if rows:
        st.subheader("Scale reliability")
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.caption("Alpha uses complete cases only and flips items marked reverse_coded in the codebook.")

if computed:
    base_name = uploaded_file.name.rsplit(".", 1)[0]
    st.download_button(
        "Download data with computed scores (CSV)",
        data=data.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{base_name}_with_scores.csv",
        mime="text/csv",
    )

st.caption("This prototype keeps the uploaded file in memory for preview; it does not save it to disk or a database.")