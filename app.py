import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="Goldilocks Top 20: Uncapped", layout="wide")
st.title("🏹 Goldilocks: Let Profit Run (Sell at Close)")

# --- PARAMETERS ---
st.sidebar.header("⚙️ Risk Management")
stop_loss_pct = 2.0  # Hard Stop
vol_threshold = st.sidebar.slider("Min RVOL", 1.0, 2.5, 1.1, 0.1)
slippage = 0.05 

# --- UPDATED TOP 20 S&P 500 (March 2026 Weights) ---
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
        
        df['EMA200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
        df['ADX'] = adx_df.iloc[:, 0] if adx_df is not None else 0
        df['Avg_Vol'] = df['Volume'].rolling(window=10).mean()
        df['RVOL'] = df['Volume'] / df['Avg_Vol']
        df['Is_Green'] = df['Close'] > df['Open']
        return df
    except: return None

tab1, tab2 = st.tabs(["🚀 Active Scan", "📊 Reality Audit (No Target)"])

with tab1:
    if st.button("🔍 Scan Top 20"):
        picks = []
        for t in TICKERS_20:
            df = get_market_data(t, "2025-01-01")
            if df is not None:
                row = df.iloc[-1]
                # Entry Logic: Trend + Momentum + Volume
                if (row['Close'] > row['EMA200'] and 40 <= row['RSI'] <= 60 and 
                    row['ADX'] > 25 and row['RVOL'] >= vol_threshold and row['Is_Green']):
                    picks.append({'Ticker': t, 'ADX': round(row['ADX'],1), 'RVOL': round(row['RVOL'],2)})
        if picks: st.dataframe(pd.DataFrame(picks).sort_values('ADX', ascending=False))
        else: st.info("Waiting for setup on Top 20...")

with tab2:
    st.header("📋 Audit: Uncapped Profit vs 2% Stop")
    c1, c2 = st.columns(2)
    yr = c1.selectbox("Year", [2026, 2025])
    mo = c2.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    
    if st.button("📈 Run Audit"):
        m_idx = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(mo) + 1
        results = []
        total_p = 0.0
        
        for t in TICKERS_20:
            df = get_market_data(t, f"{yr-1}-01-01")
            if df is not None:
                m_data = df[(df.index.year == yr) & (df.index.month == m_idx)]
                for date, row in m_data.iterrows():
                    # Check if signal fired
                    if (row['Close'] > row['EMA200'] and row['ADX'] > 25 and 
                        40 <= row['RSI'] <= 60 and row['Is_Green'] and row['RVOL'] >= vol_threshold):
                        
                        # Check if Low hit the 2% Stop
                        hit_stop = row['Low'] <= (row['Open'] * (1 - (stop_loss_pct/100)))
                        
                        if hit_stop:
                            p = -(stop_loss_pct + slippage)
                            status = "❌ STOP OUT (-2%)"
                        else:
                            # NO TARGET: Profit is determined at the Close
                            p = (((row['Close'] - row['Open']) / row['Open']) * 100) - slippage
                            status = f"💰 CLOSE EXIT ({p:.2f}%)"
                        
                        total_p += p
                        results.append({'Date': date.date(), 'Ticker': t, 'Status': status, 'Result %': round(p, 2)})
        
        if results:
            st.metric("Total Monthly Performance", f"{total_p:.2f}%")
            st.dataframe(pd.DataFrame(results), use_container_width=True)