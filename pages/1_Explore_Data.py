import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from utils.fred_api import get_series_observations, get_series_info
from utils.bls_api import get_bls_series
from utils.treasury_api import get_treasury_debt
from utils.llm import ask_gemini
from utils.analytics import calculate_changes, detect_trend, detect_anomalies, forecast_linear
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Macro Economic Analytics Prototype", layout="wide")

st.title("Macro Economic Analytics Prototype")

st.markdown("""
**Description**: Interactive exploration of public federal economic data (FRED, BLS, Treasury) with AI-powered insights. Demonstrates multi-source fusion, analytics, forecasting, RAG-grounded Gemini explanations, NL queries, and multi-factor insights for business strategy (focus: pricing in inflation).

**How to Use**:
- Select up to 2 series.
- Adjust years (defaults recent).
- Data loads automatically on selection/change.
- Toggle forecast for primary series (Click Load/Refresh button if forecast doesn't immediately appear on primary graph).
- Use Explain buttons or Ask Questions/Insights for AI analysis.
- Forecasts/scenarios illustrative only—not financial advice.
""")

SERIES_OPTIONS = {
    "GDP - Gross Domestic Product (Quarterly - Billions $)": ("fred", "GDP"),
    "CPIAUCSL - Consumer Price Index (Monthly - Index)": ("fred", "CPIAUCSL"),
    "UNRATE - Unemployment Rate (Monthly - %)": ("fred", "UNRATE"),
    "FEDFUNDS - Federal Funds Rate (Monthly - %)": ("fred", "FEDFUNDS"),
    "PPIACO - Producer Price Index (Monthly - Index)": ("fred", "PPIACO"),
    "BLS AHE Private - Average Hourly Earnings (Monthly - $)": ("bls", "CES0500000003"),
    "Treasury Public Debt - Total Outstanding (Daily - Billions $)": ("treasury", None),
}

current_year = datetime.now().year

year_options = list(range(1947, current_year + 1))[::-1]  # Recent first

# Locked defaults first load
if "selected_start_year" not in st.session_state:
    st.session_state.selected_start_year = 2020
if "selected_end_year" not in st.session_state:
    st.session_state.selected_end_year = current_year
if "selected_series_names" not in st.session_state:
    st.session_state.selected_series_names = []

with st.sidebar:
    st.header("Select Series (Max 2)")
    selected_names = st.multiselect(
        "Series",
        options=list(SERIES_OPTIONS.keys()),
        default=st.session_state.selected_series_names,
        max_selections=2,
        key="series_multi_select"
    )
    
    if not selected_names:
        st.info("Select 1-2 series to load data.")
        st.stop()
    
    col1, col2 = st.columns(2)
    with col1:
        start_index = year_options.index(st.session_state.selected_start_year) if st.session_state.selected_start_year in year_options else year_options.index(2020)
        start_year = st.selectbox("Start Year", options=year_options, index=start_index, key="start_year_select")
    with col2:
        end_index = year_options.index(st.session_state.selected_end_year) if st.session_state.selected_end_year in year_options else 0
        end_year = st.selectbox("End Year", options=year_options, index=end_index, key="end_year_select")
    
    if start_year > end_year:
        st.error("Start after end—swapping.")
        start_year, end_year = end_year, start_year
    
    load_button = st.button("Load / Refresh Data")
    
    show_forecast = st.checkbox("Show 12-Month Linear Forecast (Primary)", value=False)
    
    scenario_shock = 0.0
    if show_forecast:
        scenario_shock = st.slider("Scenario Shock (% change to primary latest value)", min_value=-50.0, max_value=50.0, value=0.0, step=0.5,
                                   key="scenario_shock_slider")

# Detect changes for auto-load
series_changed = st.session_state.get("selected_series_names", []) != selected_names
years_changed = st.session_state.get("selected_start_year") != start_year or st.session_state.get("selected_end_year") != end_year

