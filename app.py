import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Goldilocks War Chest", layout="wide")
st.title("🏹 Goldilocks Trading Dashboard")

# --- SIDEBAR: GLOBAL SETTINGS ---
st.sidebar.header("⚙️ Strategy Parameters")
target_pct = st.sidebar.slider("Profit Target (%)", 0.1, 1.0, 0.3, 0.1)
gap_limit = 2.0  # Your 2.0% gap safety rule

TICKERS = ['AAPL', 'NVDA', 'MSFT', 'TSLA', 'AMZN', 'GOOGL', 'META', 'NFLX', 
           'AMD', 'AVGO', 'COST', 'SMCI', 'MSTR', 'QCOM', 'ORCL', 'INTU', 
           'ADBE', 'CRM', 'ISRG', 'MU']

# --- TABS FOR ORGANIZATION ---
tab1, tab2 = st.tabs(["🚀 Monday's Picks", "📊 Backtest Proof (Historical Audit)"])

# --- CORE DATA FUNCTION ---
@st.cache_data(ttl=3600)
def get_processed_data(ticker, start_date):
    try:
        df = yf.download(ticker, start=start_date, progress=False, auto_adjust=True)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
        
        # Indicators
        df['EMA200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
        df['ADX'] = adx_df.iloc[:, 0]
        df['Gap'] = ((df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)) * 100
        return df
    except: return None

# --- TAB 1: NEXT OPEN SELECTION (FOR MONDAY) ---
with tab1:
    st.header("🎯 Ready-to-Trade: Next Open")
    st.info("Scanner looks at Friday's close to find high-probability Monday entries.")
    
    if st.button("🔍 Generate Monday Picks"):
        picks = []
        # Get Market Filter (SPY)
        spy = get_processed_data("SPY", "2025-01-01")
        market_bullish = spy['Close'].iloc[-1] > spy['EMA200'].iloc[-1] if spy is not None else False
        
        if not market_bullish:
            st.error("🚨 MARKET FILTER: BEARISH. SPY is below EMA200. No trades recommended.")
        else:
            st.success("✅ MARKET FILTER: BULLISH. Scanning tickers...")
            for t in TICKERS:
                df = get_processed_data(t, "2025-01-01")
                if df is not None:
                    row = df.iloc[-1] # Friday's Close
                    # Goldilocks Logic
                    if row['Close'] > row['EMA200'] and 40 <= row['RSI'] <= 60 and row['ADX'] > 25:
                        picks.append({
                            'Ticker': t, 
                            'ADX': round(row['ADX'],1), 
                            'RSI': round(row['RSI'],1), 
                            'Last Close': round(row['Close'],2),
                            'Dist': abs(row['RSI']-50)
                        })
            
            if picks:
                # Rank by High ADX and RSI Near 50
                recs = pd.DataFrame(picks).sort_values(by=['ADX', 'Dist'], ascending=[False, True]).head(3)
                st.subheader("Monday's Top 3 Targets")
                cols = st.columns(3)
                for i, (_, r) in enumerate(recs.iterrows()):
                    with cols[i]:
                        st.success(f"**Pick #{i+1}: {r['Ticker']}**")
                        st.write(f"Trend (ADX): {r['ADX']}")
                        st.write(f"RSI: {r['RSI']}")
                        st.write(f"Entry Signal: Monday Open")
            else:
                st.warning("No tickers met the 'Goldilocks' criteria on Friday's close.")

# --- TAB 2: BACKTEST PROOF (HISTORICAL AUDIT) ---
with tab2:
    st.header("📋 Historical Proof of Performance")
    c1, c2 = st.columns(2)
    current_year = datetime.now().year
    audit_year = c1.selectbox("Audit Year", range(current_year, 2020, -1))
    months = ["January", "February", "March", "April", "May", "June", 
              "July", "August", "September", "October", "November", "December"]
    audit_month_name = c2.selectbox("Audit Month", months)
    month_idx = months.index(audit_month_name) + 1

    if st.button("📊 Run Proof Audit"):
        audit_data = []
        # Fetch lead-in data for SPY and Tickers
        spy = get_processed_data("SPY", f"{audit_year-1}-01-01")
        if spy is not None:
            spy['MKT_BULL'] = spy['Close'] > spy['EMA200']
            
            with st.spinner(f"Auditing {audit_month_name} {audit_year}..."):
                for t in TICKERS:
                    df = get_processed_data(t, f"{audit_year-1}-01-01")
                    if df is not None:
                        df = df.join(spy[['MKT_BULL']], how='left')
                        # Filter for selected month/year
                        subset = df[(df.index.year == audit_year) & (df.index.month == month_idx)]
                        
                        for date, row in subset.iterrows():
                            # Skip Fridays (Hard exit strategy)
                            if date.weekday() < 4 and row['MKT_BULL'] and row['Close'] > row['EMA200'] and \
                               40 <= row['RSI'] <= 60 and row['ADX'] > 25 and abs(row['Gap']) < gap_limit:
                                
                                # Proof Calculation: Did High hit Target % above Open?
                                target_price = row['Open'] * (1 + (target_pct/100))
                                hit = row['High'] >= target_price
                                
                                audit_data.append({
                                    'Date': date.date(),
                                    'Ticker': t,
                                    'Price': round(row['Close'], 2),
                                    'Status': "✅ WIN" if hit else "❌ FAIL"
                                })
            
            if audit_data:
                res_df = pd.DataFrame(audit_data)
                win_count = len(res_df[res_df['Status'] == "✅ WIN"])
                total_sigs = len(res_df)
                win_rate = (win_count / total_sigs) * 100
                
                st.markdown("---")
                m1, m2, m3 = st.columns(3)
                m1.metric("Signals Found", total_sigs)
                m2.metric("Wins", win_count)
                m3.metric("Audit Win Rate", f"{win_rate:.1f}%")
                
                # Table Formatting
                def color_status(val):
                    color = '#125e1c' if val == "✅ WIN" else '#5e1212'
                    return f'background-color: {color}'
                
                st.dataframe(res_df.style.applymap(color_status, subset=['Status']), use_container_width=True)
                
                csv = res_df.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Proof Report", data=csv, file_name=f"Goldilocks_Audit_{audit_month_name}_{audit_year}.csv")
            else:
                st.warning(f"No qualifying signals found for {audit_month_name} {audit_year}.")
        else:
            st.error("Could not fetch Market Filter (SPY) data.")