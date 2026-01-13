import streamlit as st
from utils.llm import ask_gemini
import pandas as pd

st.title("Ask Questions About the Data")

if "merged_df" not in st.session_state or st.session_state.merged_df.empty:
    st.warning("Load data on Explore Data page first.")
    st.stop()

merged_df = st.session_state.merged_df
selected_names = st.session_state.selected_series_names
show_forecast = st.session_state.get("show_forecast", False)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask about the data (e.g., 'Compare wages and inflation' or 'Debt sustainability?')"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Step 38: NL parsing for specific intents
    lower_prompt = prompt.lower()
    if "compare wages" in lower_prompt and "inflation" in lower_prompt:
        # Wages vs CPI: compute corr/lags
        if len(selected_names) >= 2 and "BLS AHE Private" in selected_names and "CPIAUCSL" in selected_names:
            df_cor = merged_df.dropna(how='any')
            wages = df_cor["BLS AHE Private - Average Hourly Earnings (Monthly - $)"]
            cpi = df_cor["CPIAUCSL - Consumer Price Index (Monthly - Index)"]
            corr = wages.corr(cpi)
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
            context = f"Series: {', '.join(selected_names)}. Overall corr: r={corr:.2f}. Lags:\n{lag_note}"
            user_prompt = "Analyze wage vs inflation for business/pricing (spiral risk, implications) in bullets."
        else:
            context = "Wages/CPI not both loaded—general analysis."
            user_prompt = prompt
    elif "debt sustainability" in lower_prompt:
        # Debt sustainability: compute debt/GDP if loaded
        if len(selected_names) >= 2 and "GDP" in selected_names and "Treasury Public Debt" in selected_names:
            df_ratio = merged_df.copy()
            df_ratio['Debt/GDP Ratio (%)'] = (df_ratio['Treasury Public Debt - Total Outstanding (Daily - Billions $)'] / df_ratio['GDP - Gross Domestic Product (Quarterly - Billions $)']) * 100
            recent_ratio = df_ratio['Debt/GDP Ratio (%)'].iloc[-1]
            context = f"Series: {', '.join(selected_names)}. Latest Debt/GDP: {recent_ratio:.1f}%"
            user_prompt = "Analyze debt sustainability for business/pricing (ratio risks, implications) in bullets."
        else:
            context = "Debt/GDP not both loaded—general analysis."
            user_prompt = prompt
    else:
        context = f"Series: {', '.join(selected_names)}"
        user_prompt = prompt
    
    forecast_note = " Forecast shown." if show_forecast else ""
    full_context = f"{context} Primary trend: {st.session_state.primary_trend.get('recent_trend', 'N/A')}{forecast_note}"
    
    with st.chat_message("assistant"):
        with st.spinner("Gemini 2.5 Flash thinking..."):
            response = ask_gemini(user_prompt, full_context, df=merged_df)
        st.markdown(response)
    
    st.session_state.messages.append({"role": "assistant", "content": response})

# Suggested questions for value-add
with st.expander("Suggested Questions"):
    st.markdown("""
    - Compare wages and inflation
    - Debt sustainability?
    - Pricing impact of rates?
    - Forecast outlook for unemployment?
    """)

st.info("Context includes current data + analytics + RAG metadata. Gemini grounds responses.")