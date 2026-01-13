import requests
import pandas as pd
import os
from datetime import datetime
import json

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cached")
os.makedirs(CACHE_DIR, exist_ok=True)

def _cache_filename() -> str:
    return os.path.join(CACHE_DIR, "treasury_debt_to_penny.json")

def get_treasury_debt(force_refresh: bool = False) -> pd.DataFrame:
    """Fetch Treasury Debt to the Penny (daily total public debt in billions)."""
    cache_file = _cache_filename()
    
    if not force_refresh and os.path.exists(cache_file):
        cache_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file))
        if cache_age.total_seconds() < 86400:
            with open(cache_file, "r") as f:
                data = json.load(f)
            df = pd.DataFrame(data["data"])
            df["date"] = pd.to_datetime(df["record_date"])
            df["value"] = pd.to_numeric(df["tot_pub_debt_out_amt"], errors="coerce") / 1_000_000_000  # Billions
            return df[["date", "value"]].dropna().sort_values("date")
    
    base_url = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
    endpoint = "/v2/accounting/od/debt_to_penny"
    
    url = f"{base_url}{endpoint}"
    params = {
        "fields": "record_date,tot_pub_debt_out_amt",
        "filter": "record_date:gte:2000-01-01",
        "format": "json",
        "page[size]": 10000
    }
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    
    df = pd.DataFrame(data["data"])
    df["date"] = pd.to_datetime(df["record_date"])
    df["value"] = pd.to_numeric(df["tot_pub_debt_out_amt"], errors="coerce") / 1_000_000_000  # Billions
    
    df = df[["date", "value"]].dropna().sort_values("date")
    
    with open(cache_file, "w") as f:
        json.dump(data, f)
    
    return df