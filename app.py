import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Goldilocks Master Suite", layout="wide")
st.title("🏹 Goldilocks Trading Master Suite")

# --- SIDEBAR: GLOBAL STRATEGY CONTROLS ---
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

# --- SHARED DATA ENGINE ---
@st.cache_data(ttl=3600)
def get_war_chest_data(ticker, start_date):
    try:
        df = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Indicators
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
tab1, tab2, tab3 = st.tabs(["🚀 Next Open Selector", "📊 Historical Proof ($)", "💰 20-Year Growth"])

# --- TAB 1: NEXT OPEN ---
with tab1:
    st.header("🎯 Monday Morning Entry Signals")
    st.info("Scanner looks at Friday's close to find high-probability Monday entries.")
    
    if st.button("🔍 Scan 60 Tickers for Monday"):
        picks = []
        spy = get_war_chest_data("SPY", "2025-01-01")
        market_bullish = spy['Close'].iloc[-1] > spy['EMA200'].iloc[-1] if spy is not None else False
        
        if not market_bullish:
            st.error("🚨 MARKET FILTER: BEARISH. SPY is below EMA200.")
        else:
            with st.spinner(f"Scanning {len(TICKERS)} stocks..."):
                for t in TICKERS:
                    df = get_war_chest_data(t, "2025-01-01")
                    if df is not None:
                        row = df.iloc[-1]
                        if (row['Close'] > row['EMA200'] and 40 <= row['RSI'] <= 60 and 
                            row['ADX'] > 25 and row['RVOL'] >= vol_threshold and row['Is_Green']):
                            picks.append({
                                'Ticker': t, 'ADX': round(row['ADX'],1), 
                                'RVOL': round(row['RVOL'],2), 'RSI': round(row['RSI'],1)
                            })
            
            if picks:
                recs = pd.DataFrame(picks).sort_values(by=['ADX', 'RVOL'], ascending=False)
                st.success(f"Found {len(recs)} potential signals for Monday Morning!")
                st.dataframe(recs, use_container_width=True)
            else:
                st.warning("No tickers passed the strict volume/candle filters today.")

# --- TAB 2: HISTORICAL PROOF ($1000 AUDIT) ---
with tab2:
    st.header("📋 Historical Proof & Profit Audit")
    c1, c2, c3 = st.columns(3)
    audit_year = c1.selectbox("Audit Year", range(2026, 2019, -1))
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    audit_month = c2.selectbox("Audit Month", months)
    starting_cap = c3.number_input("Audit Capital ($)", value=1000)
    month_idx = months.index(audit_month) + 1

    if st.button("📊 Run $1,000 Profit Audit"):
        audit_results = []
        spy = get_war_chest_data("SPY", f"{audit_year-1}-01-01")
        if spy is not None:
            spy['MKT_BULL'] = spy['Close'] > spy['EMA200']
            with st.spinner(f"Calculating {audit_month} Profits..."):
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
                                trade_profit = starting_cap * (target_pct / 100) if hit else 0
                                audit_results.append({
                                    'Date': date.date(), 'Ticker': t, 
                                    'Status': "✅ WIN" if hit else "❌ FAIL", 
                                    'Profit ($)': round(trade_profit, 2)
                                })
            
            if audit_results:
                res_df = pd.DataFrame(audit_results)
                total_profit = res_df['Profit ($)'].sum()
                win_rate = (len(res_df[res_df['Status'] == "✅ WIN"]) / len(res_df)) * 100
                
                st.markdown("---")
                m1, m2, m3 = st.columns(3)
                m1.metric("Total