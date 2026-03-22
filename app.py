import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="Goldilocks Pure Trend", layout="wide")
st.title("🏹 Goldilocks: 50SMA > 200SMA + Global Green")

# --- RISK PARAMETERS ---
stop_loss_pct = 2.0  # Your 2.0% Hard Stop
slippage = 0.05 

# --- UPDATED TOP 20 S&P 500 (March 2026) ---
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
        
        # CORE FILTERS
        df['SMA50'] = ta.sma(df['Close'], length=50)
        df['SMA200'] = ta.sma(df['Close'], length=200)
        df['Is_Green'] = df['Close'] > df['Open']
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

tab1, tab2 = st.tabs(["🚀 Global Scan", "📊 Reality Audit"])

with tab1:
    global_go = check_global_sentinel()
    
    if st.button("🔍 Scan Top 20"):
        if not global_go:
            st.warning("⚠️ Execution blocked: Global indices are not Green.")
        else:
            picks = []
            for t in TICKERS_20:
                df = get_market_data(t, "2024-01-01")
                if df is not None:
                    row = df.iloc[-1]
                    # THE NEW LOGIC: Close > 50SMA > 200SMA + Today is Green
                    if (row['Close'] > row['SMA50'] > row['SMA200'] and row['Is_Green']):
                        picks.append({'Ticker': t, 'Price': round(row['Close'], 2)})
            
            if picks: st.success(f"Found {len(picks)} setups."); st.table(pd.DataFrame(picks))
            else: st.info("No stocks currently fit the 50 > 200 trend profile.")

with tab2:
    st.header("📋 Audit: Uncapped Profit / 2% Stop")
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
                    # Check signal: Trend alignment + Green day
                    if (row['Close'] > row['SMA50'] > row['SMA200'] and row['Is_Green']):
                        hit_stop = row['Low'] <= (row['Open'] * (1 - (stop_loss_pct/100)))
                        
                        if hit_stop:
                            p, status = -(stop_loss_pct + slippage), "❌ STOP (-2%)"
                        else:
                            p = (((row['Close'] - row['Open']) / row['Open']) * 100) - slippage
                            status = f"💰 CLOSE ({p:.2f}%)"
                        
                        total_p += p
                        results.append({'Date': date.date(), 'Ticker': t, 'Status': status, 'Result %': round(p, 2)})
        
        if results:
            st.metric("Monthly Performance", f"{total_p:.2f}%")
            st.dataframe(pd.DataFrame(results), use_container_width=True)