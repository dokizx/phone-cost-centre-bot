# streamlit_app.py
import streamlit as st
import pdfplumber
import pandas as pd
import re

# Define cost centre mapping here or load externally
cost_centre_map = {
    "0401484801": "MELB",
    "0466361330": "NSW Industrial",
    # ... Extend as needed
}

def extract_pdf_data(pdf_file):
    data = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            matches = re.findall(r'(04\d{8})\s+\$?([\d,.]+)', text)
            for number, cost in matches:
                clean_cost = float(cost.replace(',', ''))
                data.append((number, clean_cost))
    return pd.DataFrame(data, columns=["Mobile Number", "Cost ($AUD)"])

def allocate_costs(df_charges, cost_centre_map):
    df_charges["Mobile Number"] = df_charges["Mobile Number"].astype(str)
    df_charges["Cost Centre"] = df_charges["Mobile Number"].map(cost_centre_map)

    matched = df_charges[~df_charges["Cost Centre"].isna()]
    unmatched = df_charges[df_charges["Cost Centre"].isna()]
    unique_centres = matched["Cost Centre"].unique()

    total_cost = df_charges["Cost ($AUD)"].sum()
    unmatched_total = total_cost - matched["Cost ($AUD)"].sum()
    share = unmatched_total / len(unique_centres) if len(unique_centres) > 0 else 0

    shared_df = pd.DataFrame({
        "Cost Centre": unique_centres,
        "Cost ($AUD)": share
    })

    final_df = pd.concat([
        matched.groupby("Cost Centre")["Cost ($AUD)"].sum().reset_index(),
        shared_df
    ]).groupby("Cost Centre")["Cost ($AUD)"].sum().reset_index()

    diff = final_df["Cost ($AUD)"].sum() - total_cost
    if abs(diff) > 0:
        max_idx = final_df["Cost ($AUD)"].idxmax()
        final_df.loc[max_idx, "Cost ($AUD)"] -= diff

    final_df["Cost ($AUD)"] = final_df["Cost ($AUD)"].round(2)
    final_df = pd.concat([final_df, pd.DataFrame([{"Cost Centre": "Total", "Cost ($AUD)": round(total_cost, 2)}])])
    return final_df

# Streamlit UI
st.title("Linkt Invoice Cost Centre Allocator")
uploaded_file = st.file_uploader("Upload Linkt Invoice PDF", type="pdf")

if uploaded_file:
    charges_df = extract_pdf_data(uploaded_file)
    result_df = allocate_costs(charges_df, cost_centre_map)
    st.dataframe(result_df)
    st.download_button("Download CSV", result_df.to_csv(index=False), "allocated_costs.csv")
