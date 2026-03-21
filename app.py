import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Goldilocks Audit", layout="wide")
st.title("🏹 Goldilocks Trading Dashboard")
st.subheader("Historical Month/Year Audit (Mon-Thu)")

# --- SIDEBAR SETTINGS ---
st.sidebar.header("Strategy Parameters")
target_pct = st.sidebar.slider("Profit Target (%)", 0.1, 1.0, 0.3, 0.1)
stop_loss_pct = st.sidebar.slider("Stop Loss (%)", 0.5, 3.0, 1.5, 0.1)

st.sidebar.markdown("---")
st.sidebar.header("🗓️ Select Audit Period")
current_year = datetime.now().year
selected_year = st.sidebar.selectbox("Year", range(current_year, 2020, -1))

months = ["January", "February", "March", "April", "May", "June", 
          "July", "August", "September", "October", "November", "December"]
selected_month_name = st.sidebar.selectbox("Month", months)
month_idx = months.index(selected_month_name) + 1

TICKERS = ['AAPL', 'NVDA', 'MSFT', 'TSLA', 'AMZN', 'GOOGL', 'META', 'NFLX', 
           'AMD', 'AVGO', 'COST', 'SMCI', 'MSTR', 'QCOM', 'ORCL', 'INTU', 
           'ADBE', 'CRM', 'ISRG', 'MU']

# --- CORE LOGIC ---
@st.cache_data(ttl=3600)
def run_historical_audit(year, month):
    audit_results = []
    # Start data fetch earlier to stabilize EMA200
    fetch_start = f"{year-1}-01-01"
    fetch_end = datetime.now().strftime('%Y-%m-%d')
    
    for ticker in TICKERS:
        try:
            df = yf.download(ticker, start=fetch_start, end=fetch_end, progress=False, auto_adjust=True)
            if df.empty: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

            # Technical Indicators
            df['EMA200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
            df['ADX'] = adx_df.iloc[:, 0]
            df['Gap'] = ((df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)) * 100

            # Filter for specific Year and Month
            subset = df[(df.index.year == year) & (df.index.month == month)].dropna()

            for date, row in subset.iterrows():
                if date.weekday() == 4: continue # Skip Fridays
                
                # The "Goldilocks" Filters
                is_trending = row['Close'] > row['EMA200']
                is_rsi_valid = 40 <= row['RSI'] <= 60
                is_strong = row['ADX'] > 25
                is_safe_gap = abs(row['Gap']) < 2.0

                if is_trending and is_rsi_valid and is_strong and is_safe_gap:
                    # Calculate if Open-to-High hits your target
                    hit = row['High'] >= (row['Open'] * (1 + (target_pct/100)))
                    audit_results.append({
                        'Date': date.strftime('%Y-%m-%d'),
                        'Ticker': ticker,
                        'Price': f"${row['Close']:.2f}",
                        'RSI': round(row['RSI'], 1),
                        'ADX': round(row['ADX'], 1),
                        'Status': "✅ WIN" if hit else "❌ FAIL"
                    })
        except:
            continue
    return pd.DataFrame(audit_results)

# --- UI EXECUTION ---
if st.button("🚀 Run Historical Audit"):
    with st.spinner(f"Analyzing {selected_month_name} {selected_year}..."):
        results_df = run_historical_audit(selected_year, month_idx)
        
        if not results_df.empty:
            total_signals = len(results_df)
            wins = len(results_df[results_df['Status'] == "✅ WIN"])
            win_rate = (wins / total_signals) * 100
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Signals", total_signals)
            c2.metric("Wins", wins)
            c3.metric("Win Rate", f"{win_rate:.1f}%")
            
            st.dataframe(results_df, use_container_width=True)
            
            csv = results_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Audit CSV", data=csv, file_name=f"audit_{selected_year}_{month_idx}.csv")
        else:
            st.warning(f"No signals found for {selected_month_name} {selected_year}.")