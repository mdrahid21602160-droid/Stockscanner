import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd

# --- PAGE CONFIG ---
st.set_page_config(page_title="Goldilocks Global Sentinel", layout="wide")
st.title("🏹 Goldilocks Trading: Global Sentinel Edition")

# --- SIDEBAR: RISK CONTROLS ---
st.sidebar.header("⚙️ Strategy Parameters")
target_pct = st.sidebar.slider("Profit Target (%)", 0.1, 1.5, 0.7, 0.1)
stop_loss_pct = st.sidebar.slider("Stop Loss (%)", 0.5, 3.0, 1.0, 0.1)
vol_threshold = st.sidebar.slider("Min RVOL", 1.0, 2.5, 1.1, 0.1)

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
        if df is None or df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['EMA200'] = ta.ema(df['Close'], length=200)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        adx_df = ta.adx(df['High'], df['Low'], df['Close'], length=14)
        df['ADX'] = adx_df.iloc[:, 0] if adx_df is not None else 0
        df['Avg_Vol'] = df['Volume'].rolling(window=10).mean()
        df['RVOL'] = df['Volume'] / df['Avg_Vol']
        df['Is_Green'] = df['Close'] > df['Open']
        df['Change_Pct'] = ((df['Close'] - df['Open']) / df['Open']) * 100
        return df
    except: return None

# --- NEW: GLOBAL SENTINEL CHECK ---
def check_global_sentinel():
    st.subheader("🌍 Global Market Sentinel")
    col1, col2 = st.columns(2)
    
    # Nikkei 225 (^N225) and FTSE 100 (^FTSE)
    indices = {"Nikkei 225": "^N225", "FTSE 100": "^FTSE"}
    status = True
    
    for (name, sym), col in zip(indices.items(), [col1, col2]):
        idx_df = yf.download(sym, period="2d", progress=False, auto_adjust=True)
        if not idx_df.empty:
            if isinstance(idx_df.columns, pd.MultiIndex): idx_df.columns = idx_df.columns.get_level_values(0)
            change = ((idx_df['Close'].iloc[-1] - idx_df['Open'].iloc[-1]) / idx_df['Open'].iloc[-1]) * 100
            is_green = idx_df['Close'].iloc[-1] > idx_df['Open'].iloc[-1]
            
            color = "green" if is_green else "red"
            icon = "✅ GO" if is_green else "❌ NO-GO"
            col.metric(name, f"{change:.2f}%", delta=icon, delta_color="normal")
            if not is_green: status = False
        else:
            col.warning(f"Could not fetch {name}")
    return status

tab1, tab2, tab3 = st.tabs(["🚀 Monday Scan", "📊 Reality Audit", "📈 Compounding"])

# --- TAB 1: LIVE SCANNER ---
with tab1:
    global_go = check_global_sentinel()
    
    if not global_go:
        st.error("🚨 GLOBAL WARNING: Nikkei or FTSE is RED. Execution is high risk.")
    
    if st.button("🔍 Scan 60 Tickers"):
        picks = []
        spy = get_market_data("SPY", "2025-01-01")
        if spy is not None and spy['Close'].iloc[-1] > spy['EMA200'].iloc[-1]:
            for t in TICKERS:
                df = get_market_data(t, "2025-01-01")
                if df is not None:
                    row = df.iloc[-1]
                    # Original Strategy + Global Filter Logic
                    if (row['Close'] > row['EMA200'] and 40 <= row['RSI'] <= 60 and 
                        row['ADX'] > 25 and row['RVOL'] >= vol_threshold and row['Is_Green']):
                        picks.append({'Ticker': t, 'ADX': round(row['ADX'],1), 'RVOL': round(row['RVOL'],2)})
            
            if picks:
                st.success(f"Found {len(picks)} setups.")
                st.dataframe(pd.DataFrame(picks).sort_values('ADX', ascending=False), use_container_width=True)
            else: st.info("No stocks met the criteria today.")
        else: st.error("Market Bearish: SPY < EMA200.")

# --- TAB 2: AUDIT ---
with tab2:
    st.header("📋 Reality Backtest")
    c1, c2 = st.columns(2)
    yr = c1.selectbox("Year", [2026, 2025, 2024])
    mo = c2.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])
    
    if st.button("📈 Run Audit"):
        m_idx = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(mo) + 1
        results = []
        total_profit = 0.0
        
        for t in TICKERS:
            df = get_market_data(t, f"{yr-1}-01-01")
            if df is not None:
                m_data = df[(df.index.year == yr) & (df.index.month == m_idx)]
                for date, row in m_data.iterrows():
                    if (row['Close'] > row['EMA200'] and row['ADX'] > 25 and 
                        40 <= row['RSI'] <= 60 and row['Is_Green'] and row['RVOL'] >= vol_threshold):
                        
                        hit_stop = row['Low'] <= (row['Open'] * (1 - (stop_loss_pct/100)))
                        hit_target = row['High'] >= (row['Open'] * (1 + (target_pct/100)))
                        
                        if hit_stop: p, status = -(stop_loss_pct + 0.05), "❌ STOP"
                        elif hit_target: p, status = (target_pct - 0.05), "✅ WIN"
                        else: 
                            p = (((row['Close'] - row['Open']) / row['Open']) * 100) - 0.05
                            status = "✅ CLOSE WIN" if p > 0 else "❌ CLOSE LOSS"
                        
                        total_profit += p
                        results.append({'Date': date.date(), 'Ticker': t, 'Status': status, 'Net %': round(p, 2)})
        
        if results:
            res_df = pd.DataFrame(results)
            st.metric("Total Monthly Profit", f"{total_profit:.2f}%")
            st.dataframe(res_df, use_container_width=True)

# --- TAB 3: COMPOUNDING ---
with tab3:
    st.header("💰 20-Year Growth")
    init = st.number_input("Starting Capital ($)", value=1000)
    mo_avg = st.slider("Monthly Profit Avg (%)", 0.5, 20.0, 5.0)
    final_val = init * ((1 + (mo_avg/100)) ** 240)
    st.metric("Estimated Future Balance", f"${final_val:,.2f}")