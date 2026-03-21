import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Goldilocks Market Scanner", layout="wide")
st.title("🏹 Goldilocks Dashboard: Market-Filtered Audit")

# --- SIDEBAR: INPUTS ---
st.sidebar.header("🗓️ Audit Period")
current_year = datetime.now().year
selected_year = st.sidebar.selectbox("Select Year", range(current_year, 2020, -1))

months = ["January", "February", "March", "April", "May", "June", 
          "July", "August", "September", "October", "November", "December"]
selected_month_name = st.sidebar.selectbox("Select Month", months)
month_idx = months.index(selected_month_name) + 1

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Strategy Settings")
target_pct = st.sidebar.slider("Profit Target (%)", 0.1, 1.0, 0.3, 0.1)

TICKERS = ['AAPL', 'NVDA', 'MSFT', 'TSLA', 'AMZN', 'GOOGL', 'META', 'NFLX', 
           'AMD', 'AVGO', 'COST', 'SMCI', 'MSTR', 'QCOM', 'ORCL', 'INTU', 
           'ADBE', 'CRM', 'ISRG', 'MU']

# --- DATA ENGINE ---
@st.cache_data(ttl=3600)
def run_market_audit(year, month):
    audit_results = []
    fetch_start = f"{year-1}-01-01" # Lead-in for EMA stability
    
    # 1. GET MARKET FILTER (SPY)
    spy = yf.download("SPY", start=fetch_start, progress=False, auto_adjust=True)
    if isinstance(spy.columns, pd.MultiIndex): spy.columns = spy.columns.get_level_values(0)
    spy['MARKET_EMA'] = ta.ema(spy['Close'], length=200)
    spy['MARKET_BULLISH'] = spy['Close'] > spy['MARKET_EMA']
    
    # 2. SCAN TICKERS
    for ticker in TICKERS:
        try:
            df = yf.download(ticker, start=fetch_start, progress=False, auto_adjust=True)
            if df.empty: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

            # Stock Indicators
            df['EMA200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
            df['ADX'] = adx_df.iloc[:, 0]
            df['Gap'] = ((df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)) * 100

            # Merge with Market Bullish Filter
            df = df.join(spy[['MARKET_BULLISH']], how='left')

            # Filter for specific month/year
            subset = df[(df.index.year == year) & (df.index.month == month)].dropna()

            for date, row in subset.iterrows():
                if date.weekday() == 4: continue # Skip Fridays
                
                # ALL FILTERS MUST PASS:
                # Stock > EMA200 AND RSI 40-60 AND ADX > 25 AND Gap < 2.0 AND SPY > EMA200
                if row['MARKET_BULLISH'] and row['Close'] > row['EMA200'] and \
                   40 <= row['RSI'] <= 60 and row['ADX'] > 25 and abs(row['Gap']) < 2.0:
                    
                    hit = row['High'] >= (row['Open'] * (1 + (target_pct/100)))
                    audit_results.append({
                        'Date': date.strftime('%Y-%m-%d'),
                        'Ticker': ticker,
                        'Price': round(float(row['Close']), 2),
                        'Status': "✅ WIN" if hit else "❌ FAIL"
                    })
        except:
            continue
    return pd.DataFrame(audit_results)

# --- EXECUTION ---
if st.button("🚀 Run Market-Filtered Audit"):
    with st.spinner(f"Scanning for 'Bullish Market' signals in {selected_month_name}..."):
        results_df = run_market_audit(selected_year, month_idx)
        
        if not results_df.empty:
            wins = len(results_df[results_df['Status'] == "✅ WIN"])
            win_rate = (wins / len(results_df)) * 100
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Signals Found", len(results_df))
            c2.metric("Wins", wins)
            c3.metric("Win Rate", f"{win_rate:.1f}%")
            
            st.dataframe(results_df, use_container_width=True)
        else:
            st.warning("No signals found. Market might be Bearish (SPY < 200 EMA) or too choppy.")