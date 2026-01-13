import google.generativeai as genai
import pandas as pd
from config.settings import GOOGLE_API_KEY, GEMINI_MODEL
from utils.analytics import detect_trend
from utils.rag import retrieve_context

genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel(GEMINI_MODEL)

def ask_gemini(user_prompt: str, context: str = "", df: pd.DataFrame = None) -> str:
    # RAG context first
    rag_context = retrieve_context(user_prompt)
    
    # Analytics
    analytics_context = ""
    if df is not None and not df.empty:
        try:
            latest_yoy = "N/A"
            if "yoy_pct" in df.columns:
                val = df["yoy_pct"].iloc[-1]
                if not pd.isna(val):
                    latest_yoy = f"{val:.2f}%"
            
            trend = detect_trend(df).get("recent_trend", "N/A")
            anoms_last_year = len(df[df["anomaly"]].tail(12)) if "anomaly" in df.columns else 0
            
            analytics_context = f"""
Key Analytics:
- Latest YoY Change: {latest_yoy}
- Recent Trend: {trend}
- Anomalies last 12 periods: {anoms_last_year}
"""
        except Exception:
            analytics_context = "Analytics unavailable."
    
    full_prompt = f"""
You are an expert economic analyst advising business leaders on strategy and pricing.
Expert Knowledge (from FRED metadata and curated notes): {rag_context}
Data Context: {context}
Analytics Summary: {analytics_context}

Question: {user_prompt}

Respond professionally in bullets, with clear business implications.
"""
    try:
        response = model.generate_content(full_prompt)
        return response.text.strip()
    except Exception as e:
        return f"Gemini error: {str(e)}. Try again."