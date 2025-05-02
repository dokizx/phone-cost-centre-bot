
import streamlit as st
import pandas as pd
from charges import CHARGES

st.title("Phone Cost Centre Allocator")

st.write("Upload an Excel file with mobile numbers and cost centres.")

uploaded_file = st.file_uploader("Choose Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = ["Cost Centre", "Mobile Number"]

    df["Mobile Number"] = df["Mobile Number"].astype(str).str.replace(r"\D", "", regex=True)
    charges_df = pd.DataFrame(CHARGES.items(), columns=["Mobile Number", "Cost ($AUD)"])
    charges_df["Mobile Number"] = charges_df["Mobile Number"].astype(str)

    # Merge
    merged = pd.merge(df, charges_df, on="Mobile Number", how="right")

    # Clean up NSW variations
    merged["Cost Centre"] = merged["Cost Centre"].replace({
        "Bankstown": "NSW", "SYD": "NSW", "-Orange": "NSW", "NSW-": "NSW"
    })

    matched = merged[~merged["Cost Centre"].isna()]
    unmatched = merged[merged["Cost Centre"].isna()]
    centres = matched["Cost Centre"].unique()

    target_total = sum(CHARGES.values())
    matched_sum = matched["Cost ($AUD)"].sum()
    shared_total = target_total - matched_sum
    shared_cost = shared_total / len(centres)

    shared_df = pd.DataFrame({
        "Cost Centre": centres,
        "Cost ($AUD)": shared_cost
    })

    combined = pd.concat([
        matched.groupby("Cost Centre")["Cost ($AUD)"].sum().reset_index(),
        shared_df
    ]).groupby("Cost Centre")["Cost ($AUD)"].sum().reset_index()

    # Round and adjust for float errors
    diff = combined["Cost ($AUD)"].sum() - target_total
    if abs(diff) > 0:
        idx = combined["Cost ($AUD)"].idxmax()
        combined.at[idx, "Cost ($AUD)"] -= diff

    combined["Cost ($AUD)"] = combined["Cost ($AUD)"].round(2)
    total_row = pd.DataFrame([{"Cost Centre": "Total", "Cost ($AUD)": round(target_total, 2)}])
    final = pd.concat([combined, total_row], ignore_index=True)

    st.subheader("Cost Allocation:")
    st.dataframe(final)

    # Download
    csv = final.to_csv(index=False).encode()
    st.download_button("Download as CSV", csv, "cost_allocation.csv")
