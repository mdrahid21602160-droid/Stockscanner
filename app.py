import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import datetime

# --- Page Configuration ---
st.set_page_config(page_title="Goldilocks Audit Dashboard", layout="wide")
st.title("🏹 Goldilocks: Monthly & Yearly Audit")

# --- Sidebar Inputs ---
st.sidebar.header("⚙️ Audit Settings")
ticker = st.sidebar.text_input("Enter Ticker", value="NVDA").upper()
profit_target_pct = st.sidebar.number_input("Profit Target (%)", value=0.5) / 100
stop_loss_pct = st.sidebar.number_input("Stop Loss (%)", value=1.5) / 100

# Year and Month Selection
current_year = datetime.datetime.now().year
selected_year = st.sidebar.selectbox("Select Year", range(current_year, 2015, -1))

months = ["January", "February", "March", "April", "May", "June", 
          "July", "August", "September", "October", "November", "December"]
selected_month_name = st.sidebar.selectbox("Select Month", months)
month_index = months.index(selected_month_name) + 1

# --- Data Engine ---
@st.cache_data
def get_audit_data(symbol):
    # Fetching extra data to ensure indicators (like EMA200) are accurate
    data = yf.download(symbol, start="2015-01-01")
    
    # Calculate Indicators
    data['EMA200'] = ta.ema(data['Close'], length=200)
    data['RSI'] = ta.rsi(data['Close'], length=14)
    adx_df = ta.adx(data['High'], data['Low'], data['Close'], length=14)
    data['ADX'] = adx_df['ADX_14']
    
    # Define Entry Signal (Goldilocks Zone)
    data['Signal'] = (data['Close'] > data['EMA200']) & \
                     (data['RSI'].between(40, 60)) & \
                     (data['ADX'] > 25)
    return data

# --- Processing ---
df = get_audit_data(ticker)

# Filter by selected Year and Month
audit_df = df[(df.index.year == selected_year) & (df.index.month == month_index)].copy()

# --- Audit Logic ---
def run_trade_audit(row_index, full_df):
    entry_price = full_df.iloc[row_index]['Close']
    target = entry_price * (1 + profit_target_pct)
    stop = entry_price * (1 - stop_loss_pct)
    
    # Check next 5 days for outcome
    future_data = full_df.iloc[row_index + 1 : row_index + 6]
    for _, day in future_data.iterrows():
        if day['High'] >= target: return "WIN"
        if day['Low'] <= stop: return "LOSS"
    return "EXPIRED"

if not audit_df.empty:
    # Identify signals and run audit
    signals_indices = [df.index.get_loc(idx) for idx in audit_df[audit_df['Signal']].index]
    results = [run_trade_audit(idx, df) for idx in signals_indices]
    
    # --- UI Display ---
    col1, col2, col3 = st.columns(3)
    win_count = results.count("WIN")
    total_trades = len(results)
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
    
    col1.metric("Total Signals", total_trades)
    col2.metric("Wins", win_count)
    col3.metric("Win Rate", f"{win_rate:.1f}%")
    
    st.subheader(f"Detailed Logs: {selected_month_name} {selected_year}")
    st.write(audit_df[['Close', 'EMA200', 'RSI', 'ADX', 'Signal']])
else:
    st.warning(f"No data available for {selected_month_name} {selected_year}")