if load_button or series_changed or years_changed or "merged_df" not in st.session_state:
    with st.spinner("Loading and aligning multi-source data to monthly month-end..."):
        try:
            dfs = []
            for name in selected_names:
                source, series_id = SERIES_OPTIONS[name]
                if source == "fred":
                    temp_df = get_series_observations(series_id, force_refresh=load_button or series_changed or years_changed)
                    temp_df = temp_df[['date', 'value']]
                elif source == "bls":
                    temp_df = get_bls_series(series_id)
                elif source == "treasury":
                    temp_df = get_treasury_debt()
                
                temp_df['value'] = pd.to_numeric(temp_df['value'], errors='coerce')
                temp_df["date"] = pd.to_datetime(temp_df["date"])
                temp_df = temp_df[(temp_df["date"].dt.year >= start_year) & (temp_df["date"].dt.year <= end_year)]
                temp_df = temp_df.dropna(subset=["value"])
                temp_df = temp_df.rename(columns={"value": name})
                temp_df = temp_df.set_index("date")[[name]]
                dfs.append(temp_df)
            
            merged_raw = pd.concat(dfs, axis=1)
            
            if merged_raw.empty:
                st.error("No raw data in selected period.")
                st.stop()
            
            # Unified monthly alignment (month-end index)
            min_period = merged_raw.index.min().to_period('M')
            max_period = merged_raw.index.max().to_period('M')
            monthly_periods = pd.period_range(start=min_period, end=max_period, freq='M')
            monthly_index = monthly_periods.to_timestamp(how='end')
            
            expanded_index = merged_raw.index.union(monthly_index)
            merged_expanded = merged_raw.reindex(expanded_index)
            merged_ffill = merged_expanded.ffill()
            merged_df = merged_ffill.loc[monthly_index].sort_index()
            
            # Key fix: name the index 'date' for proper reset_index in analytics/forecast
            merged_df.index.name = 'date'
            
            if merged_df.empty or merged_df.dropna(how='all').empty:
                st.error("No overlapping data after monthly alignment—widen years.")
                st.stop()
            
            primary_name = selected_names[0]
            primary_df = merged_df[[primary_name]].reset_index().rename(columns={primary_name: "value"})
            primary_df, pop_label = calculate_changes(primary_df)
            primary_df = detect_anomalies(primary_df)
            trend_info = detect_trend(primary_df)
            
            st.session_state.merged_df = merged_df
            st.session_state.selected_series_names = selected_names
            st.session_state.primary_trend = trend_info
            st.session_state.pop_label = pop_label
            st.session_state.selected_start_year = start_year
            st.session_state.selected_end_year = end_year
            st.session_state.scenario_shock = scenario_shock
            st.session_state.show_forecast = show_forecast
        except Exception as e:
            st.error(f"Load failed: {str(e)}")
            st.stop()

# Force rerun on series change for smooth add/remove
if series_changed:
    st.rerun()

# Retrieve
merged_df = st.session_state.merged_df
selected_names = st.session_state.selected_series_names
trend_info = st.session_state.primary_trend
pop_label = st.session_state.pop_label
scenario_shock = st.session_state.get("scenario_shock", 0.0)

st.subheader("Multi-Source Comparison (Unified Monthly Charts)")

