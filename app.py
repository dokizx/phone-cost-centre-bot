
import streamlit as st
import pandas as pd
import pdfplumber
import re

st.title("Phone Invoice PDF Reader Bot")

uploaded_file = st.file_uploader("Upload a Linkt/Phone invoice PDF", type=["pdf"])

def extract_phone_costs_from_pdf(pdf_file):
    charges = {}
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            lines = text.split('\n')
            for line in lines:
                match = re.search(r"(04\d{8})\D+\$?(\d+\.\d{2})", line)
                if match:
                    phone, amount = match.groups()
                    charges[phone] = float(amount)
    return charges

if uploaded_file:
    st.info("Reading PDF content...")
    charges = extract_phone_costs_from_pdf(uploaded_file)
    if charges:
        df = pd.DataFrame(charges.items(), columns=["Mobile Number", "Cost ($AUD)"])
        st.success("Extracted charges:")
        st.dataframe(df)

        csv = df.to_csv(index=False).encode()
        st.download_button("Download as CSV", csv, "extracted_charges.csv")
    else:
        st.warning("No phone numbers with charges were found.")
