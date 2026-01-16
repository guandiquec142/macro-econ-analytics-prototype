# Macro Economic Analytics Prototype: AI-Powered Pricing & Strategy Insights

Personal open-source project demonstrating integrated economic intelligence using public U.S. government data + modern AI.

**Business Problem**  
In today's volatile economy—with persistent inflation, wage pressures, and shifting demand—business leaders struggle to make confident pricing, investment, and expansion decisions. Traditional methods rely on manual aggregation from multiple government websites and spreadsheets, leading to delayed insights, inconsistent analysis, and reactive rather than proactive strategies.

**How This Tool Solves It**  
This prototype fuses live data from three authoritative U.S. government APIs—FRED (Federal Reserve Economic Data for indicators like CPI, GDP, interest rates), BLS (Bureau of Labor Statistics for wages, employment), and Treasury (debt & yield curves)—into interactive, monthly-aligned charts. Users can explore trends, generate forecasts, run "what-if" scenarios (e.g., "What if inflation stays above 3% while wages rise 4%?"), and ask natural-language questions. Google Gemini delivers concise, grounded responses strictly tied to the fetched data, complete with source references.

**Business Value**  
Executives and analysts get rapid, integrated visibility into macro trends without hopping between sites or wrangling data manually—enabling faster spotting of risks like wage-push inflation or opportunities like softening rates. The AI provides reliable, evidence-based interpretations that can sharpen pricing strategies and accelerate decision cycles. Built entirely on free, public sources at effectively zero cost, the architecture is highly adaptable: swap in proprietary data for industry-specific applications (retail, manufacturing, finance, etc.).

Navigate to **Explore Data** to get started.

## Live Demo
https://macro-econ-analytics-prototype.streamlit.app/

## Technical Overview
This project evolves the RAG pattern from static document retrieval into real-time data orchestration + AI augmentation:

- **Frontend**: Streamlit (multi-page app with interactive charts, selectors, and chat interface)
- **Data Integration**: Direct API pulls from
  - FRED API (St. Louis Fed – broad macro indicators)
  - BLS Public Data API (labor/wage stats)
  - U.S. Treasury FiscalData API (debt, rates, yields – no API key required)
- **Processing & Visualization**: Pandas for alignment/resampling/forecasting, Plotly for rich monthly-aligned charts with scenario overlays
- **AI Layer**: Google Gemini 2.5-flash (fast, cheap, and surprisingly good on structured economic data) – responses grounded via in-memory context + inline citations to series IDs and observation dates
- **Architecture Notes**: No vector store, no batch indexing – everything fetched fresh on demand and passed directly to Gemini. Keeps costs at zero and data as current as the source APIs.

Runs beautifully on Streamlit Community Cloud free tier. Zero paid services required beyond your own Gemini key.

## Local Setup
1. Clone the repo
2. `pip install -r requirements.txt`
3. Set these environment variables:
   - `GOOGLE_API_KEY` (required – get free at https://aistudio.google.com/app/apikey)
   - `FRED_API_KEY` (strongly recommended)
   - `BLS_API_KEY` (strongly recommended – v2 key, register at https://data.bls.gov/registrationEngine/)
4. `streamlit run app.py`

Treasury data needs no key at all.

Feedback, forks, issues, and collaboration very welcome.

Not affiliated with any government agency—pure learning & demonstration exercise.
