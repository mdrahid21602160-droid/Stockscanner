import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Goldilocks Scanner", layout="wide")
st.title("🏹 Goldilocks Trading Dashboard")
st.subheader("High-Probability Trend Scanner (Mon-Thu)")

# --- SIDEBAR SETTINGS ---
st.sidebar.header("Strategy Parameters")
target_pct = st.sidebar.slider("Profit Target (%)", 0.1, 1.0, 0.3, 0.1)
stop_loss_pct = st.sidebar.slider("Stop Loss (%)", 0.5, 3.0, 1.5, 0.1)
lookback_days = st.sidebar.selectbox("Audit Lookback", [7, 14, 20, 30], index=2)

TICKERS = ['AAPL', 'NVDA', 'MSFT', 'TSLA', 'AMZN', 'GOOGL', 'META', 'NFLX', 
           'AMD', 'AVGO', 'COST', 'SMCI', 'MSTR', 'QCOM', 'ORCL', 'INTU', 
           'ADBE', 'CRM', 'ISRG', 'MU']

# --- CORE LOGIC ---
@st.cache_data(ttl=3600) # Cache data for 1 hour to save API hits
def run_audit(days):
    end_date = datetime.now()
    start_audit = end_date - timedelta(days=days)
    data_start = "2024-01-01"
    
    audit_results = []
    
    for ticker in TICKERS:
        df = yf.download(ticker, start=data_start, end=end_date, progress=False, auto_adjust=True)
        if df.empty: continue
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        df['EMA200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
        df['ADX'] = adx_df['ADX_14']
        df['Gap'] = ((df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)) * 100

        subset = df.loc[start_audit:].dropna()

        for date, row in subset.iterrows():
            if date.weekday() == 4: continue # Skip Fridays
            
            # Filters
            is_trending = row['Close'] > row['EMA200']
            is_rsi_valid = 40 <= row['RSI'] <= 60
            is_strong = row['ADX'] > 25
            is_safe_gap = row['Gap'] < 2.0

            if is_trending and is_rsi_valid and is_strong and is_safe_gap:
                hit = row['High'] >= (row['Open'] * (1 + (target_pct/100)))
                audit_results.append({
                    'Date': date.strftime('%Y-%m-%d'),
                    'Ticker': ticker,
                    'Price': f"${row['Close']:.2f}",
                    'RSI': round(row['RSI'], 1),
                    'ADX': round(row['ADX'], 1),
                    'Status': "✅ WIN" if hit else "❌ FAIL"
                })
    return pd.DataFrame(audit_results)

# --- UI EXECUTION ---
if st.button("🚀 Run Scanner / Audit"):
    with st.spinner("Analyzing the tape..."):
        results_df = run_audit(lookback_days)
        
        if not results_df.empty:
            # Metrics
            total_signals = len(results_df)
            wins = len(results_df[results_df['Status'] == "✅ WIN"])
            win_rate = (wins / total_signals) * 100
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Signals", total_signals)
            col2.metric("Wins", wins)
            col3.metric("Win Rate", f"{win_rate:.1f}%")
            
            # Data Table
            st.dataframe(results_df, use_container_width=True)
            
            # Download Button
            csv = results_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Report as CSV", data=csv, file_name="goldilocks_audit.csv")
        else:
            st.warning("No signals found for this period.")