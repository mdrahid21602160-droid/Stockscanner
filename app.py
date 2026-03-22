import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Goldilocks Master Suite", layout="wide")
st.title("🏹 Goldilocks Trading Master Suite")

# --- SIDEBAR: STRATEGY CONTROLS ---
st.sidebar.header("⚙️ Strategy Parameters")
target_pct = st.sidebar.slider("Profit Target (%)", 0.1, 1.0, 0.5, 0.1)
vol_threshold = st.sidebar.slider("Min Relative Volume (RVOL)", 1.0, 2.5, 1.2, 0.1)
gap_limit = 2.0 

# --- THE EXPANDED WAR CHEST (60 TICKERS) ---
TICKERS = [
    'AAPL', 'NVDA', 'MSFT', 'TSLA', 'AMZN', 'GOOGL', 'META', 'NFLX', 'ORCL', 'CRM', 'ADBE', 'IBM',
    'AMD', 'AVGO', 'SMCI', 'MU', 'QCOM', 'INTC', 'ARM', 'LRCX', 'ASML', 'ADI',
    'PYPL', 'V', 'MA', 'SQ', 'COIN', 'JPM', 'BAC', 'GS', 'MS', 'HOOD',
    'MSTR', 'PLTR', 'SNOW', 'PATH', 'U', 'RBLX', 'SHOP', 'NET', 'TSM',
    'COST', 'WMT', 'TGT', 'NKE', 'SBUX', 'LULU', 'CMG', 'BKNG',
    'LLY', 'UNH', 'PFE', 'ABBV', 'MRNA', 'ISRG',
    'XOM', 'CVX', 'CAT', 'BA', 'GE'
]

# --- DATA ENGINE ---
@st.cache_data(ttl=3600)
def get_war_chest_data(ticker, start_date):
    try:
        df = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df['EMA200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
        df['ADX'] = adx_df.iloc[:, 0]
        df['Avg_Vol'] = df['Volume'].rolling(window=10).mean()
        df['RVOL'] = df['Volume'] / df['Avg_Vol']
        df['Is_Green'] = df['Close'] > df['Open']
        df['Gap'] = ((df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)) * 100
        return df
    except: return None

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["🚀 Next Open Selector", "📊 Historical Audit (Backtest)", "💰 20-Year Growth"])

# --- TAB 1: NEXT OPEN ---
with tab1:
    st.header("🎯 Monday Morning Entry Signals")
    if st.button("🔍 Scan 60 Tickers for Monday"):
        picks = []
        spy = get_war_chest_data("SPY", "2025-01-01")
        market_bullish = spy['Close'].iloc[-1] > spy['EMA200'].iloc[-1] if spy is not None else False
        
        if not market_bullish:
            st.error("🚨 MARKET BEARISH: SPY < EMA200. No trades recommended.")
        else:
            with st.spinner(f"Scanning {len(TICKERS)} stocks..."):
                for t in TICKERS:
                    df = get_war_chest_data(t, "2025-01-01")
                    if df is not None:
                        row = df.iloc[-1]
                        if (row['Close'] > row['EMA200'] and 40 <= row['RSI'] <= 60 and 
                            row['ADX'] > 25 and row['RVOL'] >= vol_threshold and row['Is_Green']):
                            picks.append({'Ticker': t, 'ADX': round(row['ADX'],1), 'RVOL': round(row['RVOL'],2), 'RSI': round(row['RSI'],1)})
            
            if picks:
                recs = pd.DataFrame(picks).sort_values(by=['ADX', 'RVOL'], ascending=False)
                st.success(f"Found {len(recs)} potential trades!")
                st.dataframe(recs, use_container_width=True)
            else:
                st.warning("No tickers passed the filters. Try lowering RVOL in the sidebar.")

# --- TAB 2: AUDIT / BACKTEST ---
with tab2:
    st.header("📋 Proof of Performance Audit")
    c1, c2 = st.columns(2)
    audit_year = c1.selectbox("Audit Year", range(2026, 2019, -1))
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    audit_month = c2.selectbox("Audit Month", months)
    month_idx = months.index(audit_month) + 1

    if st.button("📊 Run Monthly Backtest"):
        audit_results = []
        spy = get_war_chest_data("SPY", f"{audit_year-1}-01-01")
        if spy is not None:
            spy['MKT_BULL'] = spy['Close'] > spy['EMA200']
            for t in TICKERS:
                df = get_war_chest_data(t, f"{audit_year-1}-01-01")
                if df is not None:
                    df = df.join(spy[['MKT_BULL']], how='left')
                    subset = df[(df.index.year == audit_year) & (df.index.month == month_idx)]
                    for date, row in subset.iterrows():
                        if (date.weekday() < 4 and row['MKT_BULL'] and row['Close'] > row['EMA200'] and 
                            40 <= row['RSI'] <= 60 and row['ADX'] > 25 and 
                            row['RVOL'] >= vol_threshold and row['Is_Green'] and abs(row['Gap']) < gap_limit):
                            hit = row['High'] >= (row['Open'] * (1 + (target_pct/100)))
                            audit_results.append({'Date': date.date(), 'Ticker': t, 'Status': "✅ WIN" if hit else "❌ FAIL"})
            
            if audit_results:
                res_df = pd.DataFrame(audit_results)
                win_count = len(res_df[res_df['Status'] == "✅ WIN"])
                total_sigs = len(res_df)
                win_rate = (win_count / total_sigs) * 100
                
                m1, m2, m3 = st.columns(3)
                m1.metric("Signals Found", total_sigs)
                m2.metric("Wins", win_count)
                m3.metric("Win Rate", f"{win_rate:.1f}%")
                st.dataframe(res_df, use_container_width=True)
            else:
                st.warning("No signals found in this period.")

# --- TAB 3: COMPOUNDING ---
with tab3:
    st.header("💰 20-Year Growth Projection")
    initial_inv = st.number_input("Starting Capital ($)", value=1000)
    avg_wins_mo = st.slider("Successful Trades Per Month", 1, 25, 15)
    
    months_total = 20 * 12
    monthly_rate = (target_pct / 100) * avg_wins_mo
    final_val = initial_inv * ((1 + monthly_rate) ** months_total)
    
    st.metric("Estimated Final Balance", f"${final_val:,.2f}")
    st.write(f"This assumes you hit your **{target_pct}%** target **{avg_wins_mo} times** a month for 20 years.")