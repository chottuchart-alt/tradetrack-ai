import streamlit as st
from PIL import Image
import pytesseract
import re
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os

st.set_page_config(page_title="AI Trading Journal PRO", layout="centered")

st.title("📊 AI Trading Screenshot Analyzer PRO")

# -----------------------------
# OCR FUNCTION
# -----------------------------
def extract_data(image):
    text = pytesseract.image_to_string(image)
    text_lower = text.lower()

    # Detect Platform
    platform = "Unknown"
    if "metaquotes" in text_lower or "mt5" in text_lower:
        platform = "MT5"
    elif "mt4" in text_lower:
        platform = "MT4"

    # Detect Symbol
    symbol_match = re.search(r'(XAUUSD|EURUSD|BTCUSD|GBPUSD|USDJPY)', text)
    symbol = symbol_match.group(1) if symbol_match else "Unknown"

    # Detect Lot Size
    lot_match = re.search(r'0\.\d+', text)
    lot = lot_match.group() if lot_match else "0.01"

    # Detect Order Type
    order = "Unknown"
    if "buy" in text_lower:
        order = "Buy"
    elif "sell" in text_lower:
        order = "Sell"

    # Detect Today P/L (Bottom Most Value)
    numbers = re.findall(r'[-+]?\d+[.,]?\d*', text)
    today_pl = numbers[-1] if numbers else "0"

    return {
        "platform": platform,
        "symbol": symbol,
        "lot": lot,
        "order": order,
        "today_pl": today_pl
    }

# -----------------------------
# AI Insight Generator
# -----------------------------
def generate_insight(order, pl):
    try:
        pl_value = float(pl.replace(",", ""))
    except:
        pl_value = 0

    if pl_value > 0:
        return "Strong Trade Execution 👍 Trend Followed Properly"
    elif pl_value < 0:
        return "Loss Trade ⚠ Check Entry Confirmation"
    else:
        return "Break Even / Minimal Movement"

# -----------------------------
# File Storage
# -----------------------------
FILE_NAME = "trade_data.csv"

def save_trade(data):
    df_new = pd.DataFrame([{
        "date": datetime.now().strftime("%d-%m-%Y"),
        "platform": data["platform"],
        "symbol": data["symbol"],
        "lot": data["lot"],
        "order": data["order"],
        "today_pl": float(data["today_pl"].replace(",", ""))
    }])

    if os.path.exists(FILE_NAME):
        df_old = pd.read_csv(FILE_NAME)
        df = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df = df_new

    df.to_csv(FILE_NAME, index=False)

def load_data():
    if os.path.exists(FILE_NAME):
        return pd.read_csv(FILE_NAME)
    return pd.DataFrame()

# -----------------------------
# Upload Section
# -----------------------------
uploaded_file = st.file_uploader("📤 Upload Trading Screenshot", type=["png", "jpg", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, use_column_width=True)

    data = extract_data(image)
    insight = generate_insight(data["order"], data["today_pl"])

    st.markdown("---")
    st.subheader("📌 Trade Analysis Result")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("💰 Today's P/L", f"₹ {data['today_pl']}")
        st.write("📈 Symbol:", data["symbol"])
        st.write("📊 Lot Size:", data["lot"])

    with col2:
        st.write("🖥 Platform:", data["platform"])
        st.write("📝 Order:", data["order"])
        st.write("🧠 Insight:", insight)

    if st.button("💾 Save Trade"):
        save_trade(data)
        st.success("Trade Saved Successfully!")

# -----------------------------
# Monthly Dashboard
# -----------------------------
st.markdown("---")
st.subheader("📅 Monthly Performance")

df = load_data()

if not df.empty:
    total_profit = df["today_pl"].sum()
    total_trades = len(df)
    win_trades = len(df[df["today_pl"] > 0])
    loss_trades = len(df[df["today_pl"] < 0])

    st.metric("📈 Total P/L", f"₹ {round(total_profit,2)}")
    st.write("Total Trades:", total_trades)
    st.write("Winning Trades:", win_trades)
    st.write("Losing Trades:", loss_trades)

    fig = plt.figure()
    df["today_pl"].cumsum().plot()
    plt.title("Equity Growth Curve")
    plt.xlabel("Trades")
    plt.ylabel("Profit")
    st.pyplot(fig)

else:
    st.info("No trades saved yet.")
