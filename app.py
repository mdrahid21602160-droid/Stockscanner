import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Goldilocks Reality Suite", layout="wide")
st.title("🏹 Goldilocks Trading: The Reality Check")

# --- SIDEBAR: RISK CONTROLS ---
st.sidebar.header("⚙️ Strategy Parameters")
target_pct = st.sidebar.slider("Profit Target (%)", 0.1, 1.0, 0.7, 0.1)
stop_loss_pct = st.sidebar.slider("Stop Loss (%)", 0.5, 3.0, 1.0, 0.1)
vol_threshold = st.sidebar.slider("Min RVOL", 1.0, 2.5, 1.1, 0.1)
slippage = 0.05 

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
def get_market_data(ticker, start_date):
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

tab1, tab2, tab3 = st.tabs(["🚀 Monday Scan", "📊 Reality Audit", "📈 Compounding"])

# --- TAB 1: LIVE SCANNER ---
with tab1:
    st.header("🎯 Monday Morning Signals")
    if st.button("🔍 Scan 60 Tickers"):
        picks = []
        spy = get_market_data("SPY", "2024-01-01")
        if spy is not None and spy['Close'].iloc[-1] > spy['EMA200'].iloc[-1]:
            for t in TICKERS:
                df = get_market_data(t, "2024-01-01")
                if df is not None:
                    row = df.iloc[-1]
                    if (row['Close'] > row['EMA200'] and 40 <= row['RSI'] <= 60 and 
                        row['ADX'] > 25 and row['RVOL'] >= vol_threshold and row['Is_Green']):
                        picks.append({'Ticker': t, 'ADX': round(row['ADX'],1), 'RVOL': round(row['RVOL'],2)})
            if picks:
                st.dataframe(pd.DataFrame(picks).sort_values('ADX', ascending=False), use_container_width=True)
            else: st.info("No stocks met the criteria today.")
        else: st.error("Market Bearish: SPY < EMA200.")

# --- TAB 2: REALITY AUDIT ---
with tab2:
    st.header("📋 The Reality Backtest") # Fixed the quote syntax error here
    c1, c2 = st.columns(2)
    yr = c1.selectbox("Year", [2026, 2025, 2024])
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    mo = c2.selectbox("Month", months)
    
    if st.button("📈 Run Audit"):
        m_idx = months.index(mo) + 1
        results = []
        total_profit = 0.0
        
        with st.spinner("Processing trades..."):
            for t in TICKERS:
                df = get_market_data(t, f"{yr-1}-01-01")
                if df is not None:
                    m_data = df[(df.index.year == yr) & (df.index.month == m_idx)]
                    for date, row in m_data.iterrows():
                        if (row['Close'] > row['EMA200'] and row['ADX'] > 25 and 
                            40 <= row['RSI'] <= 60 and row['Is_Green'] and row['RVOL'] >= vol_threshold):
                            
                            # Logic: Did we hit Stop Loss or Target? 
                            # We check Low first (Conservative)
                            hit_stop = row['Low'] <= (row['Open'] * (1 - (stop_loss_pct/100)))
                            hit_target = row['High'] >= (row['Open'] * (1 + (target_pct/100)))
                            
                            if hit_stop:
                                status, p = "❌ STOP OUT", -(stop_loss_pct + slippage)
                            elif hit_target:
                                status, p = "✅ WIN", (target_pct - slippage)
                            else:
                                # Exit at Close if nothing hit
                                p = ((row['Close'] - row['Open']) / row['Open'] * 100) - slippage
                                status = "✅ CLOSE WIN" if p > 0 else "❌ CLOSE LOSS"
                            
                            total_profit += p
                            results.append({'Date': date.date(), 'Ticker': t, 'Status': status, 'Net %': round(p, 2)})
            
            if results:
                res_df = pd.DataFrame(results)
                win_rate = (len(res_df[res_df['Status'].str.contains("WIN")]) / len(res_df)) * 100
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Trades", len(res_df))
                m2.metric("Real Win Rate", f"{win_rate:.1f}%")
                m3.metric("Total Monthly Profit", f"{total_profit:.2f}%")
                st.dataframe(res_df, use_container_width=True)
            else: st.warning("No signals found for this period.")

# --- TAB 3: COMPOUNDING ---
with tab3:
    st.header("💰 20-Year Growth")
    init = st.number_input("Start $", value=1000)
    # Using a realistic monthly profit based on your backtest results
    mo_avg = st.slider("