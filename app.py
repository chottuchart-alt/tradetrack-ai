import streamlit as st
import easyocr
from PIL import Image
import re
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

st.set_page_config(page_title="TradeTrack AI PRO", page_icon="📊", layout="wide")

# ---------------- STYLE ----------------
st.markdown("""
<style>
body { background-color: #0e1117; color: white; }
.block-container { padding-top: 2rem; }
</style>
""", unsafe_allow_html=True)

st.title("📊 TradeTrack AI PRO")
st.caption("Advanced Screenshot Analyzer for Traders")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("trades.db", check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS trades (
    date TEXT,
    amount REAL,
    type TEXT,
    lot TEXT,
    symbol TEXT,
    order_type TEXT,
    platform TEXT
)
""")
conn.commit()

# ---------------- OCR LOAD ----------------
@st.cache_resource
def load_reader():
    return easyocr.Reader(['en'], gpu=False)

reader = load_reader()

# ---------------- EXTRACT FUNCTION ----------------
def extract_data(image):
    image_np = np.array(image)
    results = reader.readtext(image_np, detail=0)
    text = " ".join(results)

    # Amount
    amount_match = re.search(r"[-+]?\d+\.\d+", text)
    amount = float(amount_match.group()) if amount_match else 0.0
    trade_type = "Profit" if amount > 0 else "Loss"

    # Lot size
    lot_match = re.search(r"\b0\.\d+\b|\b[1-9]\d*\.\d+\b", text)
    lot = lot_match.group() if lot_match else "Unknown"

    # Symbol
    symbol_match = re.search(r"\b[A-Z]{3,6}\b", text)
    symbol = symbol_match.group() if symbol_match else "Unknown"

    # Order type
    if "buy" in text.lower():
        order = "Buy"
    elif "sell" in text.lower():
        order = "Sell"
    else:
        order = "Unknown"

    # Date
    date_match = re.search(r"\d{2}/\d{2}/\d{4}", text)
    date = date_match.group() if date_match else datetime.today().strftime("%d/%m/%Y")

    # Platform
    if "MT4" in text:
        platform = "MT4"
    elif "MT5" in text:
        platform = "MT5"
    elif "Binance" in text:
        platform = "Binance"
    else:
        platform = "Unknown"

    # Smart insight
    if order == "Buy" and trade_type == "Profit":
        insight = "Strong Uptrend Confirmation"
    elif order == "Sell" and trade_type == "Profit":
        insight = "Strong Downtrend Confirmation"
    else:
        insight = "Volatile / Weak Structure"

    return {
        "amount": amount,
        "type": trade_type,
        "lot": lot,
        "symbol": symbol,
        "order": order,
        "date": date,
        "platform": platform,
        "insight": insight
    }

# ---------------- SIDEBAR ----------------
st.sidebar.header("Upload Trade Screenshot")
file = st.sidebar.file_uploader("Upload Image", type=["png","jpg","jpeg"])

if file:
    image = Image.open(file)
    st.sidebar.image(image, use_column_width=True)

    with st.spinner("Analyzing Screenshot..."):
        data = extract_data(image)

    st.sidebar.success(f"{data['type']} ₹{data['amount']}")
    st.sidebar.write(f"Lot Size: {data['lot']}")
    st.sidebar.write(f"Symbol: {data['symbol']}")
    st.sidebar.write(f"Order: {data['order']}")
    st.sidebar.write(f"Platform: {data['platform']}")
    st.sidebar.write(f"Insight: {data['insight']}")

    if st.sidebar.button("Save Trade"):
        c.execute("INSERT INTO trades VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (data["date"], data["amount"], data["type"],
                   data["lot"], data["symbol"], data["order"], data["platform"]))
        conn.commit()
        st.sidebar.success("Trade Saved!")

# ---------------- LOAD DATA ----------------
df = pd.read_sql_query("SELECT * FROM trades", conn)

if not df.empty:
    df["date"] = pd.to_datetime(df["date"], format="%d/%m/%Y")
    df = df.sort_values("date")

    total = df["amount"].sum()
    wins = len(df[df["amount"] > 0])
    losses = len(df[df["amount"] < 0])
    winrate = (wins / len(df)) * 100
    equity = df["amount"].cumsum()
    tax_estimate = total * 0.30 if total > 0 else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total P/L", f"₹{round(total,2)}")
    col2.metric("Wins", wins)
    col3.metric("Losses", losses)
    col4.metric("Win Rate", f"{round(winrate,2)}%")
    col5.metric("Est. Tax (30%)", f"₹{round(tax_estimate,2)}")

    st.markdown("---")

    # Filter
    platforms = st.multiselect("Filter Platform", df["platform"].unique(), default=df["platform"].unique())
    filtered = df[df["platform"].isin(platforms)]

    # Equity Curve
    st.subheader("📈 Equity Curve")
    fig1, ax1 = plt.subplots()
    ax1.plot(filtered["date"], filtered["amount"].cumsum())
    ax1.set_title("Equity Growth")
    st.pyplot(fig1)

    # Monthly Performance
    st.subheader("📊 Monthly Performance")
    filtered["month"] = filtered["date"].dt.to_period("M")
    monthly = filtered.groupby("month")["amount"].sum()

    fig2, ax2 = plt.subplots()
    monthly.plot(kind="bar", ax=ax2)
    st.pyplot(fig2)

    # History Table
    st.subheader("📋 Trade History")
    st.dataframe(filtered)

    # CSV
    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV Report", csv, "trade_report.csv", "text/csv")

    if st.button("Delete All Trades"):
        c.execute("DELETE FROM trades")
        conn.commit()
        st.warning("All trades deleted. Refresh page.")

else:
    st.info("No trades uploaded yet.")