for name in selected_names:
    series_df = merged_df[[name]].reset_index().rename(columns={name: "value"})
    
    fig = px.line(series_df, x="date", y="value", title=name)
    fig.update_layout(xaxis_title="Date", yaxis_title="Value")
    
    if show_forecast and name == selected_names[0]:
        try:
            forecast_df = forecast_linear(series_df, periods=12)
            
            fig.add_scatter(x=forecast_df["date"], y=forecast_df["yhat"], mode="lines", name="Linear Forecast", line=dict(dash="dot", color="orange"))
            
            fig.add_trace(go.Scatter(
                x=pd.concat([forecast_df["date"], forecast_df["date"][::-1]]),
                y=pd.concat([forecast_df["yhat_upper"], forecast_df["yhat_lower"][::-1]]),
                fill='toself',
                fillcolor='rgba(255,165,0,0.2)',
                line=dict(color='rgba(255,165,0,0)'),
                name="95% Confidence"
            ))
            
            if scenario_shock != 0.0:
                shocked_df = series_df.copy()
                shocked_df.iloc[-1, shocked_df.columns.get_loc("value")] *= (1 + scenario_shock / 100)
                
                shocked_forecast = forecast_linear(shocked_df, periods=12)
                
                fig.add_scatter(x=shocked_forecast["date"], y=shocked_forecast["yhat"], mode="lines", name=f"Scenario ({scenario_shock:+.1f}%)", line=dict(dash="dash", color="purple"))
                
                st.info(f"Scenario: {scenario_shock:+.1f}% shock to primary latest value (illustrative).")
        except Exception as e:
            st.warning(f"Forecast unavailable for {name}: {str(e)}")
    
    st.plotly_chart(fig, use_container_width=True)

st.caption("Unified monthly (month-end): Daily Treasury debt uses month-end value; lower-frequency (e.g., quarterly GDP) forward-filled. Separate charts preserve native scales.")

# Step 40: Export CSV (with clean date format)
if not merged_df.empty:
    export_df = merged_df.reset_index()
    export_df['date'] = export_df['date'].dt.date  # Clean to YYYY-MM-DD
    csv = export_df.to_csv(index=False)
    st.download_button(
        label="Export Data (CSV)",
        data=csv,
        file_name="macro_data.csv",
        mime="text/csv",
    )

if st.button("Explain Charts (Gemini 2.5 Flash)"):
    with st.spinner("Analyzing multi-source..."):
        series_note = f"Series: {', '.join(selected_names)}"
        forecast_note = " Forecast shown." if show_forecast else ""
        scenario_note = f" Scenario shock {scenario_shock:+.1f}% applied." if scenario_shock != 0.0 else ""
        context = f"{series_note} Primary trend: {trend_info.get('recent_trend', 'N/A')}{forecast_note}{scenario_note} Data aligned monthly."
        insights = ask_gemini("Analyze for business strategy/pricing implications across series.", context, df=merged_df)
    st.markdown("**Gemini 2.5 Flash Multi-Source Insights:**")
    st.markdown(insights)

if show_forecast:
    if st.button("Explain Forecast/Scenario in Business Terms (Gemini 2.5 Flash)"):
        with st.spinner("Analyzing forecast implications..."):
            base_forecast = forecast_linear(merged_df[[selected_names[0]]].reset_index().rename(columns={selected_names[0]: "value"}), periods=12)
            trajectory = f"Base trajectory to {base_forecast['yhat'].iloc[-1]:,.2f} by {base_forecast['date'].iloc[-1].date()}"
            scenario_note = ""
            if scenario_shock != 0.0:
                shocked_df = merged_df[[selected_names[0]]].reset_index().rename(columns={selected_names[0]: "value"}).copy()
                shocked_df.iloc[-1, shocked_df.columns.get_loc("value")] *= (1 + scenario_shock / 100)
                shocked_forecast = forecast_linear(shocked_df, periods=12)
                trajectory += f"; scenario {scenario_shock:+.1f}% shock to {shocked_forecast['yhat'].iloc[-1]:,.2f}"
                scenario_note = f" Scenario applies {scenario_shock:+.1f}% shock to primary latest value for 'what if' illustration."
            context = f"Series: {', '.join(selected_names)} Primary trend: {trend_info.get('recent_trend', 'N/A')} {trajectory}{scenario_note} Monthly aligned data."
            insights = ask_gemini("Summarize business/pricing strategy implications of this forecast/scenario trajectory in concise bullets.", context, df=merged_df)
        st.markdown("**Gemini 2.5 Flash Forecast/Scenario Implications:**")
        st.markdown(insights)