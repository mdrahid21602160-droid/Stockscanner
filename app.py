import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Goldilocks Daily Selector", layout="wide")
st.title("🏹 Goldilocks: Next Open Selector")
st.info("Scanner targeting entry for: **Monday, March 23, 2026**")

# --- SIDEBAR: SETTINGS ---
st.sidebar.header("⚙️ Strategy Parameters")
target_pct = st.sidebar.slider("Profit Target (%)", 0.1, 1.0, 0.3, 0.1)
st.sidebar.markdown("---")
st.sidebar.write("Logic: Scan Friday data to find Monday morning entries.")

TICKERS = ['AAPL', 'NVDA', 'MSFT', 'TSLA', 'AMZN', 'GOOGL', 'META', 'NFLX', 
           'AMD', 'AVGO', 'COST', 'SMCI', 'MSTR', 'QCOM', 'ORCL', 'INTU', 
           'ADBE', 'CRM', 'ISRG', 'MU']

@st.cache_data(ttl=3600)
def get_next_open_picks():
    picks = []
    # Fetch data up to today to get the most recent Friday close
    fetch_start = "2025-01-01"
    
    # 1. MARKET FILTER (SPY)
    spy = yf.download("SPY", start=fetch_start, progress=False, auto_adjust=True)
    if isinstance(spy.columns, pd.MultiIndex): spy.columns = spy.columns.get_level_values(0)
    spy['MARKET_EMA'] = ta.ema(spy['Close'], length=200)
    
    # Check if Market is currently Bullish
    market_bullish = spy['Close'].iloc[-1] > spy['MARKET_EMA'].iloc[-1]
    
    if not market_bullish:
        return pd.DataFrame(), False

    # 2. TICKER SCAN
    for ticker in TICKERS:
        try:
            df = yf.download(ticker, start=fetch_start, progress=False, auto_adjust=True)
            if df.empty: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

            # Indicators
            df['EMA200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
            df['ADX'] = adx_df.iloc[:, 0]
            
            # Use the VERY LAST row (Friday's Close)
            row = df.iloc[-1]
            
            # Goldilocks Filters
            if row['Close'] > row['EMA200'] and 40 <= row['RSI'] <= 60 and row['ADX'] > 25:
                picks.append({
                    'Ticker': ticker,
                    'Last Close': round(float(row['Close']), 2),
                    'RSI': round(float(row['RSI']), 1),
                    'ADX': round(float(row['ADX']), 1),
                    'RSI_Dist': abs(row['RSI'] - 50) # For ranking
                })
        except:
            continue
            
    return pd.DataFrame(picks), True

# --- EXECUTION ---
if st.button("🔍 Find Monday's Picks"):
    with st.spinner("Analyzing Friday's close for Monday's open..."):
        picks_df, is_bullish = get_next_open_picks()
        
        if not is_bullish:
            st.error("🚨 MARKET FILTER: BEARISH. SPY is below EMA200. No trades recommended for Monday.")
        elif picks_df.empty:
            st.warning("No tickers in the War Chest met the 'Goldilocks' criteria today.")
        else:
            st.success("✅ MARKET FILTER: BULLISH. Scanning for Monday entries...")
            
            # Rank by highest ADX and RSI closest to 50
            recommendations = picks_df.sort_values(by=['ADX', 'RSI_Dist'], ascending=[False, True]).head(3)
            
            st.header("🎯 Monday Morning Top 3 Picks")
            st.write("Target Entry: Monday Open | Target Exit: +{}% or Market Close".format(target_pct))
            
            cols = st.columns(3)
            for i, (idx, row) in enumerate(recommendations.iterrows()):
                with cols[i]:
                    st.metric(f"Rank #{i+1}", row['Ticker'])
                    st.write(f"**ADX:** {row['ADX']} (Strong)")
                    st.write(f"**RSI:** {row['RSI']} (Stable)")
                    st.write(f"**Last Close:** ${row['Last Close']}")
            
            st.markdown("---")
            st.subheader("📋 All Qualifying Tickers")
            st.table(picks_df.drop(columns=['RSI_Dist']).sort_values(by='ADX', ascending=False))