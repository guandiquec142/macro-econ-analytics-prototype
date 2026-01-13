import plotly.express as px
import pandas as pd
import streamlit as st

def plot_series(df: pd.DataFrame, title: str) -> None:
    """Simple line chart with nice defaults."""
    if df.empty:
        st.warning("No data to plot.")
        return

    fig = px.line(df, x="date", y="value", title=title,
                  labels={"value": "Value", "date": "Date"},
                  template="streamlit")  # dark/light auto
    fig.update_layout(hovermode="x unified", height=600)
    fig.update_traces(line=dict(width=3))
    st.plotly_chart(fig, use_container_width=True)

    # Basic stats
    with st.expander("Summary Statistics"):
        st.write(df.describe())
        st.write(f"Latest value ({df['date'].max().date()}): {df['value'].iloc[-1]:,.2f}")