"""Turn rule hits into an account level risk score and alert tiers."""
import pandas as pd

from src.rules import RULES

WEIGHTS = {"structuring": 50, "pass_through": 45, "velocity": 30, "night_large": 25}
ALERT_AT = 40   # score needed to open a case
MEDIUM_AT = 25  # score worth a second look


def score_accounts(flagged):
    """Each rule counts once per account, so noisy repeat hits cannot inflate a score."""
    per_account = flagged.groupby("account_id")[list(RULES)].any()
    scores = sum(per_account[r].astype(int) * w for r, w in WEIGHTS.items())
    out = per_account.assign(risk_score=scores)
    out["tier"] = pd.cut(out["risk_score"], [-1, MEDIUM_AT - 1, ALERT_AT - 1, 1000], labels=["low", "medium", "high"])
    out["rules_hit"] = per_account.apply(lambda r: ",".join(k for k in RULES if r[k]), axis=1)
    return out.reset_index()


def _confusion(df, cutoff):
    flagged = df["risk_score"] >= cutoff
    fraud = df["is_fraud_account"] == 1
    tp, fp = int((flagged & fraud).sum()), int((flagged & ~fraud).sum())
    fn, tn = int((~flagged & fraud).sum()), int((~flagged & ~fraud).sum())
    return {
        "flagged": tp + fp,
        "true_positives": tp,
        "false_positives": fp,
        "missed_fraud": fn,
        "precision": round(tp / (tp + fp), 3) if tp + fp else 0.0,
        "recall": round(tp / (tp + fn), 3) if tp + fn else 0.0,
        "false_positive_rate": round(fp / (fp + tn), 4) if fp + tn else 0.0,
    }


def evaluate(scored, truth):
    """Compare against the synthetic ground truth at account level.

    Two views: `alerts` (score >= ALERT_AT, opens a case) and `review_queue`
    (score >= MEDIUM_AT, gets a quick analyst look).
    """
    df = truth.merge(scored, on="account_id", how="left").fillna({"risk_score": 0})
    return {
        "accounts": len(df),
        "alerts": _confusion(df, ALERT_AT),
        "review_queue": _confusion(df, MEDIUM_AT),
    }
