import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Goldilocks Profit Tracker", layout="wide")
st.title("🏹 Goldilocks Trading: Monthly Profit Audit")

# --- SIDEBAR ---
st.sidebar.header("⚙️ Strategy Parameters")
target_pct = st.sidebar.slider("Profit Target (%)", 0.1, 1.0, 0.5, 0.1)
vol_threshold = st.sidebar.slider("Min Relative Volume (RVOL)", 1.0, 2.5, 1.1, 0.1)
gap_limit = 2.0 

TICKERS = [
    'AAPL', 'NVDA', 'MSFT', 'TSLA', 'AMZN', 'GOOGL', 'META', 'NFLX', 'ORCL', 'CRM', 'ADBE', 'IBM',
    'AMD', 'AVGO', 'SMCI', 'MU', 'QCOM', 'INTC', 'ARM', 'LRCX', 'ASML', 'ADI',
    'PYPL', 'V', 'MA', 'SQ', 'COIN', 'JPM', 'BAC', 'GS', 'MS', 'HOOD',
    'MSTR', 'PLTR', 'SNOW', 'PATH', 'U', 'RBLX', 'SHOP', 'NET', 'TSM',
    'COST', 'WMT', 'TGT', 'NKE', 'SBUX', 'LULU', 'CMG', 'BKNG',
    'LLY', 'UNH', 'PFE', 'ABBV', 'MRNA', 'ISRG',
    'XOM', 'CVX', 'CAT', 'BA', 'GE'
]

@st.cache_data(ttl=3600)
def get_clean_data(ticker, start_date):
    try:
        df = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
        if df is None or df.empty or len(df) < 200: return None
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

tab1, tab2, tab3 = st.tabs(["🚀 Next Open Selector", "📊 Historical Audit", "💰 20-Year Growth"])

# --- TAB 1: LIVE SCAN ---
with tab1:
    st.header("🎯 Monday Morning Signals")
    if st.button("🔍 Run Live Scan"):
        picks = []
        spy = get_clean_data("SPY", "2024-01-01")
        if spy is not None and spy['Close'].iloc[-1] > spy['EMA200'].iloc[-1]:
            for t in TICKERS:
                df = get_clean_data(t, "2024-01-01")
                if df is not None:
                    row = df.iloc[-1]
                    if (row['Close'] > row['EMA200'] and 40 <= row['RSI'] <= 60 and 
                        row['ADX'] > 25 and row['RVOL'] >= vol_threshold and row['Is_Green']):
                        picks.append({'Ticker': t, 'ADX': round(row['ADX'],1), 'RVOL': round(row['RVOL'],2), 'Price': round(row['Close'],2)})
            if picks:
                st.dataframe(pd.DataFrame(picks).sort_values('ADX', ascending=False), use_container_width=True)
            else:
                st.info("No matches found. Try lowering RVOL.")
        else:
            st.error("Market Filter: SPY is Bearish.")

# --- TAB 2: AUDIT WITH PROFIT TRACKING ---
with tab2:
    st.header("📊 Monthly Profit Audit")
    c1, c2 = st.columns(2)
    audit_year = c1.selectbox("Year", [2026, 2025, 2024])
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    audit_month = c2.selectbox("Month", months)
    
    if st.button("📈 Run Profit Backtest"):
        m_idx = months.index(audit_month) + 1
        results = []
        total_monthly_gain = 0.0
        
        with st.spinner(f"Calculating profit for {audit_month}..."):
            for t in TICKERS:
                df = get_clean_data(t, f"{audit_year-1}-01-01")
                if df is not None:
                    m_data = df[(df.index.year == audit_year) & (df.index.month == m_idx)]
                    for date, row in m_data.iterrows():
                        if (row['Close'] > row['EMA200'] and row['ADX'] > 25 and 
                            40 <= row['RSI'] <= 60 and row['Is_Green'] and row['RVOL'] >= vol_threshold):
                            
                            target_price = row['Open'] * (1 + (target_pct / 100))
                            hit = row['High'] >= target_price
                            
                            trade_profit = target_pct if hit else 0.0
                            total_monthly_gain += trade_profit
                            
                            results.append({
                                'Date': date.date(), 
                                'Ticker': t, 
                                'Status': "✅ WIN" if hit else "❌ FAIL",
                                'Profit (%)': f"+{trade_profit}%" if hit else "0.0%"
                            })
            
            if results:
                res_df = pd.DataFrame(results)
                win_rate = (len(res_df[res_df['Status'] == "✅ WIN"]) / len(res_df)) * 100
                
                # --- PROFIT METRICS ---
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Signals", len(res_df))
                m2.metric("Win Rate", f"{win_rate:.1f}%")
                m3.metric("Total Monthly Profit", f"+{total_monthly_gain:.2f}%", delta_color="normal")
                
                st.dataframe(res_df, use_container_width=True)
            else:
                st.warning("No setups found. Try lowering RVOL to 1.0.")

# --- TAB 3: GROWTH ---
with tab3:
    st.header("💰 20-Year Growth Projection")
    init = st.number_input("Starting Capital", value=1000)
    wins = st.slider("Total Monthly Profit Target (%)", 1.0, 20.0, 7.5) # Based on Tab 2 results
    final = init * ((1 + (wins/100)) ** 240)
    st.metric("20-Year Outcome", f"${final:,.2f}")