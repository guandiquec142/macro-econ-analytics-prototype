import streamlit as st

st.set_page_config(page_title="Macro Economic Analytics Prototype", layout="wide")

st.title("Macro Economic Analytics Prototype")

st.markdown("""
**Business Problem:**
In a volatile economic environment, businesses grapple with pricing decisions amid inflation, striving to offset rising costs without eroding margins or dampening demand. Traditional approaches involve manual aggregation from disparate sources, resulting in delayed insights and reactive strategies.

**How This Tool Solves It:**
This prototype fuses data from three official U.S. government APIs—FRED (Federal Reserve for indicators like GDP and CPI), BLS (labor stats like wages), and Treasury (debt figures)—into interactive monthly-aligned charts with forecasts and "what if" scenarios. Google Gemini AI provides natural language queries and grounded responses for swift, actionable analysis.

**Business Value:**
Leaders gain rapid access to integrated federal data without navigating multiple spreadsheets or sites, enabling faster trend spotting (e.g., wage pressures on pricing). AI delivers reliable insights, potentially accelerating strategy cycles—though real gains depend on integration. Built on open sources at zero cost, it's adaptable to proprietary data in any industry.

Navigate to Explore Data to start.
""")

@st.experimental_singleton(suppress_st_warning=True)
def init_rag():
    from rag.ingest import ingest_rag_data
    ingest_rag_data()  # Builds vectorstore on first run
init_rag()