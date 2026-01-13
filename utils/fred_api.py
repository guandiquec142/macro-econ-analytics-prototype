import requests
import pandas as pd
import os
from datetime import datetime
import json
from config.settings import FRED_API_KEY
import streamlit as st  # For error messages in app context

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "cached")
os.makedirs(CACHE_DIR, exist_ok=True)

def _cache_filename(series_id: str) -> str:
    return os.path.join(CACHE_DIR, f"{series_id}.json")

def get_series_observations(series_id: str, force_refresh: bool = False) -> pd.DataFrame:
    """Fetch FRED series with caching, timeout, and error handling."""
    cache_file = _cache_filename(series_id)
    
    # Try cache first
    if not force_refresh and os.path.exists(cache_file):
        cache_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(cache_file))
        if cache_age.total_seconds() < 86400:
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                df = pd.DataFrame(data["observations"])
                if not df.empty:
                    df["date"] = pd.to_datetime(df["date"])
                    df["value"] = pd.to_numeric(df["value"], errors="coerce")
                    return df
            except Exception:
                pass  # Bad cache—fall through to fetch
    
    # Live fetch with timeout and retry logic
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id.upper(),
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "limit": 10000
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)  # 30s timeout
        response.raise_for_status()
        data = response.json()
        
        df = pd.DataFrame(data["observations"])
        if df.empty:
            raise ValueError("No data returned")
        
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        
        # Cache successful
        with open(cache_file, "w") as f:
            json.dump(data, f)
        
        return df
    
    except requests.Timeout:
        st.error("FRED API timeout—network issue or slow response. Try again or shorter range. Using cache if available.")
        raise
    except requests.RequestException as e:
        st.error(f"FRED API error: {str(e)}. Check connection or try later.")
        raise
    except Exception as e:
        st.error(f"Data processing error: {str(e)}")
        raise

def get_series_info(series_id: str) -> dict:
    url = "https://api.stlouisfed.org/fred/series"
    params = {"series_id": series_id.upper(), "api_key": FRED_API_KEY, "file_type": "json"}
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()["seriess"][0]
    except Exception as e:
        st.warning(f"Metadata fetch failed: {str(e)}")
        return {}