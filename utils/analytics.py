import pandas as pd
import numpy as np
from scipy.stats import linregress
import streamlit as st

def calculate_changes(df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    df = df.copy().sort_values("date")
    
    diffs = df["date"].diff().dt.days.median()
    if np.isnan(diffs):
        diffs = 30
    if diffs > 60:
        yoy_shift = 4
        pop_label = "QoQ %"
    else:
        yoy_shift = 12
        pop_label = "MoM %"
    
    df["value_lag_yoy"] = df["value"].shift(yoy_shift)
    df["yoy_pct"] = (df["value"] / df["value_lag_yoy"] - 1) * 100
    
    df["value_lag_pop"] = df["value"].shift(1)
    df["pop_pct"] = (df["value"] / df["value_lag_pop"] - 1) * 100
    
    return df, pop_label

def detect_trend(df: pd.DataFrame, window: int = 12) -> dict:
    df = df.copy().sort_values("date")
    recent = df.tail(window)
    
    if len(recent) < 2:
        return {"recent_trend": "Insufficient data", "slope": 0}
    
    x = np.arange(len(recent))
    slope, intercept, r_value, _, _ = linregress(x, recent["value"])
    trend_strength = r_value ** 2
    direction = "upward" if slope > 0 else "downward" if slope < 0 else "flat"
    
    return {
        "recent_trend": f"{direction} (R²={trend_strength:.2f})",
        "recent_slope": slope
    }

def detect_anomalies(df: pd.DataFrame, window: int = 36, threshold: float = 2.5) -> pd.DataFrame:
    df = df.copy()
    rolling = df["value"].rolling(window=window, min_periods=12)
    df["rolling_mean"] = rolling.mean()
    df["rolling_std"] = rolling.std()
    
    df["z_score"] = (df["value"] - df["rolling_mean"]) / df["rolling_std"]
    df["anomaly"] = np.abs(df["z_score"]) > threshold
    
    return df

def forecast_linear(df: pd.DataFrame, periods: int = 12) -> pd.DataFrame:
    """Linear trend extrapolation forecast with OLS prediction interval."""
    if len(df) < 12:
        raise ValueError("Need ~12+ points for reliable linear forecast")
    
    df = df.copy().sort_values("date")
    
    x = np.arange(len(df))
    slope, intercept, r_value, _, std_err = linregress(x, df["value"])
    
    # Point forecast
    future_x = np.arange(len(df), len(df) + periods)
    yhat = slope * future_x + intercept
    
    # Prediction interval (95%)
    mean_x = x.mean()
    n = len(x)
    t = 1.96  # Approx for large n
    pred_var = std_err**2 * (1 + 1/n + (future_x - mean_x)**2 / np.sum((x - mean_x)**2))
    conf = t * np.sqrt(pred_var)
    
    yhat_lower = yhat - conf
    yhat_upper = yhat + conf
    
    # Future dates
    last_date = df["date"].iloc[-1]
    diffs = df["date"].diff().dt.days.median()
    freq = 'MS' if diffs < 60 else 'QS'
    future_dates = pd.date_range(start=last_date + pd.DateOffset(months=1 if diffs < 60 else 3), periods=periods, freq=freq)
    
    forecast_df = pd.DataFrame({
        "date": future_dates,
        "yhat": yhat,
        "yhat_lower": yhat_lower,
        "yhat_upper": yhat_upper
    })
    
    return forecast_df