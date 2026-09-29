"""Generate data, run the rules, score accounts, print and save the results."""
import json
from pathlib import Path

from src.generate_data import generate
from src.rules import RULES, apply_rules
from src.score import MEDIUM_AT, evaluate, score_accounts


def main():
    out = Path("outputs")
    out.mkdir(exist_ok=True)

    data = generate()
    flagged = apply_rules(data)
    scored = score_accounts(flagged)
    truth = data[["account_id", "is_fraud_account", "injected_typology"]].drop_duplicates("account_id")
    metrics = evaluate(scored, truth)

    queued = set(scored.loc[scored["risk_score"] >= MEDIUM_AT, "account_id"])
    by_type = {}
    for typ in sorted(t for t in truth["injected_typology"].unique() if t):
        ids = set(truth.loc[truth["injected_typology"] == typ, "account_id"])
        by_type[typ] = {"accounts": len(ids), "caught_in_review_queue": len(queued & ids)}
    metrics["by_typology"] = by_type
    metrics["rule_hits"] = {r: int(flagged[r].sum()) for r in RULES}

    data.to_csv(out / "transactions.csv", index=False)
    scored.sort_values("risk_score", ascending=False).to_csv(out / "account_scores.csv", index=False)
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
