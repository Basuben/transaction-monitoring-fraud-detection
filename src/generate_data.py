"""Generate a fully synthetic mobile money transaction table.

Nothing here comes from a real employer, customer or case. Accounts, amounts and
timestamps are random. A small share of accounts get fraud-like behaviour injected
so the detection rules have something to find, and a share of legitimate accounts
behave like busy merchants so the rules also produce some false alarms.
"""
import numpy as np
import pandas as pd

REPORTING_THRESHOLD = 100_000  # KES, illustrative only
TYPOLOGIES = ["structuring", "velocity", "pass_through", "night_large"]


def _normal_activity(rng, accounts, merchants, days, start):
    rows = []
    hour_p = np.array([1, 1, 1, 1, 1, 2, 4, 7, 9, 9, 8, 8, 8, 8, 8, 8, 8, 8, 7, 6, 4, 3, 2, 1], float)
    hour_p /= hour_p.sum()
    for acc in accounts:
        is_merchant = acc in merchants
        n = int(rng.integers(150, 400)) if is_merchant else int(rng.integers(8, 40))
        day = rng.integers(0, days, n)
        hour = rng.choice(24, n, p=hour_p)
        minute = rng.integers(0, 60, n)
        ts = start + pd.to_timedelta(day, unit="D") + pd.to_timedelta(hour, unit="h") + pd.to_timedelta(minute, unit="m")
        mu, sigma = (np.log(9000), 1.1) if is_merchant else (np.log(1500), 1.0)
        amt = np.clip(rng.lognormal(mu, sigma, n), 50, 90_000).round(2)
        typ = rng.choice(["deposit", "withdrawal", "transfer", "loan_repayment"], n, p=[0.30, 0.25, 0.30, 0.15])
        for t, a, k in zip(ts, amt, typ):
            rows.append((acc, t, a, k, 0))
    return rows


def _inject(rng, acc, typology, days, start):
    base = start + pd.Timedelta(days=int(rng.integers(5, days - 5)))
    rows = []
    if typology == "structuring":
        for _ in range(int(rng.integers(4, 8))):
            t = base + pd.Timedelta(hours=int(rng.integers(0, 40)), minutes=int(rng.integers(0, 60)))
            rows.append((acc, t, float(rng.integers(86_000, 99_500)), "deposit", 1))
    elif typology == "velocity":
        t0 = base + pd.Timedelta(hours=int(rng.integers(8, 20)))
        for _ in range(int(rng.integers(14, 30))):
            t = t0 + pd.Timedelta(minutes=int(rng.integers(0, 55)))
            rows.append((acc, t, float(rng.integers(500, 8_000)), str(rng.choice(["transfer", "withdrawal"])), 1))
    elif typology == "pass_through":
        t0 = base + pd.Timedelta(hours=int(rng.integers(8, 18)))
        amt = float(rng.integers(250_000, 800_000))
        rows.append((acc, t0, amt, "deposit", 1))
        out = amt * float(rng.uniform(0.93, 0.99))
        rows.append((acc, t0 + pd.Timedelta(minutes=int(rng.integers(5, 40))), round(out, 2), "transfer", 1))
    elif typology == "night_large":
        for i in range(int(rng.integers(3, 6))):
            t = base + pd.Timedelta(days=i % 2, hours=int(rng.integers(0, 5)), minutes=int(rng.integers(0, 60)))
            rows.append((acc, t, float(rng.integers(52_000, 150_000)), "transfer", 1))
    return rows


def generate(n_accounts=2000, days=60, fraud_share=0.03, merchant_share=0.05, seed=42):
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2026-01-01")
    accounts = [f"ACC{i:05d}" for i in range(n_accounts)]
    merchants = set(rng.choice(accounts, int(n_accounts * merchant_share), replace=False))
    fraud_accounts = rng.choice(accounts, int(n_accounts * fraud_share), replace=False)

    rows = _normal_activity(rng, accounts, merchants, days, start)
    typology = {}
    for i, acc in enumerate(fraud_accounts):
        typ = TYPOLOGIES[i % len(TYPOLOGIES)]
        typology[acc] = typ
        rows += _inject(rng, acc, typ, days, start)

    df = pd.DataFrame(rows, columns=["account_id", "timestamp", "amount_kes", "txn_type", "is_fraud_txn"])
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.floor("min")
    df = df.sort_values("timestamp", kind="stable").reset_index(drop=True)
    df.insert(0, "txn_id", [f"TXN{i:07d}" for i in range(len(df))])
    df["is_fraud_account"] = df["account_id"].isin(typology).astype(int)
    df["injected_typology"] = df["account_id"].map(typology).fillna("")
    return df


if __name__ == "__main__":
    data = generate()
    data.to_csv("outputs/transactions.csv", index=False)
    print(f"{len(data):,} transactions, {data['account_id'].nunique():,} accounts")
