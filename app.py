import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import datetime

# --- Page Configuration ---
st.set_page_config(page_title="Goldilocks Audit Dashboard", layout="wide")
st.title("🏹 Goldilocks Trading Dashboard")
st.subheader("High-Probability Trend Scanner & Audit")

# --- Sidebar Settings ---
st.sidebar.header("⚙️ Strategy Parameters")
ticker = st.sidebar.text_input("Ticker Symbol", value="NVDA").upper()
target_pct = st.sidebar.slider("Profit Target (%)", 0.1, 2.0, 0.5) / 100
stop_loss_pct = st.sidebar.slider("Stop Loss (%)", 0.5, 5.0, 1.5) / 100

st.sidebar.markdown("---")
st.sidebar.header("🗓️ Audit Selection")
current_year = datetime.datetime.now().year
selected_year = st.sidebar.selectbox("Select Year", range(current_year, 2018, -1))

months = ["January", "February", "March", "April", "May", "June", 
          "July", "August", "September", "October", "November", "December"]
selected_month_name = st.sidebar.selectbox("Select Month", months)
month_index = months.index(selected_month_name) + 1

# --- Data Engine ---
@st.cache_data
def get_audit_data(symbol):
    # Fetch 2 years of data to ensure indicators are stable
    data = yf.download(symbol, period="2y")
    if data.empty:
        return pd.DataFrame()
    
    # Calculate Indicators
    data['EMA200'] = ta.ema(data['Close'], length=200)
    data['RSI'] = ta.rsi(data['Close'], length=14)
    
    # Robust ADX Calculation (Fixes the error in your screenshot)
    adx_df = ta.adx(data['High'], data['Low'], data['Close'], length=14)
    data['ADX'] = adx_df.iloc[:, 0] # Always takes the first column of ADX results
    
    # Define Signal Zone
    data['Signal'] = (data['Close'] > data['EMA200']) & \
                     (data['RSI'].between(40, 60)) & \
                     (data['ADX'] > 25)
    return data

# --- Execution ---
if st.button("🚀 Run Scanner / Audit"):
    df = get_audit_data(ticker)
    
    if not df.empty:
        # Filter for the selected audit period
        audit_df = df[(df.index.year == selected_year) & (df.index.month == month_index)].copy()
        
        if not audit_df.empty:
            # Count Signals
            total_signals = audit_df['Signal'].sum()
            
            # Display Results
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Signals", int(total_signals))
            
            # Simple Win Rate Logic for Audit
            # (Checks if next day's high is > 0.5% target)
            audit_df['Result'] = "Wait"
            win_count = 0
            for i in range(len(audit_df) - 1):
                if audit_df['Signal'].iloc[i]:
                    entry = audit_df['Close'].iloc[i]
                    nxt_high = audit_df['High'].iloc[i+1]
                    if nxt_high >= entry * (1 + target_pct):
                        win_count += 1

            win_rate = (win_count / total_signals * 100) if total_signals > 0 else 0
            col2.metric("Wins", win_count)
            col3.metric("Win Rate", f"{win_rate:.1f}%")
            
            st.markdown("---")
            st.subheader(f"Data Log for {selected_month_name} {selected_year}")
            st.dataframe(audit_df[['Close', 'RSI', 'ADX', 'Signal']].tail(20))
        else:
            st.warning(f"No data found for {selected_month_name} {selected_year}. The market might have been closed or data is unavailable.")
    else:
        st.error("Ticker not found. Please check the symbol (e.g., NVDA, MSFT).")