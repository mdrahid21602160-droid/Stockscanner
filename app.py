import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Goldilocks Auditor", layout="wide")
st.title("🏹 Goldilocks Trading Dashboard")

# --- 🟢 SIDEBAR: YEAR & MONTH SELECTION 🟢 ---
# These lines create the dropdown menus you are looking for
st.sidebar.header("🗓️ Audit Period")

current_year = datetime.now().year
# Creates the Year dropdown (2026, 2025, etc.)
selected_year = st.sidebar.selectbox("Select Year", range(current_year, 2020, -1))

months = ["January", "February", "March", "April", "May", "June", 
          "July", "August", "September", "October", "November", "December"]
# Creates the Month dropdown
selected_month_name = st.sidebar.selectbox("Select Month", months)
month_idx = months.index(selected_month_name) + 1

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Strategy Parameters")
target_pct = st.sidebar.slider("Profit Target (%)", 0.1, 1.0, 0.3, 0.1)

# --- TICKER LIST ---
TICKERS = ['AAPL', 'NVDA', 'MSFT', 'TSLA', 'AMZN', 'GOOGL', 'META', 'NFLX', 
           'AMD', 'AVGO', 'COST', 'SMCI', 'MSTR', 'QCOM', 'ORCL', 'INTU', 
           'ADBE', 'CRM', 'ISRG', 'MU']

# --- CORE AUDIT LOGIC ---
@st.cache_data(ttl=3600)
def run_historical_audit(year, month):
    audit_results = []
    # Lead-in data to stabilize EMA200
    fetch_start = f"{year-1}-01-01"
    
    for ticker in TICKERS:
        try:
            df = yf.download(ticker, start=fetch_start, progress=False, auto_adjust=True)
            if df.empty: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

            df['EMA200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
            df['ADX'] = adx_df.iloc[:, 0]
            df['Gap'] = ((df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)) * 100

            # Filter exactly for the user's selected period
            subset = df[(df.index.year == year) & (df.index.month == month)].dropna()

            for date, row in subset.iterrows():
                if date.weekday() == 4: continue # Skip Fridays
                
                if row['Close'] > row['EMA200'] and 40 <= row['RSI'] <= 60 and row['ADX'] > 25 and abs(row['Gap']) < 2.0:
                    hit = row['High'] >= (row['Open'] * (1 + (target_pct/100)))
                    audit_results.append({
                        'Date': date.strftime('%Y-%m-%d'),
                        'Ticker': ticker,
                        'Price': round(float(row['Close']), 2),
                        'RSI': round(float(row['RSI']), 1),
                        'ADX': round(float(row['ADX']), 1),
                        'Status': "✅ WIN" if hit else "❌ FAIL"
                    })
        except:
            continue
    return pd.DataFrame(audit_results)

# --- RUN BUTTON ---
if st.button("🚀 Run Historical Audit"):
    # Uses the selections from the sidebar
    with st.spinner(f"Analyzing {selected_month_name} {selected_year}..."):
        results_df = run_historical_audit(selected_year, month_idx)
        
        if not results_df.empty:
            total_signals = len(results_df)
            wins = len(results_df[results_df['Status'] == "✅ WIN"])
            win_rate = (wins / total_signals) * 100
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Signals", total_signals)
            c2.metric("Wins", wins)
            c3.metric("Win Rate", f"{win_rate:.1f}%")
            
            st.dataframe(results_df, use_container_width=True)
        else:
            st.warning(f"No signals found for {selected_month_name} {selected_year}.")