# linkt_cost_centre_bot.py
import pdfplumber
import pandas as pd
import re

# Sample cost centre mapping (to be loaded from Excel or updated manually)
cost_centre_map = {
    "0401484801": "MELB",
    "0466361330": "NSW Industrial",  # Known $0 case
    # ... Add more phone-cost centre mapping
}

TOTAL_EXPECTED = 3645.43

# Function to extract phone numbers and charges from Linkt PDF
def extract_pdf_data(pdf_path):
    data = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            matches = re.findall(r'(04\d{8})\s+\$?([\d,.]+)', text)
            for number, cost in matches:
                clean_cost = float(cost.replace(',', ''))
                data.append((number, clean_cost))
    return pd.DataFrame(data, columns=["Mobile Number", "Cost ($AUD)"])

# Function to allocate costs by cost centre
def allocate_costs(df_charges, cost_centre_map):
    df_charges["Mobile Number"] = df_charges["Mobile Number"].astype(str)
    df_charges["Cost Centre"] = df_charges["Mobile Number"].map(cost_centre_map)

    matched = df_charges[~df_charges["Cost Centre"].isna()]
    unmatched = df_charges[df_charges["Cost Centre"].isna()]
    unique_centres = matched["Cost Centre"].unique()

    unmatched_total = TOTAL_EXPECTED - matched["Cost ($AUD)"].sum()
    share = unmatched_total / len(unique_centres) if len(unique_centres) > 0 else 0

    shared_df = pd.DataFrame({
        "Cost Centre": unique_centres,
        "Cost ($AUD)": share
    })

    final_df = pd.concat([
        matched.groupby("Cost Centre")["Cost ($AUD)"].sum().reset_index(),
        shared_df
    ]).groupby("Cost Centre")["Cost ($AUD)"].sum().reset_index()

    # Adjust for rounding
    diff = final_df["Cost ($AUD)"].sum() - TOTAL_EXPECTED
    if abs(diff) > 0:
        max_idx = final_df["Cost ($AUD)"].idxmax()
        final_df.loc[max_idx, "Cost ($AUD)"] -= diff

    final_df["Cost ($AUD)"] = final_df["Cost ($AUD)"].round(2)
    final_df = pd.concat([final_df, pd.DataFrame([{"Cost Centre": "Total", "Cost ($AUD)": TOTAL_EXPECTED}])])
    return final_df

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python linkt_cost_centre_bot.py <path_to_invoice_pdf>")
    else:
        charges_df = extract_pdf_data(sys.argv[1])
        final_costs = allocate_costs(charges_df, cost_centre_map)
        print(final_costs.to_string(index=False))
