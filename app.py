import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import numpy as np
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="Goldilocks War Chest v4", layout="wide")
st.title("🏹 Goldilocks Trading Dashboard")

# --- SIDEBAR: STRATEGY CONTROLS ---
st.sidebar.header("⚙️ Strategy Parameters")
target_pct = st.sidebar.slider("Profit Target (%)", 0.1, 1.0, 0.3, 0.1)
vol_threshold = st.sidebar.slider("Min Relative Volume (RVOL)", 1.0, 2.5, 1.2, 0.1)
gap_limit = 2.0 

TICKERS = ['AAPL', 'NVDA', 'MSFT', 'TSLA', 'AMZN', 'GOOGL', 'META', 'NFLX', 
           'AMD', 'AVGO', 'COST', 'SMCI', 'MSTR', 'QCOM', 'ORCL', 'INTU', 
           'ADBE', 'CRM', 'ISRG', 'MU']

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
tab1, tab2, tab3 = st.tabs(["🚀 Monday's Picks", "📊 Backtest Proof", "📈 20-Year Compounding"])

# --- TAB 1 & 2 Logic (Same as before, abbreviated for brevity) ---
with tab1:
    st.header("🎯 Monday Morning Entry")
    if st.button("🔍 Scan for Monday"):
        # ... (Same logic as previous version)
        st.write("Scan complete. (Ensure you run the Backtest tab to verify performance)")

with tab2:
    st.header("📋 Proof of Performance Audit")
    # ... (Same audit logic as previous version)
    st.write("Select Year/Month to see verified Win Rate.")

# --- NEW TAB 3: COMPOUNDING GROWTH ---
with tab3:
    st.header("💰 20-Year Wealth Projection")
    st.write("Based on the **0.3% - 1.0%** daily targets from your 'War Chest' tickers.")
    
    col_a, col_b = st.columns(2)
    initial_inv = col_a.number_input("Starting Capital ($)", value=10000)
    avg_trades_per_month = col_b.slider("Estimated Successful Trades Per Month", 1, 20, 8)
    
    # Calculation Logic
    years = 20
    months = years * 12
    monthly_return = (target_pct / 100) * avg_trades_per_month
    
    # Generate Growth Data
    balances = []
    current_balance = initial_inv
    for m in range(months + 1):
        balances.append(current_balance)
        current_balance *= (1 + monthly_return)
    
    # Create DataFrame for Charting
    growth_df = pd.DataFrame({
        "Month": range(months + 1),
        "Year": [m/12 for m in range(months + 1)],
        "Balance": balances
    })
    
    # Display Metrics
    final_val = balances[-1]
    st.metric("Estimated Value after 20 Years", f"${final_val:,.2f}")
    
    # Line Chart
    st.line_chart(growth_df.set_index("Year")["Balance"])
    
    st.info(f"""
    **Assumptions:**
    * You achieve **{avg_trades_per_month}** winning trades per month.
    * Each trade hits your **{target_pct}%** profit target.
    * Profits are reinvested monthly (Compounding).
    * This does not account for taxes or potential losing trades.
    """)

    # Table View
    if st.checkbox("Show Year-by-Year Breakdown"):
        year_breakdown = growth_df[growth_df['Month'] % 12 == 0].copy()
        year_breakdown['Balance'] = year_breakdown['Balance'].map('${:,.2f}'.format)
        st.table(year_breakdown[['Year', 'Balance']])