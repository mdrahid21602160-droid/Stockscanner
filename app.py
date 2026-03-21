import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import datetime

# --- Page Configuration ---
st.set_page_config(page_title="Goldilocks Trading Dashboard", layout="wide")
st.title("🏹 Goldilocks Trading Dashboard")
st.markdown("---")

# --- Sidebar: Strategy & Audit Settings ---
st.sidebar.header("⚙️ Parameters")
ticker = st.sidebar.text_input("Ticker Symbol", value="NVDA").upper()
target_pct = st.sidebar.slider("Profit Target (%)", 0.1, 2.0, 0.5) / 100
stop_loss_pct = st.sidebar.slider("Stop Loss (%)", 0.5, 5.0, 1.5) / 100

st.sidebar.markdown("---")
st.sidebar.header("🗓️ Select Audit Period")
current_year = datetime.datetime.now().year
selected_year = st.sidebar.selectbox("Year", range(current_year, 2018, -1))

months = ["January", "February", "March", "April", "May", "June", 
          "July", "August", "September", "October", "November", "December"]
selected_month_name = st.sidebar.selectbox("Month", months)
month_idx = months.index(selected_month_name) + 1

# --- Data Engine ---
@st.cache_data
def get_clean_data(symbol):
    # Fetch data (Download 2+ years for stable EMA200/ADX)
    raw_data = yf.download(symbol, period="max", interval="1d", auto_adjust=True)
    
    if raw_data.empty:
        return pd.DataFrame()

    # FIX: Flatten Multi-Index columns (Fixes the error in your 13:05 screenshot)
    if isinstance(raw_data.columns, pd.MultiIndex):
        raw_data.columns = raw_data.columns.get_level_values(0)

    # Calculate Indicators
    df = raw_data.copy()
    df['EMA200'] = ta.ema(df['Close'], length=200)
    df['RSI'] = ta.rsi(df['Close'], length=14)
    
    # Robust ADX naming fix
    adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
    if adx_df is not None:
        df['ADX'] = adx_df.iloc[:, 0] # Grab first column (ADX_14)
    
    # Define "Goldilocks" Signal
    df['Signal'] = (df['Close'] > df['EMA200']) & \
                   (df['RSI'].between(40, 60)) & \
                   (df['ADX'] > 25)
    return df

# --- Main Execution ---
if st.button("🚀 Run Analysis"):
    with st.spinner(f"Fetching data for {ticker}..."):
        df = get_clean_data(ticker)
    
    if not df.empty:
        # Filter data for the specific Year and Month
        audit_df = df[(df.index.year == selected_year) & (df.index.month == month_idx)].copy()
        
        if not audit_df.empty:
            # Audit Logic: Check if price hits 0.5% target in the following days
            win_count = 0
            signals_found = audit_df[audit_df['Signal']]
            
            for i in range(len(audit_df) - 1):
                if audit_df['Signal'].iloc[i]:
                    entry_price = audit_df['Close'].iloc[i]
                    target_price = entry_price * (1 + target_pct)
                    # Check next 2 days for the target (Aggressive Day Trading)
                    future_slice = df.loc[audit_df.index[i]:].iloc[1:3] 
                    if not future_slice.empty and future_slice['High'].max() >= target_price:
                        win_count += 1

            total_signals = len(signals_found)
            win_rate = (win_count / total_signals * 100) if total_signals > 0 else 0

            # --- Results Display ---
            st.success(f"Audit Complete for {selected_month_name} {selected_year}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Signals Detected", total_signals)
            c2.metric("Target Hits (0.5%)", win_count)
            c3.metric("Win Rate", f"{win_rate:.1f}%")

            st.markdown("---")
            st.subheader("📋 Daily Data Log")
            # Format the dataframe for easy reading
            display_df = audit_df[['Close', 'RSI', 'ADX', 'Signal']].copy()
            display_df.index = display_df.index.strftime('%Y-%m-%d')
            st.dataframe(display_df.style.highlight_max(subset=['Signal'], color='#125e1c'), use_container_width=True)
            
        else:
            st.warning(f"No market data found for {selected_month_name} {selected_year}.")
    else:
        st.error("Invalid Ticker. Please check the symbol and try again.")