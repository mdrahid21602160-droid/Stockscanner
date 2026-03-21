import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
from datetime import datetime, timedelta

# --- PAGE CONFIG ---
st.set_page_config(page_title="Goldilocks Daily Selector", layout="wide")
st.title("🏹 Goldilocks Trading Dashboard")
st.subheader("Market-Filtered Daily Selection & Audit")

# --- SIDEBAR: CONTROLS ---
st.sidebar.header("🗓️ Audit Period")
current_year = datetime.now().year
selected_year = st.sidebar.selectbox("Select Year", range(current_year, 2019, -1))

months = ["January", "February", "March", "April", "May", "June", 
          "July", "August", "September", "October", "November", "December"]
selected_month_name = st.sidebar.selectbox("Select Month", months)
month_idx = months.index(selected_month_name) + 1

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Strategy Settings")
target_pct = st.sidebar.slider("Profit Target (%)", 0.1, 1.0, 0.3, 0.1)
gap_limit = 2.0  # Hardcoded per your 2.0% gap safety rule

TICKERS = ['AAPL', 'NVDA', 'MSFT', 'TSLA', 'AMZN', 'GOOGL', 'META', 'NFLX', 
           'AMD', 'AVGO', 'COST', 'SMCI', 'MSTR', 'QCOM', 'ORCL', 'INTU', 
           'ADBE', 'CRM', 'ISRG', 'MU']

# --- CORE LOGIC ENGINE ---
@st.cache_data(ttl=3600)
def run_goldilocks_audit(year, month):
    audit_results = []
    # Fetch 1 year lead-in for EMA stability
    fetch_start = f"{year-1}-01-01"
    
    try:
        # 1. MARKET FILTER (SPY)
        spy = yf.download("SPY", start=fetch_start, progress=False, auto_adjust=True)
        if isinstance(spy.columns, pd.MultiIndex): spy.columns = spy.columns.get_level_values(0)
        spy['MARKET_EMA'] = ta.ema(spy['Close'], length=200)
        spy['MARKET_BULLISH'] = spy['Close'] > spy['MARKET_EMA']
        
        # 2. TICKER SCAN
        for ticker in TICKERS:
            df = yf.download(ticker, start=fetch_start, progress=False, auto_adjust=True)
            if df.empty: continue
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

            # Indicators
            df['EMA200'] = ta.ema(df['Close'], length=200)
            df['RSI'] = ta.rsi(df['Close'], length=14)
            adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
            df['ADX'] = adx_df.iloc[:, 0]
            df['Gap'] = ((df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)) * 100

            # Merge Market Filter
            df = df.join(spy[['MARKET_BULLISH']], how='left')

            # Filter for the selected month/year
            subset = df[(df.index.year == year) & (df.index.month == month)].dropna()

            for date, row in subset.iterrows():
                if date.weekday() == 4: continue # Monday to Thursday only
                
                # Goldilocks Logic
                is_bullish_mkt = row['MARKET_BULLISH']
                is_trending_stock = row['Close'] > row['EMA200']
                is_goldilocks_rsi = 40 <= row['RSI'] <= 60
                is_strong_adx = row['ADX'] > 25
                is_safe_gap = abs(row['Gap']) < gap_limit

                if is_bullish_mkt and is_trending_stock and is_goldilocks_rsi and is_strong_adx and is_safe_gap:
                    hit = row['High'] >= (row['Open'] * (1 + (target_pct/100)))
                    audit_results.append({
                        'Date': date.strftime('%Y-%m-%d'),
                        'Ticker': ticker,
                        'Price': round(float(row['Close']), 2),
                        'RSI': round(float(row['RSI']), 1),
                        'ADX': round(float(row['ADX']), 1),
                        'Gap %': round(float(row['Gap']), 2),
                        'Status': "✅ WIN" if hit else "❌ FAIL"
                    })
    except Exception as e:
        st.error(f"Error fetching data: {e}")
            
    return pd.DataFrame(audit_results)

# --- UI EXECUTION ---
if st.button("🚀 Run Analysis & Daily Picks"):
    with st.spinner(f"Auditing Market Health and {len(TICKERS)} tickers..."):
        results_df = run_goldilocks_audit(selected_year, month_idx)
        
        if not results_df.empty:
            # A. TOP RECOMMENDATION SECTION
            st.markdown("---")
            st.header("🎯 Top Daily Selections")
            latest_date = results_df['Date'].max()
            daily_picks = results_df[results_df['Date'] == latest_date].copy()
            
            if not daily_picks.empty:
                # Ranking: Best ADX + RSI closest to 50
                daily_picks['RSI_Dist'] = abs(daily_picks['RSI'] - 50)
                recommendations = daily_picks.sort_values(by=['ADX', 'RSI_Dist'], ascending=[False, True]).head(3)
                
                cols = st.columns(len(recommendations))
                for i, (idx, row) in enumerate(recommendations.iterrows()):
                    with cols[i]:
                        st.success(f"**#{i+1} Pick: {row['Ticker']}**")
                        st.write(f"Trend (ADX): {row['ADX']}")
                        st.write(f"RSI: {row['RSI']}")
            else:
                st.info("No signals found for the most recent day in this month.")

            # B. METRICS SUMMARY
            st.markdown("---")
            total_sigs = len(results_df)
            wins = len(results_df[results_df['Status'] == "✅ WIN"])
            win_rate = (wins / total_sigs) * 100 if total_sigs > 0 else 0
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Monthly Signals", total_sigs)
            m2.metric("Wins", wins)
            m3.metric("Win Rate", f"{win_rate:.1f}%")

            # C. FULL DATA TABLE
            st.subheader("📋 Full Monthly Audit Log")
            def color_status(val):
                return 'background-color: #125e1c' if val == "✅ WIN" else 'background-color: #5e1212'
            
            st.dataframe(
                results_df.style.applymap(color_status, subset=['Status']), 
                use_container_width=True
            )
            
            # Download
            csv = results_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Monthly Report", data=csv, file_name=f"Goldilocks_Audit_{selected_year}_{month_idx}.csv")
            
        else:
            st.warning(f"No signals found for {selected_month_name} {selected_year}. Either the market was bearish (SPY < EMA200) or stocks were too choppy.")