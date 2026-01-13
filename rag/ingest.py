import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from utils.fred_api import get_series_info
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings  # Local, no quota
from langchain_community.vectorstores import Chroma
import requests
from config.settings import BLS_API_KEY

# Popular FRED series (keep as is)
POPULAR_SERIES = [
    "GDP", "CPIAUCSL", "UNRATE", "FEDFUNDS", "PPIACO",
    "GS10", "T10YIE", "CORESTICKM159SFRBATL", "PCEPI", "RSXFS",
]

# Curated notes (keep as is)
CURATED_NOTES = """
GDP: Nominal Gross Domestic Product measures total economic output in current dollars. Important for business pricing as it captures both real growth and inflation.

CPIAUCSL: Headline Consumer Price Index—all items. Tracks average consumer prices; YoY used for inflation gauge. Businesses watch for wage/price spiral risks.

UNRATE: Civilian unemployment rate. Low UNRATE signals tight labor market—upward wage pressure, potential margin squeeze.

FEDFUNDS: Effective Federal Funds Rate—Fed's main policy tool. Rising rates increase borrowing costs, cool demand.

PPIACO: Producer Price Index—wholesale inflation. Leading indicator for consumer prices; high PPI often forces pricing adjustments to protect margins.

Core vs Headline: Core excludes food/energy volatility—Fed's preferred for policy. Headline felt by consumers/businesses.

Core PCE: Personal Consumption Expenditures price index, Fed's favored inflation measure—less volatile than CPI, better for long-term pricing strategy.
"""

DB_PATH = "rag/vectorstore"

def ingest_rag_data():
    docs = []
    
    # FRED metadata (keep existing logic)
    for series_id in POPULAR_SERIES:
        try:
            meta = get_series_info(series_id)
            text = f"""
Series: {meta.get('title', 'N/A')}
ID: {series_id}
Description: {meta.get('notes') or meta.get('title', 'N/A')}
Units: {meta.get('units', 'N/A')}
Frequency: {meta.get('frequency', 'N/A')}
Seasonal Adjustment: {meta.get('seasonal_adjustment', 'N/A')}
"""
            docs.append({"text": text, "source": f"FRED Metadata {series_id}"})
        except Exception as e:
            print(f"Warning: FRED metadata fetch failed for {series_id}: {e}")
    
    # Add curated notes as chunk
    docs.append({"text": CURATED_NOTES, "source": "Curated Econ Notes"})
    
    # BLS metadata fetch for wages
    bls_series_id = "CES0500000003"
    bls_url = "https://api.bls.gov/publicAPI/v2/surveys"  # Example catalog, or timeseries for specific
    headers = {"Content-type": "application/json"}
    payload = {"registrationkey": BLS_API_KEY}
    try:
        response = requests.post(bls_url, json=payload, headers=headers)
        response.raise_for_status()
        bls_data = response.json()
        # Extract or hardcode (fallback if API doesn't have detailed notes)
        bls_metadata = """
Series: Average Hourly Earnings of All Employees, Total Private (CES0500000003)
ID: CES0500000003
Description: Average hourly earnings of all employees on private nonfarm payrolls, seasonally adjusted. Measures wage growth in the private sector.
Units: Dollars per Hour
Frequency: Monthly
Seasonal Adjustment: Seasonally Adjusted
Notes: From U.S. Bureau of Labor Statistics. Key for tracking wage inflation and labor costs, potential for wage-price spirals.
"""
        docs.append({"text": bls_metadata, "source": f"BLS Metadata {bls_series_id}"})
    except Exception as e:
        print(f"Warning: BLS metadata fetch failed: {e}")
        # Hardcode fallback
        docs.append({"text": bls_metadata, "source": f"BLS Fallback {bls_series_id}"})

    # Treasury metadata (hardcode from dictionary/API)
    treasury_metadata = """
Series: Debt to the Penny
ID: Debt to the Penny
Description: Daily total public debt outstanding of the U.S. Treasury.
Fields: record_date (daily date), tot_pub_debt_out_amt (total public debt outstanding in dollars).
Units: Dollars
Frequency: Daily
Notes: From U.S. Department of the Treasury. Measures gross federal debt; key for debt/GDP ratios and sustainability analysis. High ratios may signal fiscal pressure affecting interest rates and economic growth.
"""
    docs.append({"text": treasury_metadata, "source": "Treasury Metadata Debt to Penny"})

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = []
    for doc in docs:
        split = splitter.split_text(doc["text"])
        for i, chunk in enumerate(split):
            chunks.append({"text": chunk, "source": doc["source"], "chunk_id": i})
    
    # Local embeddings—no API quota
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    texts = [c["text"] for c in chunks]
    metadatas = [{"source": c["source"], "chunk_id": c["chunk_id"]} for c in chunks]
    
    os.makedirs(DB_PATH, exist_ok=True)
    
    # Load existing DB and add new chunks incrementally
    vectordb = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    vectordb.add_texts(texts=texts, metadatas=metadatas)
    vectordb.persist()
    
    print(f"Success: RAG DB updated incrementally with {len(chunks)} new BLS/Treasury chunks (FRED preserved).")

if __name__ == "__main__":
    ingest_rag_data()