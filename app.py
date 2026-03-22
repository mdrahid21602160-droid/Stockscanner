# --- ADDED TO YOUR SCANNER LOGIC ---

with tab1:
    if st.button("🔍 Scan for Quality Gaps"):
        picks = []
        for t in TICKERS_20:
            df = get_market_data(t, "2024-01-01")
            if df is not None:
                row = df.iloc[-1]
                
                # THE "ELITE" GAP FILTER
                is_trend = row['SMA50'] > row['SMA200']
                # We target gaps between 1.0% and 3.0% (Avoids noise and exhaustion)
                is_quality_gap = 1.0 <= row['Gap_Pct'] <= 3.0
                # Volume must be at least 50% higher than average to prove it's NOT "done"
                has_fuel = row['RVOL'] > 1.5 
                
                if is_trend and is_quality_gap and has_fuel:
                    picks.append({
                        'Ticker': t, 
                        'Gap %': f"{row['Gap_Pct']:.2f}%", 
                        'RVOL': f"{row['RVOL']:.2f}x"
                    })
        
        if picks: 
            st.success("High-Probability Runners Found")
            st.table(pd.DataFrame(picks))
        else: 
            st.info("No 'Quality' Gaps today. Most moves are likely 'done' or just noise.")