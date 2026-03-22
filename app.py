import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="Goldilocks Gap Up", layout="wide")
st.title("🏹 Goldilocks: Gap Up + Buy at Open")

# --- PARAMETERS ---
st.sidebar.header("⚙️ Strategy Filters")
min_gap = st.sidebar.slider("Min Gap Up (%)", 0.0, 1.0, 0.5, 0.1)
max_gap = st.sidebar.slider("Max Gap Up (%)", 2.0, 5.0, 3.0, 0.5)
stop_loss_pct = 2.0 
slippage = 0.05 

# --- TOP 20 S&P 500 (March 2026) ---
TICKERS_20 = [
    'NVDA', 'AAPL', 'MSFT', 'AMZN', 'GOOGL', 'GOOG', 'META', 'AVGO', 'TSLA', 'BRK-B',
    'WMT', 'LLY', 'JPM', 'XOM', 'V', 'JNJ', 'MU', 'MA', 'COST', 'ORCL'
]

@st.cache_data(ttl=3600)
def get_market_data(ticker, start_date):
    try:
        df = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
        if df is None or df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['SMA50'] = ta.sma(df['Close'], length=50)
        df['SMA200'] = ta.sma(df['Close'], length=200)
        # GAP UP = (Today's Open - Yesterday's Close) / Yesterday's Close
        df['Prev_Close'] = df['Close'].shift(1)
        df['Gap_Pct'] = ((df['Open'] - df['Prev_Close']) / df['Prev_Close']) * 100
        return df
    except: return None

# [Logic for Global Sentinel Tab 1 remains the same]
# --- TAB 1 & 2 UPDATED FOR GAP LOGIC ---

tab1, tab2, tab3 = st.tabs(["🚀 Global Scan", "📊 Gap Audit", "💰 20-Year Growth"])

with tab1:
    if st.button("🔍 Scan for Gap Ups"):
        picks = []
        for t in TICKERS_20:
            df = get_market_data(t, "2024-01-01")
            if df is not None:
                row = df.iloc[-1]
                # FILTER: Trend (50>200) AND Gap Up within range
                if (row['SMA50'] > row['SMA200'] and min_gap <= row['Gap_Pct'] <= max_gap):
                    picks.append({'Ticker': t, 'Gap %': round(row['Gap_Pct'], 2)})
        if picks: st.table(pd.DataFrame(picks))
        else: st.info("No Gap Up setups found in the Top 20.")

with tab2:
    st.header("📋 Audit: Gap Up Entry at Open")
    yr = st.selectbox("Year", [2026, 2025])
    mo = st.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    
    if st.button("📈 Run Gap Audit"):
        m_idx = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(mo) + 1
        results = []
        total_p = 0.0
        for t in TICKERS_20:
            df = get_market_data(t, "2024-01-01")
            if df is not None:
                m_data = df[(df.index.year == yr) & (df.index.month == m_idx)]
                for date, row in m_data.iterrows():
                    # Check Signal: Trend + Gap Up
                    if (row['SMA50'] > row['SMA200'] and min_gap <= row['Gap_Pct'] <= max_gap):
                        hit_stop = row['Low'] <= (row['Open'] * (1 - (stop_loss_pct/100)))
                        if hit_stop:
                            p = -(stop_loss_pct + slippage)
                            status = "❌ STOP OUT"
                        else:
                            p = (((row['Close'] - row['Open']) / row['Open']) * 100) - slippage
                            status = "💰 CLOSE EXIT"
                        total_p += p
                        results.append({'Date': date.date(), 'Ticker': t, 'Gap %': round(row['Gap_Pct'],2), 'Result %': round(p, 2)})
        
        if results:
            st.metric("Total Monthly Profit", f"{total_p:.2f}%")
            st.dataframe(pd.DataFrame(results))