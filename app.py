import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="Goldilocks Low Gap", layout="wide")
st.title("🏹 Goldilocks: 0.1% - 1.0% Gap Only")

# --- SETTINGS ---
stop_loss_pct = 2.0 
slippage = 0.05 

# Updated March 2026 Top 20 S&P 500
TICKERS_20 = [
    'NVDA', 'AAPL', 'GOOGL', 'MSFT', 'AMZN', 'META', 'AVGO', 'TSLA', 'BRK-B', 
    'WMT', 'LLY', 'JPM', 'XOM', 'V', 'JNJ', 'MU', 'MA', 'COST', 'ORCL', 'PLTR'
]

@st.cache_data(ttl=3600)
def get_market_data(ticker, start_date):
    try:
        df = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
        if df is None or df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['SMA50'] = ta.sma(df['Close'], length=50)
        df['SMA200'] = ta.sma(df['Close'], length=200)
        df['Prev_Close'] = df['Close'].shift(1)
        df['Gap_Pct'] = ((df['Open'] - df['Prev_Close']) / df['Prev_Close']) * 100
        return df
    except: return None

def check_global_sentinel():
    st.subheader("🌍 Global Market Sentinel")
    col1, col2 = st.columns(2)
    indices = {"Nikkei 225": "^N225", "FTSE 100": "^FTSE"}
    status = True
    for (name, sym), col in zip(indices.items(), [col1, col2]):
        idx_df = yf.download(sym, period="2d", progress=False, auto_adjust=True)
        if not idx_df.empty:
            if isinstance(idx_df.columns, pd.MultiIndex): idx_df.columns = idx_df.columns.get_level_values(0)
            is_green = idx_df['Close'].iloc[-1] > idx_df['Open'].iloc[-1]
            icon = "✅ GREEN" if is_green else "❌ RED"
            col.metric(name, icon)
            if not is_green: status = False
    return status

# --- TABS (DEFINED BEFORE USE) ---
tab1, tab2, tab3 = st.tabs(["🚀 Active Scan", "📊 Reality Audit", "💰 20-Year Growth"])

with tab1:
    global_go = check_global_sentinel()
    if st.button("🔍 Scan for Small Gaps"):
        picks = []
        for t in TICKERS_20:
            df = get_market_data(t, "2024-01-01")
            if df is not None:
                row = df.iloc[-1]
                # FILTER: Trend + Gap (0 < Gap < 1%)
                if (row['SMA50'] > row['SMA200'] and 0.1 <= row['Gap_Pct'] <= 1.0):
                    picks.append({'Ticker': t, 'Gap %': round(row['Gap_Pct'], 2)})
        if picks: st.table(pd.DataFrame(picks))
        else: st.info("No stocks found with a gap between 0.1% and 1.0%.")

with tab2:
    st.header("📋 1% Gap Audit")
    yr = st.selectbox("Year", [2026, 2025])
    mo = st.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    
    if st.button("📈 Run Audit"):
        m_idx = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(mo) + 1
        results = []
        total_p = 0.0
        for t in TICKERS_20:
            df = get_market_data(t, "2024-01-01")
            if df is not None:
                m_data = df[(df.index.year == yr) & (df.index.month == m_idx)]
                for date, row in m_data.iterrows():
                    if (row['SMA50'] > row['SMA200'] and 0.1 <= row['Gap_Pct'] <= 1.0):
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

with tab3:
    st.header("💰 20-Year Growth")
    start_val = st.number_input("Starting Capital ($)", value=1000)
    mo_return = st.slider("Monthly Return (%)", 1.0, 20.0, 5.0)
    final_val = start_val * (1 + (mo_return / 100)) ** 240
    st.metric("Future Balance", f"${final_val:,.2f}")