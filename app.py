import streamlit as st
import easyocr
from PIL import Image
import re
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

st.set_page_config(page_title="TradeTrack AI", page_icon="📊", layout="centered")

st.title("📊 TradeTrack AI - Cloud Edition")
st.write("Upload trading screenshot → Auto detect Profit / Loss → Monthly Report")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("trades.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS trades (
    date TEXT,
    amount REAL,
    type TEXT,
    platform TEXT
)
""")
conn.commit()

# ---------------- OCR SETUP ----------------
@st.cache_resource
def load_reader():
    return easyocr.Reader(['en'], gpu=False)

reader = load_reader()

def extract_data_from_image(image):
    image_np = np.array(image)
    results = reader.readtext(image_np, detail=0)
    text = " ".join(results)

    # Detect amount
    amount_match = re.search(r"[-+]?\d+\.\d+", text)
    amount = float(amount_match.group()) if amount_match else 0.0

    trade_type = "Profit" if amount > 0 else "Loss"

    # Detect date
    date_match = re.search(r"\d{2}/\d{2}/\d{4}", text)
    date = date_match.group() if date_match else datetime.today().strftime("%d/%m/%Y")

    # Detect platform
    if "MT4" in text:
        platform = "MT4"
    elif "MT5" in text:
        platform = "MT5"
    elif "Binance" in text:
        platform = "Binance"
    else:
        platform = "Unknown"

    return amount, trade_type, date, platform

# ---------------- FILE UPLOAD ----------------
uploaded_file = st.file_uploader("Upload Screenshot", type=["png", "jpg", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Screenshot", use_column_width=True)

    with st.spinner("Analyzing screenshot..."):
        amount, trade_type, date, platform = extract_data_from_image(image)

    st.success(f"Detected: {trade_type} ₹{amount}")
    st.info(f"Date: {date} | Platform: {platform}")

    if st.button("Save Trade"):
        c.execute("INSERT INTO trades VALUES (?, ?, ?, ?)", (date, amount, trade_type, platform))
        conn.commit()
        st.success("Trade Saved Successfully")

# ---------------- DASHBOARD ----------------
st.subheader("📈 Monthly Summary")

df = pd.read_sql_query("SELECT * FROM trades", conn)

if not df.empty:
    df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y")
    df["month"] = df["date"].dt.to_period("M")

    monthly = df.groupby("month")["amount"].sum()

    total = df["amount"].sum()
    wins = len(df[df["amount"] > 0])
    losses = len(df[df["amount"] < 0])
    winrate = (wins / len(df)) * 100

    st.metric("Total P/L", f"₹{round(total,2)}")
    st.metric("Win Rate", f"{round(winrate,2)}%")

    fig, ax = plt.subplots()
    monthly.plot(kind="bar", ax=ax)
    ax.set_title("Monthly Profit/Loss")
    st.pyplot(fig)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download Report CSV", csv, "trade_report.csv", "text/csv")

else:
    st.warning("No trades saved yet.")
