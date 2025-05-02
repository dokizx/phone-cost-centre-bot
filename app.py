
import streamlit as st
import pandas as pd
import pdfplumber
import re

st.title("Invoice Cost Centre Allocator")

uploaded_pdf = st.file_uploader("Upload the PDF invoice", type=["pdf"])
uploaded_excel = st.file_uploader("Upload Excel file with phone numbers and cost centres", type=["xlsx"])

def extract_charges(pdf_file):
    charges = {}
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            for line in text.split("\n"):
                match = re.search(r"(04\d{8})\D+\$?(\d+\.\d{2})", line)
                if match:
                    phone, amount = match.groups()
                    charges[re.sub(r"\D", "", phone)] = float(amount)
    return charges

if uploaded_pdf and uploaded_excel:
    st.info("Extracting charges from PDF...")
    charges = extract_charges(uploaded_pdf)
    df_charges = pd.DataFrame(charges.items(), columns=["Mobile Number", "Cost ($AUD)"])

    st.info("Reading phone numbers from Excel...")
    df_cost_centres = pd.read_excel(uploaded_excel)
    df_cost_centres.columns = ["Cost Centre", "Mobile Number"]
    df_cost_centres["Mobile Number"] = df_cost_centres["Mobile Number"].astype(str).str.replace(r"\D", "", regex=True)
    df_charges["Mobile Number"] = df_charges["Mobile Number"].astype(str)

    # Merge and normalize names
    df_cost_centres["Cost Centre"] = df_cost_centres["Cost Centre"].replace({
        "Bankstown": "NSW", "SYD": "NSW", "-Orange": "NSW", "NSW-": "NSW"
    })

    merged = pd.merge(df_cost_centres, df_charges, on="Mobile Number", how="right")
    matched = merged[~merged["Cost Centre"].isna()]
    unmatched = merged[merged["Cost Centre"].isna()]
    unique_centres = matched["Cost Centre"].unique()

    target_total = df_charges["Cost ($AUD)"].sum()
    matched_sum = matched["Cost ($AUD)"].sum()
    remaining = target_total - matched_sum
    shared_cost = remaining / len(unique_centres) if len(unique_centres) > 0 else 0

    shared_df = pd.DataFrame({
        "Cost Centre": unique_centres,
        "Cost ($AUD)": shared_cost
    })

    result = pd.concat([
        matched.groupby("Cost Centre")["Cost ($AUD)"].sum().reset_index(),
        shared_df
    ]).groupby("Cost Centre")["Cost ($AUD)"].sum().reset_index()

    diff = result["Cost ($AUD)"].sum() - target_total
    if abs(diff) > 0:
        idx = result["Cost ($AUD)"].idxmax()
        result.at[idx, "Cost ($AUD)"] -= diff

    result["Cost ($AUD)"] = result["Cost ($AUD)"].round(2)
    total_row = pd.DataFrame([{"Cost Centre": "Total", "Cost ($AUD)": round(target_total, 2)}])
    final = pd.concat([result, total_row], ignore_index=True)

    st.success("Final Cost Allocation by Cost Centre")
    st.dataframe(final)

    csv = final.to_csv(index=False).encode()
    st.download_button("Download as CSV", csv, "cost_by_cost_centre.csv")
