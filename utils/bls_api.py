import requests
import pandas as pd
import os
from datetime import datetime
import json
from config.settings import BLS_API_KEY

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cached")
os.makedirs(CACHE_DIR, exist_ok=True)

def _cache_filename(series_id: str) -> str:
    return os.path.join(CACHE_DIR, f"bls_{series_id}.json")

def get_bls_series(series_id: str = "CES0500000003", years: int = 20, force_refresh: bool = False) -> pd.DataFrame:
    """Fetch BLS series (CES0500000003 = Average Hourly Earnings Private)."""
    cache_file = _cache_filename(series_id)
    
    if not force_refresh and os.path.exists(cache_file):
        cache_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file))
        if cache_age.total_seconds() < 86400:
            with open(cache_file, "r") as f:
                data = json.load(f)
            return _parse_bls_response(data)
    
    url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
    headers = {"Content-type": "application/json"}
    start_year = str(datetime.now().year - years)
    end_year = str(datetime.now().year)
    payload = {
        "seriesid": [series_id],
        "startyear": start_year,
        "endyear": end_year,
        "registrationkey": BLS_API_KEY
    }
    
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    json_data = response.json()
    
    with open(cache_file, "w") as f:
        json.dump(json_data, f)
    
    return _parse_bls_response(json_data)

def _parse_bls_response(json_data: dict) -> pd.DataFrame:
    if json_data["status"] != "REQUEST_SUCCEEDED":
        raise ValueError(f"BLS error: {json_data.get('message', 'Unknown')}")
    
    series = json_data["Results"]["series"][0]
    data = series["data"]
    
    rows = []
    for item in data:
        year = int(item["year"])
        month = int(item["period"].replace("M", ""))
        date = pd.to_datetime(f"{year}-{month:02d}-01")
        value = float(item["value"])
        rows.append({"date": date, "value": value})
    
    df = pd.DataFrame(rows).sort_values("date")
    return df