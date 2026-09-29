"""Rule based transaction monitoring checks.

Every rule takes a transaction table sorted by timestamp (with a clean 0..n index)
and returns a boolean Series saying which rows tripped the rule. Windows look
backwards from each transaction and include both ends.
"""
import numpy as np
import pandas as pd

OUTFLOW = ("withdrawal", "transfer")


def _trailing_sum(df, values, window):
    """Per account sum of `values` over the trailing time window, at every row."""
    ts = df["timestamp"].to_numpy().astype("datetime64[ns]").astype("int64")
    width = pd.Timedelta(window).value
    vals = np.asarray(values, dtype=float)
    out = np.zeros(len(df))
    for idx in df.groupby("account_id").indices.values():
        t = ts[idx]
        csum = np.concatenate([[0.0], np.cumsum(vals[idx])])
        left = np.searchsorted(t, t - width, side="left")
        out[idx] = csum[np.arange(len(t)) + 1] - csum[left]
    return out


def structuring(df, threshold=100_000, band=0.85, min_count=3, window="48h"):
    """Several deposits sitting just under the reporting threshold in a short span."""
    near = (df["txn_type"] == "deposit") & (df["amount_kes"] >= band * threshold) & (df["amount_kes"] < threshold)
    return pd.Series(near.to_numpy() & (_trailing_sum(df, near, window) >= min_count), index=df.index)


def velocity(df, max_txns=10, window="1h"):
    """Too many transactions from one account inside an hour."""
    return pd.Series(_trailing_sum(df, np.ones(len(df)), window) >= max_txns, index=df.index)


def pass_through(df, min_inflow=200_000, ratio=0.9, window="60min"):
    """Large money in, almost all of it out again within the hour."""
    inflow = np.where((df["txn_type"] == "deposit") & (df["amount_kes"] >= min_inflow), df["amount_kes"], 0.0)
    outflow = np.where(df["txn_type"].isin(OUTFLOW), df["amount_kes"], 0.0)
    in_sum = _trailing_sum(df, inflow, window)
    out_sum = _trailing_sum(df, outflow, window)
    hit = (in_sum >= min_inflow) & (out_sum >= ratio * in_sum) & df["txn_type"].isin(OUTFLOW).to_numpy()
    return pd.Series(hit, index=df.index)


def night_large(df, min_amount=50_000, start_hour=0, end_hour=5, min_count=2, window="24h"):
    """Repeated large movements in the small hours."""
    hour = df["timestamp"].dt.hour
    hit = ((hour >= start_hour) & (hour < end_hour) & (df["amount_kes"] >= min_amount)).to_numpy()
    return pd.Series(hit & (_trailing_sum(df, hit, window) >= min_count), index=df.index)


RULES = {
    "structuring": structuring,
    "velocity": velocity,
    "pass_through": pass_through,
    "night_large": night_large,
}


def apply_rules(df):
    flags = pd.DataFrame({name: fn(df) for name, fn in RULES.items()})
    return pd.concat([df, flags], axis=1)
