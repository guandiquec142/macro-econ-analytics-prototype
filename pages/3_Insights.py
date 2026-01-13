import streamlit as st
from utils.llm import ask_gemini
import pandas as pd

st.title("Insights Dashboard")

if "merged_df" not in st.session_state or st.session_state.merged_df.empty:
    st.warning("No data loaded. Visit Explore Data page and load a series first.")
    st.stop()

merged_df = st.session_state.merged_df
selected_names = st.session_state.selected_series_names
trend_info = st.session_state.get("primary_trend", {})
pop_label = st.session_state.get("pop_label", "PoP %")

# Primary for single or default
primary_name = selected_names[0]
primary_df = merged_df[[primary_name]].reset_index().rename(columns={primary_name: "value"})
latest_date = primary_df['date'].iloc[-1].date()
latest_value = primary_df['value'].iloc[-1]
latest_yoy = primary_df["yoy_pct"].iloc[-1] if "yoy_pct" in primary_df.columns and not pd.isna(primary_df["yoy_pct"].iloc[-1]) else "N/A"
latest_pop = primary_df["pop_pct"].iloc[-1] if "pop_pct" in primary_df.columns and not pd.isna(primary_df["pop_pct"].iloc[-1]) else "N/A"
anoms = primary_df[primary_df["anomaly"]] if "anomaly" in primary_df.columns else pd.DataFrame()

st.header(f"Key Insights: {', '.join(selected_names)}")

st.subheader("Current Snapshot")
st.markdown(f"""
- **Latest Value (Primary: {primary_name})**: {latest_value:,.3f} as of {latest_date}
- **Recent Trend (Primary)**: {trend_info.get('recent_trend', 'N/A')}
- **Latest Changes (Primary)**: YoY {latest_yoy if isinstance(latest_yoy, str) else f'{latest_yoy:.2f}%'} | {pop_label} {latest_pop if isinstance(latest_pop, str) else f'{latest_pop:.2f}%'}
""")

st.subheader("Anomalies & Risks (Primary)")
if not anoms.empty:
    st.write(f"{len(anoms)} anomalies detected in period (z-score > 2.5):")
    st.dataframe(anoms[["date", "value", "z_score"]].sort_values("date", ascending=False).head(10))
else:
    st.success("No significant anomalies in selected period—stable primary series.")

# Step 39: Multi-factor insights for pairs
multi_factor_context = ""
multi_factor_prompt = ""
if len(selected_names) == 2:
    df_cor = merged_df.dropna(how='any')
    df1_name, df2_name = selected_names
    corr = df_cor.corr().iloc[0,1]
    
    # Wages vs CPI: spiral risk
    if "BLS AHE Private" in selected_names and "CPIAUCSL" in selected_names:
        wages = df_cor["BLS AHE Private - Average Hourly Earnings (Monthly - $)"]
        cpi = df_cor["CPIAUCSL - Consumer Price Index (Monthly - Index)"]
        lag_data = []
        for lag in range(-3, 4):
            if lag < 0:
                shifted = cpi.shift(lag)
                lag_label = f"Wages lead CPI by {-lag} mo"
                lag_corr = wages.corr(shifted)
            else:
                shifted = wages.shift(lag)
                lag_label = f"CPI leads Wages by {lag} mo"
                lag_corr = shifted.corr(cpi)
            lag_data.append(f"{lag_label}: r={lag_corr:.2f}")
        lag_note = "\n".join(lag_data)
        multi_factor_context = f"Overall corr r={corr:.2f}. Lags:\n{lag_note}"
        multi_factor_prompt = "Using only the provided data + RAG metadata, analyze wage vs inflation for multi-factor insights (spiral risk, pricing implications) in bullets."
    
    # Debt/GDP: sustainability
    elif "GDP" in selected_names and "Treasury Public Debt" in selected_names:
        df_ratio = df_cor.copy()
        df_ratio['Debt/GDP Ratio (%)'] = (df_ratio['Treasury Public Debt - Total Outstanding (Daily - Billions $)'] / df_ratio['GDP - Gross Domestic Product (Quarterly - Billions $)']) * 100
        recent_ratio = df_ratio['Debt/GDP Ratio (%)'].iloc[-1]
        ratio_trend = detect_trend(df_ratio.reset_index().rename(columns={'Debt/GDP Ratio (%)': 'value'})).get('recent_trend', 'N/A')
        multi_factor_context = f"Latest Debt/GDP: {recent_ratio:.1f}% ({ratio_trend} trend)"
        multi_factor_prompt = "Using only the provided data + RAG metadata, analyze debt/GDP ratio for multi-factor insights (sustainability risks, pricing implications) in bullets."
    
    # General fallback
    else:
        multi_factor_context = f"Overall corr r={corr:.2f}"
        multi_factor_prompt = "Using only the provided data + RAG metadata, analyze series correlation for multi-factor insights (risks, pricing implications) in bullets."

st.subheader("Business Implications (Primary)")
with st.spinner("Gemini 2.5 Flash summarizing implications..."):
    context = f"Series: {', '.join(selected_names)} Latest primary: {latest_value:,.3f} ({latest_date}) Trend: {trend_info.get('recent_trend', 'N/A')} YoY: {latest_yoy if isinstance(latest_yoy, str) else f'{latest_yoy:.2f}%'} Anomalies: {len(anoms)}"
    implications = ask_gemini("Using only the provided data + RAG metadata, summarize business strategy implications (pricing, margins, demand, risk) in concise bullets.", context, df=primary_df)
st.markdown(implications)

# Multi-factor if applicable
if len(selected_names) == 2 and multi_factor_prompt:
    st.subheader("Multi-Factor Insights (Cross-Series)")
    with st.spinner("Gemini 2.5 Flash analyzing multi-factors..."):
        multi_implications = ask_gemini(multi_factor_prompt, multi_factor_context, df=merged_df.reset_index())
    st.markdown(multi_implications)

st.caption("Insights auto-generated from current data + analytics. Refresh on Explore page for updates.")